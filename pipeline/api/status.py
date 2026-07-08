from __future__ import annotations

_busy = False
_busy_book_id: str | None = None


def get_status() -> dict:
    return {
        "busy": _busy,
        "reason": "ingesting" if _busy else "idle",
        "book_id": _busy_book_id,
    }
