"""Run the 60-item CS testset through BookAgent's real answer() pipeline.

Produces two things in one pass (reuses the same real LLM calls):
  1. eval/results_bookagent.csv   — same schema as BookAgent-Baseline's results_baseline.csv,
     for eval.compare (Token / Hit@5 / latency).
  2. eval/tool_calling_cs60.csv   — tool-calling accuracy per question_type
     (计算题→calculate, 事实题/音频题→retrieve, 无答案题→should not fabricate a citation).

Hit@5 ground truth comes from eval/ground_truth_bookagent.json (derived by
eval/derive_ground_truth.py from source_location, human-eyeballed where the
automated page/section match was ambiguous — see that file's comments).

Usage:
    python eval/run_cs60_bookagent.py
Requires: book_id 'cs-eval-60' already ingested into .chroma-eval-cs60
    (see scripts/ingest.py invocation in this session's history).
"""
from __future__ import annotations
import csv
import json
import sys
import tiktoken
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from pipeline.agent.answer import answer
from pipeline.agent.client import OllamaAgentClient, NO_CITATION_TAG
from pipeline.agent.executor import RealExecutor
from pipeline.embed import Embedder
from pipeline.store import ChromaStore

_BOOK_ID = "cs-eval-60"
_CHROMA_DIR = ".chroma-eval-cs60"
_MODEL = "qwen3:q4km"
_QA_FILE = Path(__file__).parent / "testset/cs/qa/qa.jsonl"
_GT_FILE = Path(__file__).parent / "ground_truth_bookagent.json"

_ENC = tiktoken.get_encoding("cl100k_base")

_EXPECTED_TOOL = {
    "计算题": "calculate",
    "事实题": "retrieve",
    "音频题": "retrieve",
    "无答案题": "retrieve",  # 应该仍尝试检索，正确行为是检索后发现无据可查
}


def main() -> None:
    qa_items = [json.loads(l) for l in open(_QA_FILE) if l.strip()]
    ground_truth = json.load(open(_GT_FILE))

    store = ChromaStore(persist_dir=_CHROMA_DIR)
    count = store.count(_BOOK_ID)
    if count == 0:
        print(f"[错误] book_id '{_BOOK_ID}' 在 {_CHROMA_DIR} 中没有数据，请先 ingest。")
        sys.exit(1)
    print(f"book '{_BOOK_ID}' 共 {count} 个 chunk，开始跑 {len(qa_items)} 题（单轮，无历史）...\n")

    # 单条查询走 CPU embedder（Embedder 类文档明确写这是给 RealExecutor.retrieve
    # 这类单次查询场景用的），把 GPU 让给常驻的 Ollama 对话模型，避免两边抢显存 OOM
    # （之前用 device=None 自动检测 GPU 时，跟已驻留的 qwen3:q4km 撞了）
    embedder = Embedder(device="cpu")
    executor = RealExecutor(book_id=_BOOK_ID, embedder=embedder, store=store)
    client = OllamaAgentClient(model=_MODEL, executor=executor)

    bench_rows = []
    tool_rows = []

    for i, item in enumerate(qa_items, start=1):
        q = item["question"]
        result = answer(q, history=[], client=client)

        cited_chunk_ids = [c.chunk_id for c in result.citations]
        gt_ids = ground_truth.get(item["id"], {}).get("chunk_ids", [])
        gt_method = ground_truth.get(item["id"], {}).get("method", "")
        if gt_ids:
            hit = bool(set(cited_chunk_ids) & set(gt_ids))
        else:
            hit = False  # no_location_expected 类题目没有"正确chunk"，不计入命中

        # tiktoken 估算 input_tokens（answer() 只返回 total_tokens，这里近似拆分：
        # 用 tiktoken 编码问题文本作 input 参考，不是 Ollama 真实 prompt_tokens，
        # 仅用于跟 baseline 的 input/output 拆分列对齐格式，token 对比以 total_tokens 为准）
        q_tokens = len(_ENC.encode(q))
        out_tokens = len(_ENC.encode(result.answer))
        in_tokens = max(result.total_tokens - out_tokens, q_tokens)

        bench_rows.append({
            "question": q,
            "answer": result.answer,
            "hit_at_5": hit,
            "input_tokens": in_tokens,
            "output_tokens": out_tokens,
            "total_tokens": result.total_tokens,
            "latency_s": round(result.latency_s, 3),
            "sources": "|".join(cited_chunk_ids),
        })

        expected_tool = _EXPECTED_TOOL.get(item["question_type"], "retrieve")
        no_answer_correct = None
        if item["question_type"] == "无答案题":
            no_answer_correct = NO_CITATION_TAG in result.answer or not cited_chunk_ids
        tool_rows.append({
            "id": item["id"],
            "question_type": item["question_type"],
            "expected_tool": expected_tool,
            "triggered_tool": result.triggered_tool,
            "attempted_retrieve": result.attempted_retrieve,
            "used_calculate": result.used_calculate,
            "tool_accuracy_ok": result.triggered_tool == expected_tool,
            "no_answer_correct": no_answer_correct,
            "hit_at_5": hit,
            "gt_method": gt_method,
            "total_tokens": result.total_tokens,
            "latency_s": round(result.latency_s, 3),
        })

        tag = "✓" if hit else ("·" if not gt_ids else "✗")
        print(f"[{i:>2}/{len(qa_items)}] {tag} tool={result.triggered_tool!s:<10} "
              f"tok={result.total_tokens:>5} {q[:40]}")

    with open(Path(__file__).parent / "results_bookagent.csv", "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=list(bench_rows[0].keys()))
        w.writeheader()
        w.writerows(bench_rows)

    with open(Path(__file__).parent / "tool_calling_cs60.csv", "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=list(tool_rows[0].keys()))
        w.writeheader()
        w.writerows(tool_rows)

    n = len(qa_items)
    n_with_gt = sum(1 for r in tool_rows if r["gt_method"] != "no_location_expected")
    hits = sum(1 for r in tool_rows if r["hit_at_5"])
    tool_ok = sum(1 for r in tool_rows if r["tool_accuracy_ok"])
    no_ans_items = [r for r in tool_rows if r["no_answer_correct"] is not None]
    no_ans_ok = sum(1 for r in no_ans_items if r["no_answer_correct"])
    avg_tok = sum(r["total_tokens"] for r in tool_rows) / n
    avg_lat = sum(r["latency_s"] for r in tool_rows) / n

    print(f"\n── BookAgent CS60 Summary ────────────────────")
    print(f"Hit@5 (有ground truth的{n_with_gt}题内): {hits}/{n_with_gt} = {hits/n_with_gt:.1%}")
    print(f"工具调用准确率:      {tool_ok}/{n} = {tool_ok/n:.1%}")
    print(f"无答案题正确拒答率: {no_ans_ok}/{len(no_ans_items)} = {no_ans_ok/len(no_ans_items):.1%}" if no_ans_items else "")
    print(f"Avg tokens: {avg_tok:.0f}   Avg latency: {avg_lat:.2f}s")
    print(f"Saved: eval/results_bookagent.csv, eval/tool_calling_cs60.csv")


if __name__ == "__main__":
    main()
