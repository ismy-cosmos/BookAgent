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

# 在任何 pipeline 模块（marker/embedder/whisperx 子进程）被 import 之前设好
# 离线模式——理由见 pipeline/offline_mode.py。子进程默认继承父进程环境变量，
# 这里调一次，WhisperX 子进程也会一并覆盖到。
from pipeline.offline_mode import force_offline
force_offline()

import uvicorn


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=int(os.environ.get("BOOKAGENT_API_PORT", 8420)))
    args = parser.parse_args()
    uvicorn.run("pipeline.api.app:app", host=args.host, port=args.port)


if __name__ == "__main__":
    main()
