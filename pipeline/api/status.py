from __future__ import annotations

from pipeline.api import busy_state
from pipeline.api.import_queue import get_import_queue


def get_status() -> dict:
    state = busy_state.get_state()
    pause_requested = get_import_queue().is_pause_requested()
    if state is None:
        return {"busy": False, "reason": "idle", "book_id": None,
                "pause_requested": pause_requested}
    return {"busy": True, "reason": state.reason, "book_id": state.book_id,
            "pause_requested": pause_requested}
