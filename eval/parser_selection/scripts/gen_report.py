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
SPEED_TARGET = 15.0  # pages/min


def _load_results(results_dir: Path, parser: str) -> dict[str, dict]:
    return {
        (d := json.loads(f.read_text()))["id"]: d
        for f in sorted((results_dir / parser).glob("*.json"))
    }


def _load_scorecard(results_dir: Path) -> list[dict]:
    with open(results_dir / "scorecard.csv", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def _speed_stats(results: dict[str, dict]) -> dict:
    times = [r["elapsed_sec"] for r in results.values()
             if r.get("elapsed_sec") is not None]
    if not times:
        return {"pages_per_min": 0.0, "p50": 0.0, "p95": 0.0}
    times_sorted = sorted(times)
    n = len(times_sorted)
    p50 = statistics.median(times_sorted)
    p95 = times_sorted[min(int(n * 0.95), n - 1)]
    avg = statistics.mean(times)
    return {
        "pages_per_min": round(60.0 / avg, 1) if avg > 0 else 0.0,
        "p50": round(p50, 3),
        "p95": round(p95, 3),
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

    speed = {p: _speed_stats(all_results[p]) for p in PARSERS}
    scores = {p: _score_totals(scorecard, p) for p in PARSERS}

    lines: list[str] = ["# 解析器选型对比报告\n"]

    lines += [
        "## 1. 速度对比\n",
        "| 解析器 | pages/min | p50 延迟(s) | p95 延迟(s) | 达标(≥15) |",
        "|---|---|---|---|---|",
    ]
    for p in PARSERS:
        s = speed[p]
        ok = "✅" if s["pages_per_min"] >= SPEED_TARGET else "❌"
        lines.append(f"| {p} | {s['pages_per_min']} | {s['p50']} | {s['p95']} | {ok} |")

    lines += [
        "\n## 2. 人工评分汇总（满分 90）\n",
        "| 解析器 | detect(/30) | content(/30) | struct(/30) | 总分(/90) |",
        "|---|---|---|---|---|",
    ]
    for p in PARSERS:
        sc = scores[p]
        lines.append(
            f"| {p} | {sc['detect']} | {sc['content']} | {sc['struct']} | {sc['total']} |"
        )

    lines.append("\n## 3. 选定建议\n")
    qualified = [p for p in PARSERS if speed[p]["pages_per_min"] >= SPEED_TARGET]

    if not qualified:
        lines.append("❌ **两个解析器均未达速度要求（≥15 pages/min），需调整策略后重测。**")
        winner = None
    elif len(qualified) == 1:
        winner = qualified[0]
        loser = next(p for p in PARSERS if p != winner)
        lines.append(f"✅ **选定：`{winner}`**（`{loser}` 速度不达标，直接出局）")
    else:
        winner = max(qualified, key=lambda p: scores[p]["total"])
        other = next(p for p in qualified if p != winner)
        lines.append(
            f"✅ **选定：`{winner}`**（速度均达标；人工总分 {scores[winner]['total']} > {scores[other]['total']}）"
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
