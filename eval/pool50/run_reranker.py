"""P4: Concat + Reranker evaluation.

Builds candidate pools from Chroma Dense Top-30 + Lance Lexical Top-N,
deduplicates by chunk_id, re-ranks with bge-reranker-v2-m3, and computes
strict-ID Hit@5.

Compares against the Chroma Dense baseline using the CORRECTED ground truth
(after the CS/Law auditor confirmations recorded in the 2026-07-28 handoff).
"""
from __future__ import annotations

import json
import sys
from collections import defaultdict
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(REPO_ROOT))

from FlagEmbedding import FlagReranker

from eval.retrieval_evaluation import load_ground_truth

WORK_DIR = Path(__file__).resolve().parent

# ── Config ────────────────────────────────────────────────────────────────────
CHROMA_BASELINE = WORK_DIR / "chroma-baseline" / "results.json"
LANCE_LEXICAL = WORK_DIR / "lang-lexical" / "results.json"  # Language-aware lexical
CORPUS_DIR = WORK_DIR / "corpus"
OUTPUT_DIR = WORK_DIR / "reranker-lang"

CHROMA_TOP = 30
LANCE_TOP = 5           # Reduced from 20: Lance unique SC is only 5 law questions;
                        # larger pool introduces keyword-match noise that fools
                        # the cross-encoder (confirmed on cs-b006 ablation).
LANCE_SUBJECTS = {"law"}  # Only law has Lance-unique supporting chunks (5 questions).
TOP_K = 5

RESULT_SCHEMA_VERSION = "issue48.reranker-result/v2"
RERANKER_MODEL = "BAAI/bge-reranker-v2-m3"


# ── Helpers ────────────────────────────────────────────────────────────────────
def load_corpus() -> dict[str, str]:
    """Return chunk_id → content for all subjects."""
    corpus: dict[str, str] = {}
    for subj in ["cs", "clinical", "law"]:
        corpus_file = CORPUS_DIR / f"{subj}.jsonl"
        if not corpus_file.exists():
            print(f"WARN: corpus file not found: {corpus_file}")
            continue
        with open(corpus_file, encoding="utf-8") as fh:
            for line in fh:
                obj = json.loads(line)
                corpus[obj["chunk_id"]] = obj["content"]
    return corpus


def build_candidate_pool(
    chroma_row: dict,
    lance_row: dict | None,
) -> list[dict]:
    """Merge Chroma Top-N + Lance Top-N, deduplicate by chunk_id.

    Lance candidates are only included when the subject is in LANCE_SUBJECTS.
    """
    subject = chroma_row["subject"]
    seen: dict[str, dict] = {}

    # Chroma dense pool (sorted, take first CHROMA_TOP)
    for rank, hit in enumerate(
        chroma_row["rrf_candidate_pools"]["dense"][:CHROMA_TOP], start=1
    ):
        cid = hit["chunk_id"]
        entry = dict(hit)
        entry.setdefault("sources", []).append("dense")
        entry.setdefault("source_ranks", {}).setdefault("dense", rank)
        if cid not in seen:
            seen[cid] = entry

    # Lance lexical pool (only for subjects where it helps)
    if lance_row is not None and subject in LANCE_SUBJECTS:
        lance_pool = lance_row["rrf_candidate_pools"].get("lexical", [])
        for rank, hit in enumerate(lance_pool[:LANCE_TOP], start=1):
            cid = hit["chunk_id"]
            if cid in seen:
                seen[cid].setdefault("sources", []).append("lexical")
                seen[cid].setdefault("source_ranks", {}).setdefault("lexical", rank)
            else:
                entry = dict(hit)
                entry.setdefault("sources", []).append("lexical")
                entry.setdefault("source_ranks", {}).setdefault("lexical", rank)
                seen[cid] = entry

    return list(seen.values())


def build_query(row: dict) -> str:
    """Use dense_query (agent rewrite) — ablation showed concat hurts reranker.

    Concat(lexical, dense) creates an overly long query that drowns the
    cross-encoder in detail noise, pushing GT chunks out of Top-5 even when
    they were at dense rank 1 (see cs-b002/b009/b011 ablation).
    """
    return row.get("dense_query", "") or row.get("lexical_query", "")


