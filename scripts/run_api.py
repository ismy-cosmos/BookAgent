"""Launch the BookAgent local HTTP API (FastAPI + uvicorn).

Usage:
    python scripts/run_api.py [--host 127.0.0.1] [--port 8420]

前端（Tauri）启动时会把这个脚本当 sidecar 子进程拉起。
"""
from __future__ import annotations
import argparse
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

import uvicorn


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=int(os.environ.get("BOOKAGENT_API_PORT", 8420)))
    args = parser.parse_args()
    uvicorn.run("pipeline.api.app:app", host=args.host, port=args.port)


if __name__ == "__main__":
    main()
