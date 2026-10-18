# License & Privacy Note (Group 6)

## Licenses of what we use
| Component | License | Use |
|---|---|---|
| Goedel-LM/Lean-workbook-proofs (dataset) | MIT | seed proofs; redistributed only as small samples (`data_sample/`) |
| Lean 4, Lean REPL | Apache-2.0 | verifier |
| Mathlib 4 | Apache-2.0 | library imported by every check |
| google-genai SDK | Apache-2.0 | Gemini API client |
| Gemini API outputs | Google Generative AI terms (paid tier) | generated repairs; reviewed by Lean + audit before use |
| This repository's code | course project (PTIT INT4418) | — |

Full datasets are not committed (CLAUDE.md Rule 4); they are rebuilt with checksum-verified scripts
(`scripts/download_data.sh`, `data_sample/manifest.json`).

## Privacy
- The data are formal mathematics (theorem statements, proofs, compiler messages). **No personal data** is collected, stored or sent.
- Data sent to the Gemini API: Lean source with comments removed and Lean diagnostics only. Calls used the **paid tier** (Cloud billing via Google AI Pro credit); no free-tier data-usage terms apply to the experiment runs.
- API keys live only in `.env` (git-ignored) or Kaggle Secrets; they never appear in code, logs, run records or the cost ledger (verified by scanning the Git history for key patterns).

## Responsible use
- Repairs are accepted only after Lean verification and the semantic audit (no `sorry`/`axiom`, unchanged statement); see `docs/system_card.md`.
- AI assistance in building the system is declared in `docs/ai_use_statement.md`.
