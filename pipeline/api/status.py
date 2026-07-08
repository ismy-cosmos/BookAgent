from __future__ import annotations

from pipeline.api.import_queue import get_import_queue


def get_status() -> dict:
    return get_import_queue().get_status()
