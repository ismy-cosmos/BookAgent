"""Generate parser comparison report from bench results + filled scorecard."""
from __future__ import annotations
import csv
import json
import statistics
from pathlib import Path

_SCRIPTS = Path(__file__).parent
ROOT = _SCRIPTS.parent
_DEFAULT_RESULTS = ROOT / "results"
_DEFAULT_REPORT = ROOT / "results" / "report.md"

PARSERS = ["unstructured", "marker"]
SPEED_TARGET = 15.0  # pages/min — applies to VLM-adjusted speed


def _load_results(results_dir: Path, parser: str) -> dict[str, dict]:
    return {
        (d := json.loads(f.read_text()))["id"]: d
        for f in sorted((results_dir / parser).glob("*.json"))
    }


def _load_scorecard(results_dir: Path) -> list[dict]:
    with open(results_dir / "scorecard.csv", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def _vlm_page_ids(
    all_results: dict[str, dict[str, dict]],
    scorecard: list[dict],
) -> set[str]:
    """Pages routed to VLM in production — excluded from parser speed calculation.

    Criterion A: marker output contains image placeholder (![]()) — the page is
    figure-dominated; no text parser can recover it regardless.

    Criterion B: both parsers score struct=0 — visually complex layout that
    neither parser can reconstruct (e.g. nested drug grids, dense index tables).
    """
    vlm: set[str] = set()

    # Build struct score lookup first (needed for criterion A filter)
    struct: dict[str, dict[str, int]] = {}
    for row in scorecard:
        pid, parser = row["id"], row["parser"]
        val = row.get("struct", "").strip()
        struct.setdefault(pid, {})[parser] = int(val) if val.isdigit() else 0

    # A: any page where marker output contains an image placeholder (![]())
    # — marker cannot render the figure; must go to VLM regardless of surrounding text quality
    for pid, r in all_results.get("marker", {}).items():
        content = "".join(e.get("content", "") for e in r.get("elements", []))
        if "![" in content:
            vlm.add(pid)

    # B: both parsers fail on structure (struct=0 for all parsers)
    for pid, parser_scores in struct.items():
        if parser_scores and all(s == 0 for s in parser_scores.values()):
            vlm.add(pid)

    return vlm


def _speed_stats(results: dict[str, dict], exclude_ids: set[str] | None = None) -> dict:
    times = [
        r["elapsed_sec"]
        for pid, r in results.items()
        if r.get("elapsed_sec") is not None and pid not in (exclude_ids or set())
    ]
    if not times:
        return {"pages_per_min": float("inf"), "p50": 0.0, "p95": 0.0, "n": 0}
    times_sorted = sorted(times)
    n = len(times_sorted)
    p50 = statistics.median(times_sorted)
    p95 = times_sorted[min(int(n * 0.95), n - 1)]
    avg = statistics.mean(times)
    return {
        "pages_per_min": round(60.0 / avg, 1) if avg > 0 else float("inf"),
        "p50": round(p50, 3),
        "p95": round(p95, 3),
        "n": n,
    }


def _score_totals(scorecard: list[dict], parser: str) -> dict[str, int]:
    rows = [r for r in scorecard if r["parser"] == parser]
    totals: dict[str, int] = {"detect": 0, "content": 0, "struct": 0}
    for row in rows:
        for dim in totals:
            val = row.get(dim, "").strip()
            if val:
                totals[dim] += int(val)
    totals["total"] = sum(v for k, v in totals.items() if k != "total")
    return totals


def main(
    results_dir: Path = _DEFAULT_RESULTS,
    report_path: Path = _DEFAULT_REPORT,
) -> None:
    all_results = {p: _load_results(results_dir, p) for p in PARSERS}
    scorecard = _load_scorecard(results_dir)

    vlm_ids = _vlm_page_ids(all_results, scorecard)
    speed_raw = {p: _speed_stats(all_results[p]) for p in PARSERS}
    speed_adj = {p: _speed_stats(all_results[p], exclude_ids=vlm_ids) for p in PARSERS}
    scores = {p: _score_totals(scorecard, p) for p in PARSERS}

    n_total = len(next(iter(all_results.values()), {}))
    n_vlm = len(vlm_ids)

    lines: list[str] = ["# 解析器选型对比报告\n"]

    # ── section 1: raw speed ──────────────────────────────────────────────────
    lines += [
        "## 1. 速度对比（原始）\n",
        "| 解析器 | pages/min | p50 延迟(s) | p95 延迟(s) |",
        "|---|---|---|---|",
    ]
    for p in PARSERS:
        s = speed_raw[p]
        lines.append(f"| {p} | {s['pages_per_min']} | {s['p50']} | {s['p95']} |")

    # ── section 2: VLM routing ────────────────────────────────────────────────
    vlm_list = ", ".join(sorted(vlm_ids)) if vlm_ids else "（无）"
    lines += [
        "\n## 2. VLM 路由分析\n",
        f"图片页或双解析器均失败的页面将路由至 VLM，不计入解析器速度考核。\n",
        f"- **VLM 页数**：{n_vlm} / {n_total}",
        f"- **VLM 页面**：{vlm_list}\n",
        "| 解析器 | 有效页/min（剔除VLM页） | 达标(≥15) |",
        "|---|---|---|",
    ]
    for p in PARSERS:
        s = speed_adj[p]
        ppm = s["pages_per_min"]
        ok = "✅" if ppm >= SPEED_TARGET else "❌"
        ppm_str = f"{ppm}" if ppm != float("inf") else "∞（全部为VLM页）"
        lines.append(f"| {p} | {ppm_str} | {ok} |")

    # ── section 3: quality scores ─────────────────────────────────────────────
    lines += [
        "\n## 3. 人工评分汇总（满分 90）\n",
        "| 解析器 | detect(/30) | content(/30) | struct(/30) | 总分(/90) |",
        "|---|---|---|---|---|",
    ]
    for p in PARSERS:
        sc = scores[p]
        lines.append(
            f"| {p} | {sc['detect']} | {sc['content']} | {sc['struct']} | {sc['total']} |"
        )

    # ── section 4: recommendation ─────────────────────────────────────────────
    lines.append("\n## 4. 选定建议\n")
    qualified = [p for p in PARSERS if speed_adj[p]["pages_per_min"] >= SPEED_TARGET]

    if not qualified:
        lines.append(
            "❌ **两个解析器剔除VLM页后均未达速度要求（≥15 pages/min），需调整策略后重测。**"
        )
        winner = None
    elif len(qualified) == 1:
        winner = qualified[0]
        loser = next(p for p in PARSERS if p != winner)
        lines.append(
            f"✅ **选定：`{winner}`**（`{loser}` 有效速度不达标，直接出局）"
        )
    else:
        winner = max(qualified, key=lambda p: scores[p]["total"])
        other = next(p for p in qualified if p != winner)
        lines.append(
            f"✅ **选定：`{winner}`**"
            f"（速度均达标；人工总分 {scores[winner]['total']} > {scores[other]['total']}）"
        )

    if winner:
        lines.append(
            f"\n**下一步：** 在 `requirements.txt` 中取消 `{winner}` 注释，"
            f"删除 `requirements-bench.txt`，合并 `feat/w1-parser-selection` → `main`。"
        )

    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text("\n".join(lines), encoding="utf-8")
    print(f"Report → {report_path}")


if __name__ == "__main__":
    main()
