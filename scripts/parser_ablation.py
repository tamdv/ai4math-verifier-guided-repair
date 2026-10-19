"""Offline parser ablation: what does each part of the error parser buy the hybrid router?

Replays the 1K hold-out hybrid k=1 runs under weaker parsers without new LLM calls:
  full            v0.2 parser: consequence filtering + missing-import inference (as run)
  no_consequence  earliest error wins even when it is the `unsolved goals` consequence
  no_import_infer message-only classification, no source-code check for IMP_02
  naive           both switched off (first error by position, message only)
  no_parser       every sample goes to the LLM (equals llm_only k=1)

Counterfactual per sample and repeat:
  * same first attempt as logged (same engine and candidate) -> logged outcome;
  * routed to the LLM -> outcome of the paired llm_only k=1 run (same prompt, T=0, cached);
  * a different rule candidate -> verified now with the local Lean REPL (--verify), else counted
    as unknown and reported as a bound.

Usage:
    python scripts/parser_ablation.py [--verify] [--output results/figures]
"""

import argparse
import collections
import csv
import gzip
import json
import statistics
import sys
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.error_parser import ErrorCategory, LeanErrorParser, RepairRoute  # noqa: E402
from src.llm_repair import strip_comments  # noqa: E402
from src.repair_pipeline import RULE_ROUTES, _sha  # noqa: E402
from src.rule_repair import RuleRepairEngine  # noqa: E402
from src.semantic_auditor import audit  # noqa: E402

RAW = Path("results/raw")
DATA = Path("data/errors/errors_1k.jsonl")
# (hybrid k=1, llm_only k=1) pairs on the 1K hold-out, gemini-3.5-flash-lite, run back to back.
PAIRS = [
    ("exp-hybrid-b1-w4-20261017101423-570b33", "exp-llm_only-b1-w4-20261017100929-5d501e"),
    ("exp-hybrid-b1-w4-20261017103802-1c7c05", "exp-llm_only-b1-w4-20261017103401-f64327"),
    ("exp-hybrid-b1-w4-20261017110053-3c408c", "exp-llm_only-b1-w4-20261017105652-6fbf4b"),
]
VARIANTS = ("full", "no_consequence", "no_import_infer", "naive", "no_parser")


def label(diagnostics: list[dict[str, Any]], code: str,
          variant: str) -> tuple[ErrorCategory | None, RepairRoute | None]:
    """Primary (category, route) under a parser variant."""
    if variant == "no_parser":
        return None, None
    errors = [d for d in diagnostics if d.get("severity") == "error"]
    if variant in ("full", "no_import_infer"):
        causes = [d for d in errors if not d.get("message", "").lower().startswith("unsolved goals")]
        errors = causes or errors
    use_code = code if variant in ("full", "no_consequence") else None
    if errors:
        first = min(errors, key=lambda d: (d.get("line") or 0, d.get("column") or 0))
        return LeanErrorParser.classify_message(first.get("message", ""), use_code)
    sorry = [d for d in diagnostics if "sorry" in d.get("message", "")]
    if sorry:
        return LeanErrorParser.classify_message(sorry[0]["message"], use_code)
    return None, None


def first_attempt(sample: dict[str, Any], variant: str,
                  rules: RuleRepairEngine) -> tuple[str, str | None, str | None]:
    """(engine, rule, candidate) of hybrid attempt 1; mirrors RepairPipeline._propose."""
    code = strip_comments(sample["code"])
    diags = sample["diagnostics"]
    category, route = label(diags, code, variant)
    msg = next((d["message"] for d in diags if d.get("severity") == "error"), "")
    if category is not None and route in RULE_ROUTES:
        res = rules.repair_file(code, category.value, msg)
        if res:
            return "rule", res.rule_applied, res.repaired_code
    return "llm", None, None


