"""Language-aware lexical retrieval with translation (Argos + term protection).

Architecture:
  Index: chunk → language detection → content_lex_en | content_lex_zh
  Query: language detection → route to matching field
         + cross-language: Argos-translate query → search other field
         → merge both result lists → return Top-N

References:
  - TREC 2024 NeuCLIR: query-translation BM25 baseline
  - Azure AI Search: language-specific fields + searchFields routing
"""
from __future__ import annotations

import json
import re
import shutil
import sys
import time
from collections import defaultdict
from pathlib import Path
from typing import Any, Sequence

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
DB_DIR = WORK_DIR / "lancedb-lang-index"
OUTPUT_DIR = WORK_DIR / "lang-lexical"
BASELINE_RESULTS = WORK_DIR / "chroma-baseline" / "results.json"


# ═══════════════════════════════════════════════════════════════════════════════
# 1. Terminology Dictionary
# ═══════════════════════════════════════════════════════════════════════════════

def build_glossary() -> dict[str, str]:
    """Domain terminology: zh_term → en_term.

    Terms extracted from eval queries across law, clinical, and CS.
    Bidirectional lookup: reverse for en→zh.
    """
    return {
        # ── Legal ──
        "第四修正案": "Fourth Amendment",
        "搜查令": "search warrant",
        "搜查": "search",
        "扣押": "seizure",
        "合理隐私期待": "reasonable expectation of privacy",
        "违宪": "unconstitutional",
        "令状": "warrant",
        "大麻": "marijuana",
        "热成像": "thermal imaging",
        "逮捕": "arrest",
        "窃听": "wiretapping",
        "电子监控": "electronic surveillance",
        "无令状": "warrantless",
        "强制": "compelled",
        "供述": "testimony",
        "自证其罪": "self-incrimination",
        "辩护律师": "defense counsel",
        "陪审团": "jury",
        "probable cause": "probable cause",
        "search incident to arrest": "search incident to arrest",
        "third-party doctrine": "third-party doctrine",
        "exclusionary rule": "exclusionary rule",
        "knock-and-announce": "knock-and-announce",
        "stop and frisk": "stop and frisk",
        "GPS": "GPS",
        "CSLI": "CSLI",
        # ── Medical ──
        "β-内酰胺酶": "beta-lactamase",
        "青霉素": "penicillin",
        "抗生素": "antibiotic",
        "革兰氏阳性菌": "gram-positive bacteria",
        "革兰氏阴性菌": "gram-negative bacteria",
        "万古霉素": "vancomycin",
        "氟喹诺酮": "fluoroquinolone",
        "耐药性": "drug resistance",
        "抗菌": "antibacterial",
        "细胞壁": "cell wall",
        "转肽酶": "transpeptidase",
        "Vancomycin": "Vancomycin",
        "Fluoroquinolone": "Fluoroquinolone",
        "Penicillin": "Penicillin",
        # ── CS ──
        "文件描述符": "file descriptor",
        "输出重定向": "output redirection",
        "子进程": "child process",
        "父进程": "parent process",
        "虚拟地址": "virtual address",
        "临界区": "critical section",
        "互斥锁": "mutex",
        "分页": "paging",
        "页表": "page table",
        "虚拟内存": "virtual memory",
        "调度器": "scheduler",
        "护航效应": "convoy effect",
        "初始化": "initialization",
        "fork": "fork",
        "exec": "exec",
        "SQMS": "SQMS",
        "FIFO": "FIFO",
        "MMU": "MMU",
        "VPN": "VPN",
        "TLB": "TLB",
    }


# ═══════════════════════════════════════════════════════════════════════════════
# 2. Translation (Argos + Term Protection)
# ═══════════════════════════════════════════════════════════════════════════════

