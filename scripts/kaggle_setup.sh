#!/usr/bin/env bash
# One-shot environment setup for a Kaggle CPU notebook (4 vCPU, ~30 GB RAM).
# Heavy artifacts (elan toolchain, Mathlib cache ~7 GB, data) live on the ephemeral
# disk under /root; only results are copied to /kaggle/working at the end.
#
# Usage (notebook cell):  !bash scripts/kaggle_setup.sh
set -euo pipefail
cd "$(dirname "$0")/.."
export PATH="$HOME/.elan/bin:$PATH"

echo "=== [1/5] elan + Lean toolchain"
if ! command -v lake >/dev/null; then
  curl -sSf https://raw.githubusercontent.com/leanprover/elan/master/elan-init.sh \
    | sh -s -- -y --no-modify-path --default-toolchain none
fi

elan default "$(cat lean_ws/lean-toolchain)"

echo "=== [2/5] Mathlib cache + Lean REPL (pinned by lean_ws/lake-manifest.json)"
(cd lean_ws && lake exe cache get && lake build repl)

echo "=== [3/5] Python dependencies"
pip install -q google-genai pyyaml psutil pyarrow pytest matplotlib

echo "=== [4/5] Source data (checksum-verified)"
bash scripts/download_data.sh

echo "=== [5/5] Unit tests"
python -m pytest tests -q

lean --version
nproc; free -g | head -2
echo "Setup complete."
