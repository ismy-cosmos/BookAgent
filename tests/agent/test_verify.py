import csv
import json
import pytest
from pathlib import Path
from unittest.mock import MagicMock, patch


def _write_cases(path: Path, cases: list[dict]) -> None:
    with open(path, "w") as f:
        for c in cases:
            f.write(json.dumps(c, ensure_ascii=False) + "\n")


CALC_CASE = {"id": "calc-001", "type": "calc", "question": "0.5 × 70 是多少？",
             "expected_tool": "calculate", "expected_answer": "35"}
RET_CASE  = {"id": "ret-001",  "type": "retrieve", "question": "注意力公式？",
             "expected_tool": "retrieve",  "expected_answer": None}
NOOP_CASE = {"id": "noop-001", "type": "noop", "question": "你好",
             "expected_tool": None, "expected_answer": None}


def test_load_cases_parses_jsonl(tmp_path):
    from pipeline.agent.verify_tools import load_cases
    p = tmp_path / "cases.jsonl"
    _write_cases(p, [CALC_CASE, RET_CASE])
    cases = load_cases(str(p))
    assert len(cases) == 2
    assert cases[0]["id"] == "calc-001"


def test_compute_metrics_format_ok():
    from pipeline.agent.verify_tools import compute_metrics
    rows = [
        {"type": "calc", "expected_tool": "calculate", "triggered_tool": "calculate", "format_ok": True},
        {"type": "calc", "expected_tool": "calculate", "triggered_tool": "calculate", "format_ok": False},
        {"type": "calc", "expected_tool": "calculate", "triggered_tool": "calculate", "format_ok": True},
    ]
    m = compute_metrics(rows)
    assert abs(m["format_ok"] - 2/3) < 0.01


def test_compute_metrics_trigger_precision():
    from pipeline.agent.verify_tools import compute_metrics
    rows = [
        {"type": "calc",     "expected_tool": "calculate", "triggered_tool": "calculate", "format_ok": True},
        {"type": "calc",     "expected_tool": "calculate", "triggered_tool": None,        "format_ok": True},
        {"type": "retrieve", "expected_tool": "retrieve",  "triggered_tool": "retrieve",  "format_ok": True},
        {"type": "noop",     "expected_tool": None,        "triggered_tool": None,        "format_ok": True},
    ]
    m = compute_metrics(rows)
    assert abs(m["trigger_precision"] - 2/3) < 0.01


def test_compute_metrics_trigger_specificity():
    from pipeline.agent.verify_tools import compute_metrics
    rows = [
        {"type": "noop", "expected_tool": None, "triggered_tool": None,         "format_ok": True},
        {"type": "noop", "expected_tool": None, "triggered_tool": "retrieve",   "format_ok": True},
    ]
    m = compute_metrics(rows)
    assert m["trigger_specificity"] == pytest.approx(0.5)


def test_compute_metrics_tool_accuracy():
    from pipeline.agent.verify_tools import compute_metrics
    rows = [
        {"type": "calc",     "expected_tool": "calculate", "triggered_tool": "calculate", "format_ok": True},
        {"type": "retrieve", "expected_tool": "retrieve",  "triggered_tool": "calculate", "format_ok": True},
        {"type": "retrieve", "expected_tool": "retrieve",  "triggered_tool": "retrieve",  "format_ok": True},
    ]
    m = compute_metrics(rows)
    assert m["tool_accuracy"] == pytest.approx(2/3)


def test_save_csv_writes_correct_columns(tmp_path):
    from pipeline.agent.verify_tools import save_csv
    rows = [{
        "id": "calc-001", "type": "calc", "question": "问题", "run": 1,
        "triggered_tool": "calculate", "tool_args": '{"expression":"1+1"}',
        "format_ok": True, "tool_accuracy": True,
        "final_answer": "答案", "fill_ok_manual": "",
        "total_tokens": 100, "latency_s": 1.5,
    }]
    out = tmp_path / "result.csv"
    save_csv(rows, str(out))
    assert out.exists()
    reader = list(csv.DictReader(open(out)))
    assert len(reader) == 1
    expected_cols = {"id", "type", "question", "run", "triggered_tool",
                     "tool_args", "format_ok", "tool_accuracy",
                     "final_answer", "fill_ok_manual", "total_tokens", "latency_s"}
    assert expected_cols.issubset(set(reader[0].keys()))


def test_is_passing_all_metrics():
    from pipeline.agent.verify_tools import is_passing
    good = {"format_ok": 0.97, "trigger_precision": 0.95,
            "trigger_specificity": 0.94, "tool_accuracy": 0.92}
    assert is_passing(good) is True


def test_is_passing_fails_on_low_metric():
    from pipeline.agent.verify_tools import is_passing
    bad = {"format_ok": 0.97, "trigger_precision": 0.80,  # < 0.90
           "trigger_specificity": 0.94, "tool_accuracy": 0.92}
    assert is_passing(bad) is False