def load_log(run_id: str) -> dict[str, dict[str, Any]]:
    with gzip.open(RAW / "logs" / f"{run_id}.jsonl.gz", "rt", encoding="utf-8") as f:
        return {e["error_id"]: e for e in map(json.loads, f)}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--verify", action="store_true", help="Verify new rule candidates with Lean")
    parser.add_argument("--output", default="results/figures")
    args = parser.parse_args()

    samples = {}
    with open(DATA, encoding="utf-8") as f:
        for r in map(json.loads, f):
            if r["split"] == "holdout":
                samples[r["error_id"]] = r
    rules = RuleRepairEngine()
    plans = {v: {eid: first_attempt(s, v, rules) for eid, s in samples.items()} for v in VARIANTS}

    # Label agreement with the injected category on synthetic samples.
    synth = [s for s in samples.values() if s["source"] == "synthetic"]
    agreement = {}
    for v in VARIANTS[:-1]:
        hits = sum(1 for s in synth if (label(s["diagnostics"], strip_comments(s["code"]), v)[0]
                                        or ErrorCategory.UNKNOWN).value == s["intended_category"])
        agreement[v] = hits / len(synth)

    # New rule candidates never verified in any logged run.
    logs = [(load_log(h), load_log(l)) for h, l in PAIRS]
    known: dict[str, bool] = {}
    for hyb, _ in logs:
        for e in hyb.values():
            for a in e["attempts"]:
                known[a["candidate_sha256"]] = bool(a["audit_passed"])
    pending = {_sha(c): (eid, c) for v in VARIANTS for eid, (eng, _, c) in plans[v].items()
               if eng == "rule" and c is not None and _sha(c) not in known}
    if pending and args.verify:
        from src.lean_repl import LeanREPLVerifier

        verifier = LeanREPLVerifier(timeout_s=60)
        try:
            for digest, (eid, cand) in pending.items():
                res = verifier.verify(cand)
                known[digest] = audit(cand, res, samples[eid]["statement"]).passed
        finally:
            verifier.close()

    rows = []
    for v in VARIANTS:
        rates, tokens, rule_share, unknown = [], [], [], 0
        for hyb, llm in logs:
            ok = tok = n_rule = 0
            for eid, (eng, _, cand) in plans[v].items():
                if eng == "llm":
                    e = llm[eid]
                    ok += bool(e["success"])
                    tok += e["total_tokens"]
                    continue
                n_rule += 1
                digest = _sha(cand)
                if digest in known:
                    ok += known[digest]
                else:
                    unknown += 1
            rates.append(ok / len(samples))
            tokens.append(tok / len(samples))
            rule_share.append(n_rule / len(samples))
        changed = sum(1 for eid in samples if plans[v][eid] != plans["full"][eid])
        rows.append({
            "variant": v,
            "label_agreement": round(agreement.get(v, float("nan")), 4),
            "routed_to_rule": round(statistics.mean(rule_share), 4),
            "first_attempt_changed": changed,
            "success_median": round(statistics.median(rates), 4),
            "success_min": round(min(rates), 4),
            "success_max": round(max(rates), 4),
            "tokens_per_sample": round(statistics.mean(tokens), 1),
            "unverified_candidates": unknown // len(logs),
        })

    # Sanity: the full variant must reproduce every logged hybrid first attempt.
    mismatch = collections.Counter()
    for hyb, _ in logs:
        for eid, e in hyb.items():
            a = e["attempts"][0] if e["attempts"] else None
            eng, _, cand = plans["full"][eid]
            logged = "rule" if a and a["engine"] == "rule" else "llm"
            if logged != eng or (eng == "rule" and a["candidate_sha256"] != _sha(cand)):
                mismatch[eid] += 1
    out = Path(args.output)
    out.mkdir(parents=True, exist_ok=True)
    with open(out / "table_parser_ablation.csv", "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0]))
        w.writeheader()
        w.writerows(rows)
    from src.provenance import write_run_record

    write_run_record(
        "parser-ablation",
        {"pairs": PAIRS, "variants": list(VARIANTS), "verify": args.verify},
        {"rows": rows, "replay_mismatch": len(mismatch),
         "newly_verified": len(pending) if args.verify else 0},
        data_version=f"{DATA.name}@{_sha(DATA.read_text(encoding='utf-8'))[:12]}",
        seed=42, timeout=60.0, status="SUCCESS" if not mismatch else "PARTIAL")
    print(f"holdout={len(samples)} synthetic={len(synth)} reps={len(logs)} "
          f"replay_mismatch={len(mismatch)} newly_verified={len(pending) if args.verify else 0}")
    for r in rows:
        print(r)


if __name__ == "__main__":
    main()
