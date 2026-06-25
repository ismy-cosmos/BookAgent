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
        "id": "calc-001", "type": "calc", "question": "问题", "expected_tool": "calculate",
        "triggered_tool": "calculate", "tool_args": '{"expression":"1+1"}',
        "format_ok": True, "tool_accuracy_ok": True,
        "final_answer": "答案", "fill_ok": None,
        "total_tokens": 100, "latency_s": 1.5,
    }]
    out = tmp_path / "result.csv"
    save_csv(rows, str(out))
    assert out.exists()
    reader = list(csv.DictReader(open(out)))
    assert len(reader) == 1
    expected_cols = {"id", "type", "question", "expected_tool", "triggered_tool",
                     "format_ok", "tool_accuracy_ok",
                     "final_answer", "fill_ok", "total_tokens", "latency_s"}
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


def test_run_model_returns_agent_turn_list():
    from pipeline.agent.verify_tools import _run_model
    from pipeline.agent.client import AgentTurn
    from pipeline.agent.executor import StubExecutor

    mock_turn = AgentTurn(
        format_ok=True,
        triggered_tool="calculate",
        fill_ok=None,
        final_answer="42",
        total_tokens=10,
        prompt_tokens=7, completion_tokens=3,   # 新增
        latency_s=0.1,
        question="?",
        tool_args={"expression": "6*7"},
    )

    with patch("pipeline.agent.verify_tools.OllamaAgentClient") as MockClient:
        mock_client_instance = MagicMock()
        MockClient.return_value = mock_client_instance
        mock_client_instance.run.return_value = mock_turn

        result, _ = _run_model(
            cases=[{"id": "c1", "type": "calc", "question": "6*7", "expected_tool": "calculate", "expected_answer": "42"}],
            model="test-model",
            executor=StubExecutor(),
            repeats=1,
            base_url="http://localhost:11434/v1",
        )

    assert isinstance(result, list)
    assert len(result) == 1
    assert result[0]["triggered_tool"] == "calculate"


def test_main_creates_csv_file(tmp_path):
    from pipeline.agent.verify_tools import main
    from pipeline.agent.client import AgentTurn

    noop_turn = AgentTurn(
        format_ok=True,
        triggered_tool=None,
        fill_ok=None,
        final_answer="no",
        total_tokens=5,
        prompt_tokens=4, completion_tokens=1,   # 新增
        latency_s=0.05,
        question="?",
        tool_args=None,
    )

    with patch("pipeline.agent.verify_tools.OllamaAgentClient") as MockClient, \
         patch("pipeline.agent.verify_tools.subprocess") as _mock_sp:
        mock_client_instance = MagicMock()
        MockClient.return_value = mock_client_instance
        mock_client_instance.run.return_value = noop_turn

        main([
            "--cases", "eval/tool_calling_cases.jsonl",
            "--models", "test-model",
            "--output-dir", str(tmp_path),
            "--base-url", "http://localhost:11434/v1",
        ])

    assert any(tmp_path.glob("*.csv"))


def test_percentile_median():
    from pipeline.agent.verify_tools import _percentile
    assert _percentile([1.0, 2.0, 3.0, 4.0, 5.0], 0.5) == pytest.approx(3.0)


def test_percentile_p95():
    from pipeline.agent.verify_tools import _percentile
    vals = [float(i) for i in range(1, 21)]  # 1.0 .. 20.0
    result = _percentile(vals, 0.95)
    assert 19.0 <= result <= 20.0


def test_percentile_single_element():
    from pipeline.agent.verify_tools import _percentile
    assert _percentile([5.0], 0.5) == pytest.approx(5.0)
    assert _percentile([5.0], 0.95) == pytest.approx(5.0)


def test_save_csv_includes_new_columns(tmp_path):
    from pipeline.agent.verify_tools import save_csv
    rows = [{
        "id": "c1", "type": "calc", "run": 1, "question": "q",
        "expected_tool": "calculate", "triggered_tool": "calculate",
        "tool_args": "{}", "format_ok": True, "tool_accuracy_ok": True,
        "final_answer": "42", "fill_ok": None,
        "total_tokens": 60, "prompt_tokens": 40, "completion_tokens": 20,
        "latency_s": 1.0,
    }]
    out = tmp_path / "r.csv"
    save_csv(rows, str(out))
    reader = list(csv.DictReader(open(out)))
    for col in ("run", "prompt_tokens", "completion_tokens"):
        assert col in reader[0], f"missing column: {col}"
