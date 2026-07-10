from pathlib import Path

import pytest

from pipeline.agent.schema import ChatTurn, Citation
from pipeline.api import conversations as conv


def test_create_conversation_returns_record_with_id(tmp_path):
    record = conv.create_conversation(str(tmp_path), "ostep")
    assert record["book_id"] == "ostep"
    assert record["title"] == "新对话"
    assert record["turns"] == []
    assert len(record["id"]) > 0


def test_list_conversations_empty(tmp_path):
    assert conv.list_conversations(str(tmp_path), "ostep") == []


def test_list_conversations_after_create(tmp_path):
    a = conv.create_conversation(str(tmp_path), "ostep")
    b = conv.create_conversation(str(tmp_path), "ostep")
    ids = {c["id"] for c in conv.list_conversations(str(tmp_path), "ostep")}
    assert ids == {a["id"], b["id"]}


def test_load_conversation_missing_raises(tmp_path):
    with pytest.raises(FileNotFoundError):
        conv.load_conversation(str(tmp_path), "ostep", "does-not-exist")


def test_delete_conversation_missing_raises(tmp_path):
    with pytest.raises(FileNotFoundError):
        conv.delete_conversation(str(tmp_path), "ostep", "does-not-exist")


def test_delete_conversation_removes_it(tmp_path):
    record = conv.create_conversation(str(tmp_path), "ostep")
    conv.delete_conversation(str(tmp_path), "ostep", record["id"])
    assert conv.list_conversations(str(tmp_path), "ostep") == []


def test_append_turn_updates_title_and_turns(tmp_path):
    record = conv.create_conversation(str(tmp_path), "ostep")
    turn = ChatTurn(
        question="fork() 和 exec() 的区别是什么？",
        answer="fork 创建子进程副本……",
        citations=[Citation(chunk_id="c1", source_file="ch3.pdf", element_type="text", citation="第3章", score=0.9)],
    )

    updated = conv.append_turn(str(tmp_path), "ostep", record["id"], turn)

    assert updated["title"] == "fork() 和 exec() 的区别是什么？"[:20]
    assert len(updated["turns"]) == 1
    assert updated["turns"][0]["question"] == turn.question
    assert updated["turns"][0]["citations"][0]["chunk_id"] == "c1"


def test_history_from_record_roundtrips_chat_turns(tmp_path):
    record = conv.create_conversation(str(tmp_path), "ostep")
    turn = ChatTurn(question="Q1", answer="A1", citations=[])
    conv.append_turn(str(tmp_path), "ostep", record["id"], turn)

    reloaded = conv.load_conversation(str(tmp_path), "ostep", record["id"])
    history = conv.history_from_record(reloaded)

    assert len(history) == 1
    assert isinstance(history[0], ChatTurn)
    assert history[0].question == "Q1"
    assert history[0].answer == "A1"


def test_write_uses_atomic_replace(tmp_path, monkeypatch):
    calls = []
    original_replace = Path.replace

    def spy_replace(self, target):
        calls.append((str(self), str(target)))
        return original_replace(self, target)

    monkeypatch.setattr(Path, "replace", spy_replace)
    conv.create_conversation(str(tmp_path), "ostep")

    assert len(calls) == 1
    assert calls[0][0].endswith(".tmp")


def test_write_failure_does_not_corrupt_existing_file(tmp_path, monkeypatch):
    record = conv.create_conversation(str(tmp_path), "ostep")
    original = conv.load_conversation(str(tmp_path), "ostep", record["id"])

    original_write_text = Path.write_text
    call_count = 0

    def flaky_write_text(self, *a, **k):
        nonlocal call_count
        call_count += 1
        raise OSError("disk full")

    monkeypatch.setattr(Path, "write_text", flaky_write_text)

    turn = ChatTurn(question="Q", answer="A", citations=[])
    with pytest.raises(OSError):
        conv.append_turn(str(tmp_path), "ostep", record["id"], turn)

    monkeypatch.setattr(Path, "write_text", original_write_text)
    reloaded = conv.load_conversation(str(tmp_path), "ostep", record["id"])
    assert reloaded == original
