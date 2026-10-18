# Output Contract — Group 6 → Groups 7 / 8 (`repaired-v1`)

Group 6 delivers **Lean 4 proofs that Lean accepted and that passed the semantic audit**, together with
the error taxonomy label of the original failure and the full repair trace.

| Item | Value |
|---|---|
| Producer | `scripts/export_repaired.py --run-id <run_id>` |
| Formats | JSONL (one record per line) and Parquet (`repair_trace` as a JSON string) |
| Location | `data/repaired/repaired_<run_id>.{jsonl,parquet}` (not in Git); sample: `data_sample/repaired_sample_50.jsonl` |
| Toolchain | Lean 4.35.0, Mathlib v4.35.0 (`lean_ws/lake-manifest.json`) — consumers must re-verify on other versions |
| Inclusion rule | final attempt compiled, no `sorry`, no forbidden construct, theorem statement unchanged |

## Fields
| Field | Type | Meaning |
|---|---|---|
| `schema_version` | str | `repaired-v1` |
| `error_id`, `seed_id` | str | sample id; seed theorem id (Lean Workbook problem id) |
| `source` | str | `synthetic` (injected error) or `natural` (Mathlib version drift) |
| `error_category` | str | taxonomy v0.2 code of the original error (SYN_01 … TAC_07) |
| `statement` | str | theorem statement the repair must prove (audited) |
| `broken_code`, `repaired_code` | str | full Lean files before / after repair |
| `repaired_sha256` | str | SHA-256 of `repaired_code` (dedup / integrity) |
| `repair_trace` | list | per attempt: engine (`rule` / `llm_diagnostic` / `llm_blind`), rule id, category, Lean status, audit result, tokens, latencies |
| `attempts_used`, `total_tokens` | int | cost of the repair |
| `verified_by` | str | `lean --version` of the verifying worker |
| `run_id`, `git_commit`, `strategy`, `model` | str | provenance; `model` is null for rule-only repairs |

## Delivered snapshots (dataset v1.0)
| Run | Data | Repairs |
|---|---|---|
| `exp-llm_only-b3-w4-20261017101714-3f7a7e` | 1K hold-out (284) | 185 |
| `exp-hybrid-b1-w4-20261017111634-84f517` | 10K hold-out (2,907) | 991 |

## Guarantees and limits
- Every record was compiled by Lean in a fresh environment (Mathlib imported, no state leaks between checks).
- Statement equality is textual after whitespace normalisation (conservative).
- Repairs of `TMO_05` samples may restore a higher `maxHeartbeats`; downstream timing analyses should note it.