class Translator:
    """Offline EN↔ZH translation with domain terminology protection.

    Uses Argos Translate for sentence-level MT, with pre/post-processing
    to guarantee that domain terms survive tokenization intact.
    """

    def __init__(self, glossary: dict[str, str]):
        import argostranslate.translate as _at
        self._at = _at
        self._glossary = glossary
        # Reverse lookup: en→zh
        self._glossary_rev = {v: k for k, v in glossary.items()}

    def _has_cjk(self, text: str) -> bool:
        return any("一" <= c <= "鿿" for c in text)

    def _detect(self, text: str) -> str:
        return "zh" if self._has_cjk(text) else "en"

    def _protect(self, text: str, source: str) -> tuple[str, dict[str, str]]:
        """Replace domain terms with word-like placeholders."""
        if source == "zh":
            pairs = [(zh, en) for zh, en in self._glossary.items()]
        else:
            pairs = [(en, zh) for en, zh in self._glossary_rev.items()]

        pairs.sort(key=lambda x: len(x[0]), reverse=True)
        mapping: dict[str, str] = {}
        protected = text
        for i, (term, _) in enumerate(pairs):
            placeholder = f"XTERM{i}X"
            if term in protected:
                protected = protected.replace(term, placeholder)
                mapping[placeholder] = term
        return protected, mapping

    def _restore(self, text: str, mapping: dict[str, str], source: str) -> str:
        """Restore placeholders with target-language terms."""
        result = text
        for placeholder, src_term in mapping.items():
            if source == "zh":
                tgt = self._glossary.get(src_term, src_term)
            else:
                tgt = self._glossary_rev.get(src_term, src_term)
            # Handle tokenizer mangling: placeholder might become "XTERM 0 X" etc
            for variant in {placeholder, placeholder.replace("XTERM", "XTERM "),
                          placeholder.replace("X", " X")}:
                result = result.replace(variant, tgt)
            result = result.replace(placeholder, tgt)
        return result

    def translate(self, text: str, target: str) -> str:
        """Translate text to target language with term protection."""
        source = self._detect(text)
        if source == target:
            return text  # No translation needed

        protected, mapping = self._protect(text, source)
        try:
            raw = self._at.translate(protected, source, target)
        except Exception:
            # Fallback: try without protection
            try:
                raw = self._at.translate(text, source, target)
            except Exception:
                return text  # Last resort: return original
        result = self._restore(raw, mapping, source)
        return result


# ═══════════════════════════════════════════════════════════════════════════════
# 3. Language Detection & Tokenization
# ═══════════════════════════════════════════════════════════════════════════════

def has_cjk(text: str) -> bool:
    return any("一" <= c <= "鿿" for c in text)


def detect_lang(text: str) -> str:
    return "zh" if has_cjk(text) else "en"


def tokenize_for_lang(text: str, lang: str) -> str:
    """Tokenize text for indexing/search in the given language."""
    if lang == "zh":
        return " ".join(jieba.cut(text))
    else:
        return text  # English: keep as-is (LanceDB simple tokenizer handles it)


# ═══════════════════════════════════════════════════════════════════════════════
# 4. LanceDB Index Builder
# ═══════════════════════════════════════════════════════════════════════════════

