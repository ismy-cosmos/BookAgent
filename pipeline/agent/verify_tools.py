"""
W1 验证 A：工具调用早期验证运行器

用法：
    # 拉取 Q4 模型（Ollama registry 有 tag）
    ollama pull qwen3-vl:8b-instruct-q4_K_M

    # 注册 Q5 模型（需先下载 GGUF）
    huggingface-cli download bartowski/Qwen_Qwen3-VL-8B-Instruct-GGUF \\
        Qwen_Qwen3-VL-8B-Instruct-Q5_K_S.gguf --local-dir models/
    ollama create bookagent-q5ks -f deploy/Modelfile.q5_k_s

    # 运行验证
    python -m pipeline.agent.verify_tools \\
        --models qwen3-vl:8b-instruct-q4_K_M bookagent-q5ks \\
        --cases eval/tool_calling_cases.jsonl \\
        --output-dir eval/
"""
from __future__ import annotations

import argparse
import csv
import json
import sys
from pathlib import Path

from pipeline.agent.client import OllamaAgentClient
from pipeline.agent.executor import StubExecutor

# Pass/fail thresholds (§D.5)
_THRESHOLDS = {
    "format_ok": 0.95,
    "trigger_precision": 0.90,
    "trigger_specificity": 0.90,
    "tool_accuracy": 0.90,
}


def load_cases(path: str) -> list[dict]:
    with open(path, encoding="utf-8") as f:
        return [json.loads(line) for line in f if line.strip()]


def compute_metrics(rows: list[dict]) -> dict:
    """Compute 4 automated metrics from raw result rows."""
    triggered_rows = [r for r in rows if r["triggered_tool"] is not None]
    should_call_rows = [r for r in rows if r["expected_tool"] is not None]
    noop_rows = [r for r in rows if r["expected_tool"] is None]

    format_ok = (
        sum(1 for r in triggered_rows if r["format_ok"]) / len(triggered_rows)
        if triggered_rows else 1.0
    )
    trigger_precision = (
        sum(1 for r in should_call_rows if r["triggered_tool"] is not None) / len(should_call_rows)
        if should_call_rows else 1.0
    )
    trigger_specificity = (
        sum(1 for r in noop_rows if r["triggered_tool"] is None) / len(noop_rows)
        if noop_rows else 1.0
    )
    tool_accuracy = (
        sum(1 for r in triggered_rows if r["triggered_tool"] == r["expected_tool"])
        / len(triggered_rows)
        if triggered_rows else 1.0
    )

    return {
        "format_ok": format_ok,
        "trigger_precision": trigger_precision,
        "trigger_specificity": trigger_specificity,
        "tool_accuracy": tool_accuracy,
    }


def is_passing(metrics: dict) -> bool:
    return all(metrics[k] >= _THRESHOLDS[k] for k in _THRESHOLDS)


def save_csv(rows: list[dict], path: str) -> None:
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    fieldnames = [
        "id", "type", "question", "run",
        "triggered_tool", "tool_args", "format_ok", "tool_accuracy",
        "final_answer", "fill_ok_manual", "total_tokens", "latency_s",
    ]
    with open(path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def _run_model(
    model: str,
    cases: list[dict],
    base_url: str,
    repeats: int,
) -> tuple[list[dict], dict]:
    executor = StubExecutor()
    client = OllamaAgentClient(model=model, executor=executor, base_url=base_url)
    rows: list[dict] = []

    for case in cases:
        for run_idx in range(1, repeats + 1):
            turn = client.run(case["question"])
            tool_acc = (
                turn.triggered_tool == case["expected_tool"]
                if turn.triggered_tool is not None
                else None
            )
            rows.append({
                "id": case["id"],
                "type": case["type"],
                "question": case["question"],
                "run": run_idx,
                "triggered_tool": turn.triggered_tool,
                "tool_args": json.dumps(turn.tool_args, ensure_ascii=False) if turn.tool_args else "",
                "format_ok": turn.format_ok,
                "tool_accuracy": tool_acc,
                "expected_tool": case["expected_tool"],  # used by compute_metrics, not in CSV
                "final_answer": turn.final_answer,
                "fill_ok_manual": "",  # human review
                "total_tokens": turn.total_tokens,
                "latency_s": round(turn.latency_s, 3),
            })

    metrics = compute_metrics(rows)
    return rows, metrics


def _print_summary(model: str, metrics: dict, avg_tokens: float, avg_latency: float) -> None:
    passed = is_passing(metrics)
    verdict = "✓ PASS" if passed else "✗ FAIL"
    print(
        f"── {model:<40} "
        f"format={metrics['format_ok']:.0%}  "
        f"precision={metrics['trigger_precision']:.0%}  "
        f"specificity={metrics['trigger_specificity']:.0%}  "
        f"tool_acc={metrics['tool_accuracy']:.0%}  "
        f"→ {verdict}  "
        f"avg_tokens={avg_tokens:.0f}  latency={avg_latency:.1f}s"
    )


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description="W1 验证 A：工具调用早期验证")
    parser.add_argument("--cases", default="eval/tool_calling_cases.jsonl")
    parser.add_argument("--models", nargs="+",
                        default=["qwen3-vl:8b-instruct-q4_K_M"])
    parser.add_argument("--repeats", type=int, default=3)
    parser.add_argument("--output-dir", default="eval/")
    parser.add_argument("--base-url", default="http://localhost:11434/v1")
    args = parser.parse_args(argv)

    cases = load_cases(args.cases)
    if not cases:
        print(f"ERROR: {args.cases} is empty", file=sys.stderr)
        sys.exit(1)
    print(f"Loaded {len(cases)} cases ({args.repeats} repeats each)\n")

    all_results: dict[str, dict] = {}

    for model in args.models:
        print(f"Running model: {model} ...")
        rows, metrics = _run_model(model, cases, args.base_url, args.repeats)

        # strip internal field before saving CSV
        csv_rows = [{k: v for k, v in r.items() if k != "expected_tool"} for r in rows]
        tag = model.replace(":", "-").replace("/", "-")
        csv_path = str(Path(args.output_dir) / f"tool_calling_result_{tag}.csv")
        save_csv(csv_rows, csv_path)

        avg_tokens = sum(r["total_tokens"] for r in rows) / len(rows)
        avg_latency = sum(r["latency_s"] for r in rows) / len(rows)
        all_results[model] = {"metrics": metrics, "avg_tokens": avg_tokens,
                               "avg_latency": avg_latency, "csv_path": csv_path}
        print(f"  → saved to {csv_path}")

    print(f"\n{'─' * 80}")
    print("SUMMARY")
    print(f"{'─' * 80}")
    for model, data in all_results.items():
        _print_summary(model, data["metrics"], data["avg_tokens"], data["avg_latency"])

    print(f"\nThresholds: format≥{_THRESHOLDS['format_ok']:.0%}  "
          f"precision≥{_THRESHOLDS['trigger_precision']:.0%}  "
          f"specificity≥{_THRESHOLDS['trigger_specificity']:.0%}  "
          f"tool_acc≥{_THRESHOLDS['tool_accuracy']:.0%}")

    passing = [m for m, d in all_results.items() if is_passing(d["metrics"])]
    failing = [m for m, d in all_results.items() if not is_passing(d["metrics"])]

    if passing:
        fastest = min(passing, key=lambda m: all_results[m]["avg_tokens"])
        print(f"\n结论：推荐默认量化 → {fastest}")
    if failing:
        print(f"未通过：{failing} — 考虑增加 JSON 修复约束或降级为 always-retrieve 模式")


if __name__ == "__main__":
    main()