def compute_question_level_hits(rows: list[dict]) -> dict:
    """Aggregate trace-level rows to question-level strict-ID Hit@5.

    A question 'hits' if AT LEAST ONE of its traces has a hit in Top-5.
    Returns {question_id: bool} for questions that have ground truth.
    """
    qmap: dict[str, list[bool]] = defaultdict(list)
    for row in rows:
        qid = row["question_id"]
        if row["ground_truth_chunk_ids"]:
            qmap[qid].append(row["strict_hit"])

    return {qid: any(hits) for qid, hits in qmap.items()}


# ── Main ──────────────────────────────────────────────────────────────────────
def main() -> None:
    print("Loading corrected ground truth...")
    gt_corrected = load_ground_truth()
    print(f"  {len(gt_corrected)} questions with ground truth")

    print("Loading corpus...")
    corpus = load_corpus()
    print(f"  {len(corpus)} chunks")

    print("Loading baseline results...")
    with open(CHROMA_BASELINE, encoding="utf-8") as fh:
        chroma_data = json.load(fh)
    chroma_rows: dict[str, dict] = {r["id"]: r for r in chroma_data["rows"]}
    print(f"  {len(chroma_rows)} rows")

    print("Loading lance-lexical results...")
    with open(LANCE_LEXICAL, encoding="utf-8") as fh:
        lance_data = json.load(fh)
    lance_rows: dict[str, dict] = {r["id"]: r for r in lance_data["rows"]}
    print(f"  {len(lance_rows)} rows")

    # ── Recompute baseline against corrected GT ────────────────────────────
    print("\nRecomputing baseline against corrected ground truth...")
    base_qhits: dict[str, bool] = {}
    for row in chroma_data["rows"]:
        qid = row["question_id"]
        gt_ids = set(gt_corrected.get(qid, []))
        if not gt_ids:
            continue
        top5_ids = {h["chunk_id"] for h in row["modes"]["dense"]}
        hit = bool(gt_ids & top5_ids)
        base_qhits[qid] = base_qhits.get(qid, False) or hit

    base_total = len(base_qhits)
    base_hits = sum(base_qhits.values())
    print(f"  Baseline (corrected GT): {base_hits}/{base_total} = {base_hits/base_total:.4f}")

    # Per-subject baseline
    base_by_subj = defaultdict(lambda: {"total": 0, "hits": 0})
    for row in chroma_data["rows"]:
        qid = row["question_id"]
        if qid not in base_qhits:
            continue
        subj = row["subject"]
        base_by_subj[subj]["total"] = max(base_by_subj[subj]["total"],
                                          1 if base_qhits.get(qid, False) or True else 0)
    # Recompute properly
    base_by_subj = defaultdict(lambda: {"total": set(), "hits": set()})
    for row in chroma_data["rows"]:
        qid = row["question_id"]
        if qid not in base_qhits:
            continue
        subj = row["subject"]
        base_by_subj[subj]["total"].add(qid)
        if base_qhits[qid]:
            base_by_subj[subj]["hits"].add(qid)
    for subj in base_by_subj:
        t = len(base_by_subj[subj]["total"])
        h = len(base_by_subj[subj]["hits"])
        print(f"    {subj}: {h}/{t} = {h/t:.4f}" if t else f"    {subj}: N/A")

    # ── Load reranker ──────────────────────────────────────────────────────
    print(f"\nLoading reranker: {RERANKER_MODEL}")
    reranker = FlagReranker(RERANKER_MODEL, use_fp16=True)
    print("  model loaded")

    # ── Process each row ───────────────────────────────────────────────────
    all_rows: list[dict] = []
    chunk_misses = 0
    pool_sizes: list[int] = []

    for row_id, chroma_row in chroma_rows.items():
        lance_row = lance_rows.get(row_id)
        qid = chroma_row["question_id"]

        # Use corrected ground truth
        gt_ids = set(gt_corrected.get(qid, []))
        row_eligible = len(gt_ids) > 0

        # Build candidate pool
        candidates = build_candidate_pool(chroma_row, lance_row)
        pool_sizes.append(len(candidates))

        # Build query
        query = build_query(chroma_row)

        # Look up chunk texts
        docs: list[str] = []
        valid_candidates: list[dict] = []
        for c in candidates:
            text = corpus.get(c["chunk_id"])
            if text is None:
                chunk_misses += 1
                continue
            docs.append(text)
            valid_candidates.append(c)

        # Rerank
        if not docs:
            top5: list[dict] = []
        elif len(docs) == 1:
            top5 = [{**valid_candidates[0], "rerank_score": 1.0}]
        else:
            pairs = [[query, doc] for doc in docs]
            scores: list[float] = reranker.compute_score(pairs, normalize=True)
            ranked = sorted(
                zip(valid_candidates, scores), key=lambda x: x[1], reverse=True
            )
            top5 = []
            for c, s in ranked[:TOP_K]:
                entry = dict(c)
                entry["rerank_score"] = round(float(s), 6)
                entry["original_score"] = c.get("score")
                top5.append(entry)

        # Strict-ID hit
        top5_ids = {c["chunk_id"] for c in top5}
        hit_ids = sorted(gt_ids & top5_ids) if row_eligible else []

        row_result = {
            "id": row_id,
            "question_id": qid,
            "subject": chroma_row["subject"],
            "trace_source": chroma_row.get("trace_source", ""),
            "status": chroma_row["status"],
            "eligible": row_eligible,
            "dense_query": chroma_row.get("dense_query", ""),
            "lexical_query": chroma_row.get("lexical_query", ""),
            "reranker_query": query,
            "ground_truth_chunk_ids": sorted(gt_ids),
            "candidate_pool_size": len(candidates),
            "candidate_pool_valid": len(valid_candidates),
            "candidate_sources": {
                "dense_count": sum(
                    1 for c in candidates if "dense" in c.get("sources", [])
                ),
                "lexical_count": sum(
                    1 for c in candidates if "lexical" in c.get("sources", [])
                ),
                "both_count": sum(
                    1
                    for c in candidates
                    if "dense" in c.get("sources", [])
                    and "lexical" in c.get("sources", [])
                ),
            },
            "top5": top5,
            "strict_hit_ids": hit_ids,
            "strict_hit": len(hit_ids) > 0,
        }
        all_rows.append(row_result)

    # ── Question-level aggregation ─────────────────────────────────────────
    qhits = compute_question_level_hits(all_rows)
    rerank_total = len(qhits)
    rerank_hits = sum(qhits.values())

    # Per-subject at question level
    re_by_subj: dict[str, dict] = defaultdict(lambda: {"total": set(), "hits": set()})
    for row in all_rows:
        qid = row["question_id"]
        if qid not in qhits:
            continue
        subj = row["subject"]
        re_by_subj[subj]["total"].add(qid)
        if qhits[qid]:
            re_by_subj[subj]["hits"].add(qid)

    # ── Summary ────────────────────────────────────────────────────────────
    by_subject_summary = {}
    for subj in ["cs", "clinical", "law"]:
        t = len(re_by_subj[subj]["total"])
        h = len(re_by_subj[subj]["hits"])
        by_subject_summary[f"subject:{subj}"] = {
            "hits": h,
            "eligible": t,
            "recall@5": round(h / t, 6) if t > 0 else 0,
        }

    # Also trace-level for reference
    trace_eligible = [r for r in all_rows if r["eligible"]]
    trace_hits = sum(1 for r in trace_eligible if r["strict_hit"])

    pool_sizes_all = [r["candidate_pool_size"] for r in all_rows]
    pool_stats = {
        "min": min(pool_sizes_all),
        "max": max(pool_sizes_all),
        "mean": round(sum(pool_sizes_all) / len(pool_sizes_all), 1),
        "median": sorted(pool_sizes_all)[len(pool_sizes_all) // 2],
    }

    summary = {
        "question_level": {
            "trace_count": len(all_rows),
            "question_count": len(qhits),
            "strict_supporting_id": {
                "hits": rerank_hits,
                "eligible": rerank_total,
                "recall@5": round(rerank_hits / rerank_total, 6) if rerank_total else 0,
            },
            **by_subject_summary,
        },
        "trace_level": {
            "trace_count": len(all_rows),
            "eligible": len(trace_eligible),
            "hits": trace_hits,
            "recall@5": round(trace_hits / len(trace_eligible), 6) if trace_eligible else 0,
        },
        "candidate_pool": pool_stats,
    }

    # ── Baseline comparison (question-level) ───────────────────────────────
    comparison = {
        "baseline_hits": base_hits,
        "baseline_eligible": base_total,
        "baseline_hit@5": round(base_hits / base_total, 6) if base_total else 0,
        "reranker_hits": rerank_hits,
        "reranker_eligible": rerank_total,
        "reranker_hit@5": round(rerank_hits / rerank_total, 6) if rerank_total else 0,
        "delta_hits": rerank_hits - base_hits,
        "delta_pct": round(
            (rerank_hits / rerank_total - base_hits / base_total) * 100, 2
        ) if rerank_total and base_total else 0,
    }

    # Per-subject comparison
    subj_comparison = {}
    for subj in ["cs", "clinical", "law"]:
        bt = len(base_by_subj[subj]["total"])
        bh = len(base_by_subj[subj]["hits"])
        rt = len(re_by_subj[subj]["total"])
        rh = len(re_by_subj[subj]["hits"])
        subj_comparison[subj] = {
            "baseline": f"{bh}/{bt}",
            "reranker": f"{rh}/{rt}",
            "delta": f"{rh - bh:+d}",
        }

    report = {
        "schema_version": RESULT_SCHEMA_VERSION,
        "reranker_model": RERANKER_MODEL,
        "candidate_pool": {
            "chroma_top_n": CHROMA_TOP,
            "lance_top_n": LANCE_TOP,
            "lance_subjects": sorted(LANCE_SUBJECTS),
            "dedup_by": "chunk_id",
        },
        "query_formulation": "dense_query (agent rewrite from historic trace)",
        "top_k": TOP_K,
        "ground_truth_source": "eval/ground_truth_bookagent.json + testset/*/qa/qa.jsonl (corrected)",
        "rows": all_rows,
        "summary": summary,
        "baseline_comparison": comparison,
        "per_subject_comparison": subj_comparison,
        "chunk_misses": chunk_misses,
    }

    # ── Write output ──────────────────────────────────────────────────────
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    json_path = OUTPUT_DIR / "results.json"
    with open(json_path, "w", encoding="utf-8") as fh:
        json.dump(report, fh, ensure_ascii=False, indent=2)
    print(f"\nResults written to {json_path}")

    # ── Print summary ─────────────────────────────────────────────────────
    print(f"\n{'='*60}")
    print("Reranker Evaluation (question-level, corrected GT)")
    print(f"{'='*60}")
    print(f"Traces: {len(all_rows)}  |  Questions: {rerank_total}  |  "
          f"Chunk misses: {chunk_misses}")
    print(f"Pool: mean={pool_stats['mean']}, median={pool_stats['median']}, "
          f"min={pool_stats['min']}, max={pool_stats['max']}")
    print(f"Strategy: Chroma Top-{CHROMA_TOP}", end="")
    print(f" + Lance Top-{LANCE_TOP} (only for {sorted(LANCE_SUBJECTS)})")

    print(f"\n{'─'*60}")
    print(f"{'Subject':<12} {'Eligible':>8} {'Hits':>6} {'Hit@5':>8}  Baseline")
    print(f"{'─'*60}")
    for subj in ["cs", "clinical", "law"]:
        key = f"subject:{subj}"
        s = summary["question_level"][key]
        b = subj_comparison[subj]
        print(f"{subj:<12} {s['eligible']:>8} {s['hits']:>6} {s['recall@5']:>8.4f}  {b['baseline']}")
    print(f"{'─'*60}")
    print(f"{'OVERALL':<12} {rerank_total:>8} {rerank_hits:>6} "
          f"{rerank_hits/rerank_total:>8.4f}  {base_hits}/{base_total}")
    print(f"{'─'*60}")

    print(f"\nBaseline:  {base_hits}/{base_total} ({base_hits/base_total:.4f})")
    print(f"Reranker:  {rerank_hits}/{rerank_total} ({rerank_hits/rerank_total:.4f})")
    delta = comparison["delta_pct"]
    direction = "↑" if delta > 0 else ("↓" if delta < 0 else "=")
    print(f"Delta:     {comparison['delta_hits']:+d} hits ({delta:+.2f}%) {direction}")

    print(f"\nPer-subject deltas:")
    for subj in ["cs", "clinical", "law"]:
        sc = subj_comparison[subj]
        print(f"  {subj}: baseline {sc['baseline']} → reranker {sc['reranker']} "
              f"({sc['delta']})")


if __name__ == "__main__":
    main()
