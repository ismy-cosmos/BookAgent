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

echo "Python: $($PYTHON --version)"

# ── 2. Venv ──────────────────────────────────────────────────────────────────
if [ ! -d "$VENV" ]; then
    $PYTHON -m venv "$VENV"
    echo "Created $VENV"
fi
source "$VENV/bin/activate"
pip install -q --upgrade pip

# ── 3. PyTorch ───────────────────────────────────────────────────────────────
if $CPU_ONLY; then
    pip install -q torch --index-url https://download.pytorch.org/whl/cpu
    echo "Installed torch (CPU)"
else
    pip install -q torch --index-url https://download.pytorch.org/whl/cu128
    echo "Installed torch (CUDA 12.8)"
fi

# ── 4. Dependencies ──────────────────────────────────────────────────────────
pip install -q -r requirements-dev.txt
echo "Installed requirements"

# ── 4.5 WhisperX (isolated venv) ─────────────────────────────────────────────
WHISPERX_VENV=whisperx.venv
if [ ! -d "$WHISPERX_VENV" ]; then
    $PYTHON -m venv "$WHISPERX_VENV"
    echo "Created $WHISPERX_VENV"
fi
if $CPU_ONLY; then
    "$WHISPERX_VENV/bin/pip" install -q torch --index-url https://download.pytorch.org/whl/cpu
else
    "$WHISPERX_VENV/bin/pip" install -q torch --index-url https://download.pytorch.org/whl/cu128
fi
"$WHISPERX_VENV/bin/pip" install -q -r requirements-whisperx.txt
echo "Installed whisperx (isolated venv)"

# ── 5. Smoke test ────────────────────────────────────────────────────────────
python -m pytest tests/ --collect-only -q 2>&1 | tail -3
echo ""
echo "Setup complete. Activate: source $VENV/bin/activate"