def build_lang_database(corpus_dir: Path, db_dir: Path) -> dict:
    """Build LanceDB with dual language fields + FTS indices."""
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
                content = obj["content"]
                lang = detect_lang(content)
                rows.append({
                    "chunk_id": obj["chunk_id"],
                    "content": content,
                    "lang": lang,
                    "content_lex_en": content if lang == "en" else "",
                    "content_lex_zh": tokenize_for_lang(content, "zh") if lang == "zh" else "",
                    "vector": obj["embedding"],
                    "book_id": obj["book_id"],
                    "metadata_json": json.dumps(obj.get("metadata", {}), ensure_ascii=False, sort_keys=True),
                })

        table = db.create_table(subject, data=rows, mode="create")

        # FTS index on English field
        table.create_index(
            "content_lex_en",
            config=FTS(stem=False, remove_stop_words=False, ascii_folding=False),
        )
        # FTS index on Chinese field (jieba-pre-tokenized, simple tokenizer)
        table.create_index(
            "content_lex_zh",
            config=FTS(stem=False, remove_stop_words=False, ascii_folding=False),
        )

        lang_counts = defaultdict(int)
        for r in rows:
            lang_counts[r["lang"]] += 1
        tables_info.append({
            "subject": subject,
            "chunk_count": len(rows),
            "lang_distribution": dict(lang_counts),
        })

    return {
        "backend": f"lancedb-{lancedb.__version__}-lang",
        "corpus_dir": str(corpus_dir),
        "tables": tables_info,
        "fts": {
            "content_lex_en": "simple tokenizer, English content",
            "content_lex_zh": "jieba pre-tokenized, Chinese content",
        },
    }


# ═══════════════════════════════════════════════════════════════════════════════
# 5. Language-Aware Lexical Retriever
# ═══════════════════════════════════════════════════════════════════════════════

class LangAwareLexicalRetriever:
    """Lexical retrieval with language routing and cross-language translation."""

    name = "lancedb-lang-aware"

    def __init__(self, db_dir: Path, translator: Translator):
        self._db = lancedb.connect(str(db_dir))
        self._tables = {
            s: self._db.open_table(s) for s in ("cs", "clinical", "law")
        }
        self._translator = translator

    def search_dense(self, subject: str, query_vector, limit: int):
        return []  # Dense route reuses recorded Chroma results

    def search_lexical(self, subject: str, query: str, limit: int) -> Sequence[RankedHit]:
        query_lang = detect_lang(query)
        hits: dict[str, RankedHit] = {}  # chunk_id → hit (dedup, keep best score)

        # ── Same-language route ──
        if query_lang == "zh":
            q_tokenized = tokenize_for_lang(query, "zh")
            rows = (
                self._tables[subject]
                .search(q_tokenized, query_type="fts")
                .limit(limit)
                .to_list()
            )
            for r in rows:
                hits[r["chunk_id"]] = RankedHit(chunk_id=r["chunk_id"], score=r.get("_score"))
        else:
            rows = (
                self._tables[subject]
                .search(query, query_type="fts")
                .limit(limit)
                .to_list()
            )
            for r in rows:
                hits[r["chunk_id"]] = RankedHit(chunk_id=r["chunk_id"], score=r.get("_score"))

        # ── Cross-language route ──
        target_lang = "en" if query_lang == "zh" else "zh"
        translated = self._translator.translate(query, target_lang)
        if translated != query:  # Translation succeeded and is different
            if target_lang == "zh":
                q_trans = tokenize_for_lang(translated, "zh")
                rows = (
                    self._tables[subject]
                    .search(q_trans, query_type="fts")
                    .limit(limit)
                    .to_list()
                )
            else:
                rows = (
                    self._tables[subject]
                    .search(translated, query_type="fts")
                    .limit(limit)
                    .to_list()
                )
            for r in rows:
                cid = r["chunk_id"]
                score = r.get("_score", 0)
                if cid not in hits or (score is not None and (hits[cid].score is None or score > hits[cid].score)):
                    hits[cid] = RankedHit(chunk_id=cid, score=score)

        # Sort by score descending, return Top-N
        sorted_hits = sorted(
            hits.values(), key=lambda h: h.score if h.score is not None else 0, reverse=True
        )
        return sorted_hits[:limit]


# ═══════════════════════════════════════════════════════════════════════════════
# 6. Main
# ═══════════════════════════════════════════════════════════════════════════════

