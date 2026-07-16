"""Derive Hit@5 ground truth (which chunks "should" be retrieved) for the 60-item
CS testset, by parsing each item's human-annotated `source_location` (page ranges,
section titles, or audio MM:SS ranges) and matching against real ingested chunks.

Two chunk dumps in play (different chunking schemes, must be matched separately):
  - eval/chunks_dump_bookagent.json   (BookAgent's own chunker; chunk_id + page_start/end + start_sec/end_sec)
  - BookAgent-Baseline's eval/chunks_dump.json (RecursiveCharacterTextSplitter; source string + page/start_index)

This is a first-pass automated matcher, NOT a substitute for human spot-check —
per project convention, QA ground truth must be eyeballed before being trusted
(see memory: QA溯源核验原则). Items where matching is ambiguous or the source_location
gives no specific page (chapter-level "no answer" items) are flagged, not guessed.

Usage:
    python eval/derive_ground_truth.py
Outputs:
    eval/ground_truth_bookagent.json
    eval/ground_truth_baseline.json
    prints a summary of match confidence per item
"""
from __future__ import annotations
import json
import re
from pathlib import Path

_ROOT = Path(__file__).parent.parent
_QA_FILE = _ROOT / "eval/testset/cs/qa/qa.jsonl"
_BOOKAGENT_DUMP = _ROOT / "eval/chunks_dump_bookagent.json"
_BASELINE_DUMP = Path("/home/ismy/github/BookAgent-Baseline/eval/chunks_dump.json")

_PAGE_RANGE_RE = re.compile(r"\bp(\d+)(?:-p?(\d+))?\b")
_AUDIO_RANGE_RE = re.compile(r"(\d{2}):(\d{2})[–\-](\d{2}):(\d{2})")


def _mmss_to_sec(mm: str, ss: str) -> float:
    return int(mm) * 60 + int(ss)


def _parse_location_part(part: str) -> dict:
    """Parse one clause of source_location (already split on '；')."""
    part = part.strip()
    if part.startswith("音频"):
        m = _AUDIO_RANGE_RE.search(part)
        if m:
            start = _mmss_to_sec(m.group(1), m.group(2))
            end = _mmss_to_sec(m.group(3), m.group(4))
            return {"kind": "audio", "source": "segment-01.mp3", "start_sec": start, "end_sec": end}
        return {"kind": "no_location", "source": "segment-01.mp3"}

    file_m = re.search(r"([\w.\-]+\.(?:pdf|epub))", part)
    if not file_m:
        return {"kind": "unparsed", "raw": part}
    source_file = file_m.group(1)
    rest = part[file_m.end():]

    page_m = _PAGE_RANGE_RE.search(rest)
    if page_m:
        p_start = int(page_m.group(1))
        p_end = int(page_m.group(2)) if page_m.group(2) else p_start
        return {"kind": "page", "source": source_file, "page_start": p_start, "page_end": p_end}

    # No page number: try section-title text search fallback (resolved later against dump).
    section_m = re.search(r"§[\d.]+\s*([^（；]+)?", rest)
    if section_m:
        title = (section_m.group(1) or "").strip()
        return {"kind": "section", "source": source_file, "section_title": title, "raw_rest": rest.strip()}

    # Whole-chapter parenthetical note (e.g. "（本章未涉及...）") — no specific location, by design.
    return {"kind": "no_location", "source": source_file}


def parse_source_location(loc: str) -> list[dict]:
    return [_parse_location_part(p) for p in loc.split("；") if p.strip()]


def _match_bookagent(hints: list[dict], chunks: list[dict]) -> tuple[list[str], str]:
    matched: list[str] = []
    method = "no_location_expected"
    for h in hints:
        if h["kind"] == "page":
            cands = [c for c in chunks if c["source_file"] == h["source"]
                      and c["page_start"] is not None
                      and h["page_start"] <= c["page_start"] <= h["page_end"]]
            matched += [c["chunk_id"] for c in cands]
            if cands:
                method = "page_exact"
        elif h["kind"] == "audio":
            cands = [c for c in chunks if c["source_file"] == h["source"]
                      and c["start_sec"] is not None
                      and not (c["end_sec"] <= h["start_sec"] or c["start_sec"] >= h["end_sec"])]
            matched += [c["chunk_id"] for c in cands]
            if cands:
                method = "audio_overlap"
        elif h["kind"] == "section":
            title = h.get("section_title", "")
            cands = [c for c in chunks if c["source_file"] == h["source"]
                      and title and title.lower()[:20] in c["content"].lower()]
            matched += [c["chunk_id"] for c in cands]
            method = "section_search" if cands else "section_search_no_hit"
        elif h["kind"] == "unparsed":
            method = "unparsed"
    return sorted(set(matched)), method


