#!/usr/bin/env bash
# BookAgent dev environment setup
# Usage: bash setup.sh [--cpu]   (--cpu skips CUDA torch)
set -euo pipefail

PYTHON=python3.12
VENV=bookagent.venv
CPU_ONLY=false
[[ "${1:-}" == "--cpu" ]] && CPU_ONLY=true

# ── 1. Checks ────────────────────────────────────────────────────────────────
command -v $PYTHON >/dev/null || { echo "ERROR: python3.12 not found"; exit 1; }
command -v ollama  >/dev/null || echo "WARN: ollama not found — model serving unavailable"
command -v pnpm    >/dev/null || { echo "ERROR: pnpm not found"; exit 1; }

echo "Python: $($PYTHON --version)"

# ── 2. Venv ──────────────────────────────────────────────────────────────────
if [ ! -d "$VENV" ]; then
    $PYTHON -m venv "$VENV"
    echo "Created $VENV"
fi
source "$VENV/bin/activate"
pip install --upgrade pip

# ── 3. PyTorch ───────────────────────────────────────────────────────────────
if $CPU_ONLY; then
    pip install torch --index-url https://download.pytorch.org/whl/cpu
    echo "Installed torch (CPU)"
else
    pip install torch --index-url https://download.pytorch.org/whl/cu128
    echo "Installed torch (CUDA 12.8)"
fi

# ── 4. Dependencies ──────────────────────────────────────────────────────────
pip install -r requirements-dev.txt
echo "Installed requirements"

# ── 4b. Pre-download surya models ──────────────────────────────────────────────
# surya-ocr 运行时按需从 S3 下载模型，首次下载失败会阻塞 PDF 导入。
# 提前预热所有模型，setup 后 PDF 导入直接走本地缓存、不走网络。
# 需要网络访问 models.datalab.to（国内可能需要代理）。
echo "Warming up surya models (first-time download, requires network)..."
python -c "
from marker.models import create_model_dict
models = create_model_dict()
for name, m in models.items():
    if hasattr(m, 'model'):
        print(f'  {name} loaded to {next(m.model.parameters()).device}')
    else:
        print(f'  {name} ready')
print('All surya models cached.')
" || echo 'WARN: surya model download failed — PDF import may fail on first use'

# ── 4.5 WhisperX (isolated venv) ─────────────────────────────────────────────
WHISPERX_VENV=whisperx.venv
if [ ! -d "$WHISPERX_VENV" ]; then
    $PYTHON -m venv "$WHISPERX_VENV"
    echo "Created $WHISPERX_VENV"
fi
if $CPU_ONLY; then
    "$WHISPERX_VENV/bin/pip" install torch --index-url https://download.pytorch.org/whl/cpu
else
    "$WHISPERX_VENV/bin/pip" install torch --index-url https://download.pytorch.org/whl/cu128
fi
"$WHISPERX_VENV/bin/pip" install -r requirements-whisperx.txt
echo "Installed whisperx (isolated venv)"
echo "NOTE: 说话人分离(--diarize)功能需要额外手动下载一次gated模型，见 requirements-whisperx.txt 顶部注释"

# ── 4.6 Frontend (JS deps only — Rust/Tauri 系统依赖不在这一步处理) ──────────
(cd frontend && pnpm install)
echo "Installed frontend JS dependencies"

# ── 5. Smoke test ────────────────────────────────────────────────────────────
python -m pytest tests/ --collect-only -q 2>&1 | tail -3
echo ""
echo "Setup complete. Activate: source $VENV/bin/activate"
