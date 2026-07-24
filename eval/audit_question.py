"""对 qa.jsonl 里的题目跑真实 answer() 管线，dump 回答 + 检索到的chunk全文，供人工审查。
用法: python eval/audit_question.py [--subject cs|clinical|law] cs-b001 cs-b002 ...
--subject 默认 cs。依赖对应学科的隔离评测库 book_id='<subject>-eval'
（.chroma-eval-<subject>，搭建方式见
docs/superpowers/plans/2026-07-20-cs-testset-audit-expansion.md Task 1，
clinical/law 是同一套模式换学科名）。
"""
from __future__ import annotations
import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from pipeline.agent.answer import answer
from pipeline.agent.client import OllamaAgentClient
from pipeline.agent.executor import RealExecutor
from pipeline.embed import Embedder
from pipeline.store import ChromaStore

_MODEL = "qwen3:q4km"


class LoggingExecutor(RealExecutor):
    """RealExecutor 的审查专用子类：额外把模型自己组织的 retrieve query 打印出来。
    审查检索质量必须知道模型实际发了什么 query，不能拿题目原文代替——两者常常不同。"""

    def _retrieve(self, args: dict) -> str:
        print(f"\n  [retrieve调用] query={args.get('query', '')!r}  k={args.get('k', 5)}")
        return super()._retrieve(args)


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--subject", default="cs", choices=["cs", "clinical", "law"])
    ap.add_argument("ids", nargs="*")
    args = ap.parse_args()

    if not args.ids:
        print("用法: python eval/audit_question.py [--subject cs|clinical|law] cs-b001 cs-b002 ...")
        sys.exit(1)

    book_id = f"{args.subject}-eval"
    chroma_dir = str(Path(__file__).parent.parent / f".chroma-eval-{args.subject}")
    qa_file = Path(__file__).parent / f"testset/{args.subject}/qa/qa.jsonl"

    qa_items = {}
    for line in open(qa_file, encoding="utf-8"):
        if line.strip():
            item = json.loads(line)
            qa_items[item["id"]] = item

    store = ChromaStore(persist_dir=chroma_dir)
    embedder = Embedder(device="cpu")
    executor = LoggingExecutor(book_id=book_id, embedder=embedder, store=store)
    client = OllamaAgentClient(model=_MODEL, executor=executor)

    for qid in args.ids:
        item = qa_items[qid]
        q = item["question"]
        print(f"\n{'=' * 100}\n[{qid}] ({item['question_type']}) {q}")
        print(f"标准答案: {item.get('standard_answer', '')!r}")
        print(f"source_location: {item.get('source_location', '')}")
        print(f"qa.jsonl里的supporting_chunks: {item.get('supporting_chunks', [])}")

        result = answer(q, history=[], client=client)
        print(f"\n--- 回答 ---\n{result.answer}")
        print(f"\n--- 引用的 {len(result.citations)} 个chunk ---")

        chunk_ids = list(dict.fromkeys(c.chunk_id for c in result.citations))
        full = {r["chunk_id"]: r for r in store.get(book_id, chunk_ids)} if chunk_ids else {}
        for c in result.citations:
            r = full.get(c.chunk_id, {})
            print(f"\n  chunk_id={c.chunk_id}  source={c.source_file}  score={c.score}"
                  f"  page={r.get('page_start')}-{r.get('page_end')}")
            print(f"  content: {(r.get('content') or '')[:1200]}")


if __name__ == "__main__":
    main()
