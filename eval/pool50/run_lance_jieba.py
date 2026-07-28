"""Step A: Rebuild LanceDB index with jieba tokenization for Chinese content.

Heuristic: chunks/queries with CJK characters → jieba pre-tokenization;
pure ASCII/Latin → kept as-is.  No language labels, no separate fields,
no translation — minimal baseline to measure the value of Chinese-aware
tokenization vs the broken simple-tokenizer-only approach.
"""
from __future__ import annotations

import json
import shutil
import sys
import time
from pathlib import Path

import jieba
import lancedb
from lancedb.index import FTS

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(REPO_ROOT))

from eval.retrieval_evaluation import (
    RankedHit,
    attach_baseline_comparison,
    evaluate_recorded_dense_with_lexical,
    load_ground_truth,
    load_traces,
    write_result_files,
)

WORK_DIR = Path(__file__).resolve().parent
CORPUS_DIR = WORK_DIR / "corpus"
DB_DIR = WORK_DIR / "lancedb-jieba-index"
OUTPUT_DIR = WORK_DIR / "lance-jieba"
BASELINE_RESULTS = WORK_DIR / "chroma-baseline" / "results.json"


# ── Tokenization ──────────────────────────────────────────────────────────────
def _has_cjk(text: str) -> bool:
    """True if text contains any CJK Unified Ideograph."""
    return any("一" <= c <= "鿿" for c in text)


def tokenize(text: str) -> str:
    """Jieba-tokenize if text has CJK characters; otherwise keep as-is."""
    if _has_cjk(text):
        return " ".join(jieba.cut(text))
    return text


# ── Build ─────────────────────────────────────────────────────────────────────
def build_jieba_database(corpus_dir: Path, db_dir: Path) -> dict:
    """Rebuild LanceDB with jieba-tokenized content_lex field + FTS index."""
    if db_dir.exists():
        shutil.rmtree(db_dir)

    manifest = json.loads((corpus_dir / "manifest.json").read_text(encoding="utf-8"))
    db = lancedb.connect(str(db_dir))
    tables_info = []

    for item in manifest["corpora"]:
        subject = item["subject"]
        rows = []
        with open(corpus_dir / item["file"], encoding="utf-8") as fh:
            for line in fh:
                obj = json.loads(line)
                raw = obj["content"]
                rows.append({
                    "chunk_id": obj["chunk_id"],
                    "content": raw,
                    "content_lex": tokenize(raw),
                    "vector": obj["embedding"],
                    "book_id": obj["book_id"],
                    "metadata_json": json.dumps(obj.get("metadata", {}), ensure_ascii=False, sort_keys=True),
                })

        table = db.create_table(subject, data=rows, mode="create")
        table.create_index(
            "content_lex",
            config=FTS(stem=False, remove_stop_words=False, ascii_folding=False),
        )
        tables_info.append({"subject": subject, "chunk_count": len(rows)})

    return {
        "backend": f"lancedb-{lancedb.__version__}-jieba",
        "corpus_dir": str(corpus_dir),
        "tables": tables_info,
        "fts": {
            "field": "content_lex",
            "tokenization": "jieba for CJK, raw for ASCII",
            "stem": False,
            "remove_stop_words": False,
            "ascii_folding": False,
        },
    }


# ── Retriever ─────────────────────────────────────────────────────────────────
class JiebaLexicalRetriever:
    """Lexical-only adapter: jieba-tokenize query, search content_lex."""

    name = "lancedb-jieba"

    def __init__(self, db_dir: Path):
        self._db = lancedb.connect(str(db_dir))
        self._tables = {
            s: self._db.open_table(s) for s in ("cs", "clinical", "law")
        }

    def search_dense(self, subject: str, query_vector, limit: int):
        # Not used — dense route reuses recorded Chroma results
        return []

    def search_lexical(self, subject: str, query: str, limit: int):
        q_tokenized = tokenize(query)
        rows = (
            self._tables[subject]
            .search(q_tokenized, query_type="fts")
            .limit(limit)
            .to_list()
        )
        return [
            RankedHit(chunk_id=r["chunk_id"], score=r.get("_score"))
            for r in rows
        ]


# ── Main ──────────────────────────────────────────────────────────────────────
def main():
    print("Building jieba-tokenized LanceDB index...")
    t0 = time.perf_counter()
    index_manifest = build_jieba_database(CORPUS_DIR, DB_DIR)
    elapsed = time.perf_counter() - t0
    for t in index_manifest["tables"]:
        print(f"  {t['subject']}: {t['chunk_count']} chunks")
    print(f"  Built in {elapsed:.1f}s")

    print("\nRunning lexical evaluation (reusing Chroma dense results)...")
    backend = JiebaLexicalRetriever(DB_DIR)
    traces = load_traces()
    gt = load_ground_truth()
    baseline_report = json.loads(BASELINE_RESULTS.read_text(encoding="utf-8"))

    report = evaluate_recorded_dense_with_lexical(
        backend,
        traces,
        baseline_report,
        gt,
        top_k=5,
        candidate_pool_k=50,
    )
    report["experiment_scope"] = "jieba_tokenization_baseline"
    report["index_manifest"] = index_manifest
    attach_baseline_comparison(report, baseline_report)

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    json_path, csv_path = write_result_files(OUTPUT_DIR, report)
    print(f"\nResults: {json_path}")
    print(f"CSV:     {csv_path}")

    # ── Print key numbers ─────────────────────────────────────────────────
    s = report["summary"]["all"]["strict_supporting_id"]
    print(f"\n{'='*50}")
    print(f"Jieba Lexical — strict-ID Hit@5")
    print(f"{'='*50}")
    for mode in ["dense", "lexical", "hybrid_rrf"]:
        m = s.get(mode, {})
        if m:
            print(f"  {mode}: {m.get('hits', '?')}/{m.get('eligible', '?')} "
                  f"({m.get('recall@5', 0):.4f})")

    for key in ["subject:cs", "subject:clinical", "subject:law"]:
        sub = report["summary"].get(key, {}).get("strict_supporting_id", {})
        lex = sub.get("lexical", {})
        if lex:
            print(f"  {key} lexical: {lex.get('hits', '?')}/{lex.get('eligible', '?')}")

    # Compare to old Lance
    print(f"\n{'='*50}")
    print("Comparison: Jieba vs old Lance (raw simple tokenizer)")
    print(f"{'='*50}")
    old_lance_path = WORK_DIR / "lance-lexical" / "results.json"
    if old_lance_path.exists():
        old = json.loads(old_lance_path.read_text(encoding="utf-8"))
        old_s = old["summary"]["all"]["strict_supporting_id"]["lexical"]
        new_s = s["lexical"]
        print(f"  Old Lance: {old_s['hits']}/{old_s['eligible']} ({old_s['recall@5']:.4f})")
        print(f"  New Jieba: {new_s['hits']}/{new_s['eligible']} ({new_s['recall@5']:.4f})")
        delta = new_s['hits'] - old_s['hits']
        print(f"  Delta: {delta:+d} hits")


if __name__ == "__main__":
    main()