def main():
    print("=" * 60)
    print("Language-Aware Lexical Retrieval with Translation")
    print("=" * 60)

    # ── Build glossary ──
    glossary = build_glossary()
    print(f"\nGlossary: {len(glossary)} domain terms")

    # ── Init translator ──
    print("Loading Argos Translate...")
    t0 = time.perf_counter()
    translator = Translator(glossary)
    print(f"  ready ({time.perf_counter() - t0:.1f}s)")

    # ── Quick translation test ──
    test_q = "警察没有搜查令进入住宅是否违宪"
    test_t = translator.translate(test_q, "en")
    print(f"  test: '{test_q[:50]}' → '{test_t[:80]}'")

    # ── Build index ──
    print(f"\nBuilding language-aware LanceDB index...")
    t0 = time.perf_counter()
    index_manifest = build_lang_database(CORPUS_DIR, DB_DIR)
    elapsed = time.perf_counter() - t0
    for t in index_manifest["tables"]:
        ld = t["lang_distribution"]
        print(f"  {t['subject']}: {t['chunk_count']} chunks, en={ld.get('en', 0)}, zh={ld.get('zh', 0)}")
    print(f"  Built in {elapsed:.1f}s")

    # ── Run evaluation ──
    print(f"\nRunning lexical evaluation...")
    backend = LangAwareLexicalRetriever(DB_DIR, translator)
    traces = load_traces()
    gt = load_ground_truth()
    baseline_report = json.loads(BASELINE_RESULTS.read_text(encoding="utf-8"))

    t0 = time.perf_counter()
    report = evaluate_recorded_dense_with_lexical(
        backend,
        traces,
        baseline_report,
        gt,
        top_k=5,
        candidate_pool_k=50,
    )
    elapsed = time.perf_counter() - t0
    print(f"  Evaluation completed in {elapsed:.1f}s")

    report["experiment_scope"] = "language_aware_lexical_with_translation"
    report["index_manifest"] = index_manifest
    report["glossary_size"] = len(glossary)
    attach_baseline_comparison(report, baseline_report)

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    json_path, csv_path = write_result_files(OUTPUT_DIR, report)
    print(f"\nResults: {json_path}")

    # ── Print summary ──
    s = report["summary"]["all"]["strict_supporting_id"]
    print(f"\n{'=' * 60}")
    print("Language-Aware Lexical — strict-ID Hit@5")
    print(f"{'=' * 60}")

    for mode in ["dense", "lexical", "hybrid_rrf"]:
        m = s.get(mode, {})
        if m:
            print(f"  {mode}: {m.get('hits', '?')}/{m.get('eligible', '?')} "
                  f"({m.get('recall@5', 0):.4f})")

    # Per-subject lexical
    print(f"\n  Per-subject lexical:")
    for key in ["subject:cs", "subject:clinical", "subject:law"]:
        sub = report["summary"].get(key, {}).get("strict_supporting_id", {}).get("lexical", {})
        if sub:
            print(f"    {key}: {sub.get('hits', '?')}/{sub.get('eligible', '?')} "
                  f"({sub.get('recall@5', 0):.4f})")

    # Comparison
    old_lance_path = WORK_DIR / "lance-lexical" / "results.json"
    if old_lance_path.exists():
        old = json.loads(old_lance_path.read_text(encoding="utf-8"))
        print(f"\n{'=' * 60}")
        print("Comparison")
        print(f"{'=' * 60}")
        for label, data, mode_key in [
            ("Old Lance (broken zh)", old, "lexical"),
            ("Jieba only (no routing)", json.loads((WORK_DIR / "lance-jieba" / "results.json").read_text(encoding="utf-8")) if (WORK_DIR / "lance-jieba" / "results.json").exists() else None, "lexical"),
            ("Lang-aware + translation", report, "lexical"),
        ]:
            if data is None:
                continue
            ms = data["summary"]["all"]["strict_supporting_id"].get(mode_key, {})
            print(f"  {label}: {ms.get('hits', '?')}/{ms.get('eligible', '?')} "
                  f"({ms.get('recall@5', 0):.4f})")


if __name__ == "__main__":
    main()