def _match_baseline(hints: list[dict], chunks: list[dict]) -> tuple[list[str], str]:
    matched: list[str] = []
    method = "no_location_expected"
    for h in hints:
        if h["kind"] == "page":
            # baseline source string: "data/<file>:p<page-1>@<offset>" (0-indexed page)
            prefix = f"data/{h['source']}:p"
            for c in chunks:
                if not c["source"].startswith(prefix):
                    continue
                pg_str = c["source"][len(prefix):].split("@")[0]
                try:
                    pg = int(pg_str) + 1  # baseline pages are 0-indexed
                except ValueError:
                    continue
                if h["page_start"] <= pg <= h["page_end"]:
                    matched.append(c["source"])
            if matched:
                method = "page_exact"
        elif h["kind"] == "audio":
            prefix = f"data/{h['source']}:t"
            for c in chunks:
                if not c["source"].startswith(prefix):
                    continue
                rng = c["source"][len(prefix):]
                try:
                    s, e = rng.split("-")
                    s, e = float(s), float(e)
                except ValueError:
                    continue
                if not (e <= h["start_sec"] or s >= h["end_sec"]):
                    matched.append(c["source"])
            if matched:
                method = "audio_overlap"
        elif h["kind"] == "section":
            title = h.get("section_title", "")
            prefix = f"data/{h['source']}:"
            for c in chunks:
                if c["source"].startswith(prefix) and title and title.lower()[:20] in c["content"].lower():
                    matched.append(c["source"])
            method = "section_search" if matched else "section_search_no_hit"
        elif h["kind"] == "unparsed":
            method = "unparsed"
    return sorted(set(matched)), method


# 人式审读补丁：这几条 source_location 只给了 §编号/章节标题，没给页码，
# 且该标题文本在 marker 解析出的正文里没有逐字出现（章节抽取 PDF 常见——
# 标题可能被识别成图片/单独的大字块、或编号格式跟正文不一致），自动化的
# section_search 匹配不到。逐条读了 eval/chunks_dump_bookagent.json 里
# cpu-intro.pdf / cpu-api.pdf 对应页的真实内容，和问题内容核对后人工定位：
#   cs-b001 "进程精确定义/进程与程序区别" → p1 内容就是这段定义
#   cs-b002 "machine state 三要素"        → 紧跟 §4.1 定义之后，p1-p2
#   cs-b003 "时分复用技术+核心代价"        → p1(virtualizing) + p2(Time sharing)
#   cs-b004 "main()前的初始化步骤"         → §4.3，p4(loading) + p5(I/O fd 初始化)
#   cs-b012 "shell 三步流程(fork/重定向/exec)" → §5.4，与 cs-b011 同段落 p6-p7
_MANUAL_PAGE_OVERRIDE = {
    "cs-b001": [{"kind": "page", "source": "cpu-intro.pdf", "page_start": 1, "page_end": 1}],
    "cs-b002": [{"kind": "page", "source": "cpu-intro.pdf", "page_start": 1, "page_end": 2}],
    "cs-b003": [{"kind": "page", "source": "cpu-intro.pdf", "page_start": 1, "page_end": 2}],
    "cs-b004": [{"kind": "page", "source": "cpu-intro.pdf", "page_start": 4, "page_end": 5}],
    "cs-b012": [{"kind": "page", "source": "cpu-api.pdf", "page_start": 6, "page_end": 7}],
    # section_search 自动匹配到的 p10/p12 是误报："Process States" 这个短语在章末
    # summary 和 homework 段落里也出现过，被朴素子串匹配误命中；真正的 §4.4 状态图
    # /Blocked-Ready-Running 讨论核对后确认在 p6（状态转换图+I/O重叠timeline表在p6-p7）。
    "cs-b005": [{"kind": "page", "source": "cpu-intro.pdf", "page_start": 6, "page_end": 6}],
    "cs-b006": [{"kind": "page", "source": "cpu-intro.pdf", "page_start": 6, "page_end": 7}],
}


def main() -> None:
    qa_items = [json.loads(l) for l in open(_QA_FILE) if l.strip()]
    ba_chunks = json.load(open(_BOOKAGENT_DUMP))
    bl_chunks = json.load(open(_BASELINE_DUMP))

    ba_out, bl_out = {}, {}
    summary = {"page_exact": 0, "audio_overlap": 0, "section_search": 0,
               "section_search_no_hit": 0, "no_location_expected": 0, "unparsed": 0}
    flagged = []

    for item in qa_items:
        hints = _MANUAL_PAGE_OVERRIDE.get(item["id"]) or parse_source_location(item["source_location"])
        ba_ids, ba_method = _match_bookagent(hints, ba_chunks)
        bl_ids, bl_method = _match_baseline(hints, bl_chunks)
        ba_out[item["id"]] = {"chunk_ids": ba_ids, "method": ba_method}
        bl_out[item["id"]] = {"support_chunks": bl_ids, "method": bl_method}
        summary[ba_method] = summary.get(ba_method, 0) + 1
        if ba_method in ("section_search_no_hit", "unparsed") or (ba_method == "page_exact" and not ba_ids):
            flagged.append((item["id"], item["source_location"], ba_method))

    with open(_ROOT / "eval/ground_truth_bookagent.json", "w", encoding="utf-8") as f:
        json.dump(ba_out, f, ensure_ascii=False, indent=2)
    with open(_ROOT / "eval/ground_truth_baseline.json", "w", encoding="utf-8") as f:
        json.dump(bl_out, f, ensure_ascii=False, indent=2)

    print(f"共 {len(qa_items)} 题，匹配方式分布：{summary}")
    print(f"\n需要人工核对的条目（{len(flagged)}个）：")
    for id_, loc, method in flagged:
        print(f"  {id_} [{method}] {loc}")


if __name__ == "__main__":
    main()
