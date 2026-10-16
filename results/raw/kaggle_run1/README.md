# Kaggle run 1 (2026-10-16) — pilot / superseded

Kept as immutable evidence; **not used for report figures** (`generate_figures.py` only reads
top-level `results/raw/run_exp-*.json`).

- Hardware: Kaggle CPU, Linux x86_64, 4 vCPU, 31.3 GB RAM; Lean 4.35.0. Worker Mathlib import 11–25 s.
- Dataset v1 was truncated: `build_seeds.py` died after 800/3000 candidates (verifier exception not
  handled; fixed by STATUS_CRASH + exception-tolerant scripts), so the "10k" tier holds 2,834 samples.
- Labels predate the primary-error fix (`unsolved goals` treated as a consequence): intended-vs-Lean
  agreement 85.1% -> 95.0% when re-labelled offline from the stored diagnostics.
- LLM pilot (50 hold-out, k=1, gemini-3.5-flash-lite): blind 34% vs diagnostic 54% audited success;
  real spend $0.1153 (see results/cost_ledger.jsonl). Tokens/call: blind in 317 / out 543,
  diagnostic in 541 / out 276; no thinking tokens.
- Lean-only scale (rule_only k=1, 3 repeats, 100 / 1K / 2,834): throughput 4 vs 1 worker = 1.7x / 2.6x / 2.4x;
  run-to-run spread ~3%.
- Option C check: 601/603 stripped seeds compile; the 2 failures are 60 s wall-clock timeouts.
