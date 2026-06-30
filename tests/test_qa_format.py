import json
import pytest
from pathlib import Path

QA_PATH = Path("eval/testset/cs/qa/qa.jsonl")
VALID_TYPES = {"事实题", "计算题", "无答案题", "音频题"}
VALID_SUBJECTS = {"cs", "clinical", "law"}


def load_qa():
    lines = QA_PATH.read_text(encoding="utf-8").strip().splitlines()
    return [json.loads(ln) for ln in lines if ln.strip()]


@pytest.fixture
def qa_list():
    return load_qa()


def test_required_fields(qa_list):
    required = {"id", "subject", "question_type", "question",
                 "standard_answer", "supporting_chunks", "source_location"}
    for item in qa_list:
        missing = required - item.keys()
        assert not missing, f"{item['id']} missing fields: {missing}"


def test_question_type_valid(qa_list):
    for item in qa_list:
        assert item["question_type"] in VALID_TYPES, (
            f"{item['id']} invalid type: {item['question_type']}"
        )


def test_subject_valid(qa_list):
    for item in qa_list:
        assert item["subject"] in VALID_SUBJECTS, (
            f"{item['id']} invalid subject: {item['subject']}"
        )


def test_no_duplicate_ids(qa_list):
    ids = [item["id"] for item in qa_list]
    assert len(ids) == len(set(ids)), f"Duplicate IDs: {[i for i in ids if ids.count(i) > 1]}"


def test_supporting_chunks_is_list(qa_list):
    for item in qa_list:
        assert isinstance(item["supporting_chunks"], list), (
            f"{item['id']} supporting_chunks must be list"
        )


def test_no_answer_question_rules(qa_list):
    for item in qa_list:
        if item["question_type"] == "无答案题":
            assert item["standard_answer"] == "", (
                f"{item['id']} 无答案题 standard_answer must be empty string"
            )
            assert item["supporting_chunks"] == [], (
                f"{item['id']} 无答案题 supporting_chunks must be []"
            )


def test_source_location_not_empty(qa_list):
    for item in qa_list:
        assert item["source_location"].strip(), (
            f"{item['id']} source_location must not be empty"
        )


def test_question_not_empty(qa_list):
    for item in qa_list:
        assert item["question"].strip(), f"{item['id']} question must not be empty"


def test_factual_has_answer(qa_list):
    for item in qa_list:
        if item["question_type"] in {"事实题", "计算题", "音频题"}:
            assert item["standard_answer"].strip(), (
                f"{item['id']} {item['question_type']} must have non-empty standard_answer"
            )
