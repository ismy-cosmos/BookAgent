from __future__ import annotations
import json
import uuid
from datetime import datetime
from pathlib import Path

from pipeline.agent.schema import ChatTurn, Citation


def _dir(chroma_dir: str, book_id: str) -> Path:
    d = Path(chroma_dir) / ".conversations" / book_id
    d.mkdir(parents=True, exist_ok=True)
    return d


def _path(chroma_dir: str, book_id: str, conversation_id: str) -> Path:
    return _dir(chroma_dir, book_id) / f"{conversation_id}.json"


def _write(chroma_dir: str, book_id: str, record: dict) -> None:
    _path(chroma_dir, book_id, record["id"]).write_text(
        json.dumps(record, ensure_ascii=False, indent=2)
    )


def create_conversation(chroma_dir: str, book_id: str) -> dict:
    now = datetime.now().isoformat()
    record = {
        "id": uuid.uuid4().hex[:12],
        "book_id": book_id,
        "title": "新对话",
        "created_at": now,
        "updated_at": now,
        "turns": [],
    }
    _write(chroma_dir, book_id, record)
    return record


def list_conversations(chroma_dir: str, book_id: str) -> list[dict]:
    summaries = []
    for p in _dir(chroma_dir, book_id).glob("*.json"):
        record = json.loads(p.read_text())
        summaries.append({
            "id": record["id"],
            "title": record["title"],
            "updated_at": record["updated_at"],
        })
    summaries.sort(key=lambda s: s["updated_at"], reverse=True)
    return summaries


def load_conversation(chroma_dir: str, book_id: str, conversation_id: str) -> dict:
    p = _path(chroma_dir, book_id, conversation_id)
    if not p.exists():
        raise FileNotFoundError(conversation_id)
    return json.loads(p.read_text())


def delete_conversation(chroma_dir: str, book_id: str, conversation_id: str) -> None:
    p = _path(chroma_dir, book_id, conversation_id)
    if not p.exists():
        raise FileNotFoundError(conversation_id)
    p.unlink()


def _turn_to_dict(turn: ChatTurn) -> dict:
    return {
        "question": turn.question,
        "answer": turn.answer,
        "citations": [
            {
                "chunk_id": c.chunk_id,
                "source_file": c.source_file,
                "element_type": c.element_type,
                "citation": c.citation,
                "score": c.score,
            }
            for c in turn.citations
        ],
    }


def append_turn(chroma_dir: str, book_id: str, conversation_id: str, turn: ChatTurn) -> dict:
    record = load_conversation(chroma_dir, book_id, conversation_id)
    record["turns"].append(_turn_to_dict(turn))
    if len(record["turns"]) == 1:
        record["title"] = turn.question[:20]
    record["updated_at"] = datetime.now().isoformat()
    _write(chroma_dir, book_id, record)
    return record


def history_from_record(record: dict) -> list[ChatTurn]:
    return [
        ChatTurn(
            question=t["question"],
            answer=t["answer"],
            citations=[Citation(**c) for c in t.get("citations", [])],
        )
        for t in record.get("turns", [])
    ]
