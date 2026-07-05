"""Interactive CLI for manually testing RealExecutor + multi-turn agent (human-driven e2e).

Complements scripts/e2e_ask.py (fixed question list, scripted review): this one lets you
type your own questions and watch multi-turn history / citations / get_chunk re-hydration
behave in real time.

Prerequisites:
    1. Ollama running locally with the target model pulled.
    2. Real data ingested into the target book, e.g.:
        python scripts/ingest.py --book-id java-ch1-e2e \
            --file eval/testset/cs/raw/book/java-ch1-e2e.epub \
            --dir eval/testset/cs/raw/pic/

Usage:
    python scripts/ask_cli.py --book-id java-ch1-e2e [--model qwen3:q4km] [--chroma-dir .chroma]

Type a question and press Enter. Type 'exit' or press Ctrl-D to quit.
"""
from __future__ import annotations
import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from pipeline.agent.answer import answer
from pipeline.agent.client import OllamaAgentClient
from pipeline.agent.executor import RealExecutor
from pipeline.embed import Embedder
from pipeline.store import ChromaStore


def main() -> None:
    parser = argparse.ArgumentParser(description="Interactive multi-turn Q&A against a book's RealExecutor")
    parser.add_argument("--book-id", required=True)
    parser.add_argument("--model", default="qwen3:q4km")
    parser.add_argument("--chroma-dir", default=None)
    args = parser.parse_args()

    store = ChromaStore(persist_dir=args.chroma_dir) if args.chroma_dir else ChromaStore()
    count = store.count(args.book_id)
    if count == 0:
        print(f"[错误] book_id '{args.book_id}' 在 chroma 中没有数据，请先运行 ingest。")
        sys.exit(1)
    print(f"book '{args.book_id}' 共 {count} 个 chunk。输入问题开始对话，输入 exit 退出。\n")

    # device="cpu": single-query retrieve() embeds in ~0.3s on CPU either way; keeping this
    # off GPU leaves VRAM for the LLM's own layers (measured: 21/37 -> 30/37 with embedder off GPU).
    embedder = Embedder(device="cpu")
    executor = RealExecutor(book_id=args.book_id, embedder=embedder, store=store)
    client = OllamaAgentClient(model=args.model, executor=executor)

    history: list = []
    while True:
        try:
            question = input("Q: ").strip()
        except EOFError:
            print()
            break
        if not question or question.lower() in ("exit", "quit"):
            break

        result = answer(question, history=history, client=client)
        print(f"A: {result.answer}")
        print(f"   [工具: {result.triggered_tool}  tokens: {result.total_tokens}  延迟: {result.latency_s:.1f}s]")
        if result.citations:
            for c in result.citations:
                print(f"   - [{c.element_type}] {c.citation}  (chunk_id={c.chunk_id})")
        print()
        history = result.history


if __name__ == "__main__":
    main()