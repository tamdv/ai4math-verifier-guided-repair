#!/usr/bin/env bash
# Deterministic download of large source data (CLAUDE.md Rule 4: not committed to Git).
set -euo pipefail
cd "$(dirname "$0")/.."
mkdir -p data/raw

fetch() {  # url dest sha256
  if [ ! -f "$2" ]; then curl -sSL -o "$2" "$1"; fi
  echo "$3  $2" | shasum -a 256 -c -
}

# Goedel-LM/Lean-workbook-proofs (MIT): 29,750 Lean 4 proofs used as seed theorems.
fetch "https://huggingface.co/datasets/Goedel-LM/Lean-workbook-proofs/resolve/main/data/train-00000-of-00001.parquet" \
  data/raw/goedel_lean_workbook_proofs.parquet \
  24fcb50eecc2ccbcc52a58c6412c6d10edbeaa9483a97d30e207fb20ef6e2677
