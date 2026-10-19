"""Group 6 gateway: repair a Group 5 batch file (Data Contract v0.1) end to end.

Input : autoformalization_errors_<split>_<timestamp>_<commit>.jsonl | .parquet from Group 5
        (docs/data_contract_group5_group6.md). Required fields: candidate_id, problem_id,
        candidate_code, statement_natural, split. compiler_diagnostics are optional: every
        candidate is re-verified with our pinned Lean 4.35 + Mathlib, so diagnostics always
        match the verifier that judges the repair.
Output: <out-dir>/feedback_group5.jsonl   per-candidate status for Group 5 (contract §5)
        <out-dir>/repaired_v1.jsonl/.parquet verified repairs for Groups 7/8 (output contract)
        <out-dir>/rejected.jsonl          records that failed validation, with the reason
        results/raw/run_group5-batch-*.json  provenance record (Rule 3) + replayable log

Usage:
    python scripts/repair_batch.py --input data/group5/autoformalization_errors_holdout_....jsonl \
        --strategy hybrid --budget 3 --workers 4            # LLM: needs GEMINI_API_KEY, costs tokens
    python scripts/repair_batch.py --input data_sample/group5_input_sample.jsonl \
        --strategy rule_only --budget 3 --workers 1         # $0, no LLM
"""

import argparse
import collections
import gzip
import hashlib
import json
import sys
import time
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from scripts.export_repaired import repaired_record  # noqa: E402
from src.error_parser import LeanErrorParser  # noqa: E402
from src.mutations import theorem_statement  # noqa: E402
from src.semantic_auditor import audit  # noqa: E402

REQUIRED = ("candidate_id", "problem_id", "candidate_code", "statement_natural", "split")
STATUS_SUCCESS = "SUCCESS"
STATUS_FAILED = "FAILED"
STATUS_ALREADY_VALID = "ALREADY_VALID"
STATUS_VERIFIER_ERROR = "VERIFIER_ERROR"


def sha256(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def read_input(path: Path) -> list[dict[str, Any]]:
    """Reads a Group 5 batch file (JSONL or Parquet)."""
    if path.suffix == ".parquet":
        import pyarrow.parquet as pq

        return pq.read_table(path).to_pylist()
    with open(path, encoding="utf-8") as f:
        return [json.loads(line) for line in f if line.strip()]


def validate(records: list[dict[str, Any]]) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    """Splits records into accepted and rejected (with a reason) per the data contract."""
    accepted, rejected, seen = [], [], set()
    for rec in records:
        missing = [k for k in REQUIRED if not str(rec.get(k) or "").strip()]
        if missing:
            rejected.append({"candidate_id": rec.get("candidate_id"),
                             "reason": "missing_fields", "fields": missing})
            continue
        digest = sha256(rec["candidate_code"])
        declared = rec.get("checksum_sha256")
        if declared and declared != digest:
            rejected.append({"candidate_id": rec["candidate_id"], "reason": "checksum_mismatch"})
            continue
        if digest in seen:
            rejected.append({"candidate_id": rec["candidate_id"], "reason": "duplicate_code"})
            continue
        seen.add(digest)
        accepted.append(rec)
    return accepted, rejected


def to_sample(rec: dict[str, Any]) -> dict[str, Any]:
    """Maps a contract record onto the pipeline's sample schema."""
    code = rec["candidate_code"]
    return {
        "error_id": rec["candidate_id"],
        "seed_id": rec["problem_id"],
        "source": "group5:" + str(rec.get("source_dataset") or "unknown"),
        "split": rec["split"],
        "code": code,
        "statement": theorem_statement(code),
        "statement_natural": rec["statement_natural"],
        "diagnostics": [],
        "category": None,
    }


def process(pipeline: Any, sample: dict[str, Any]) -> dict[str, Any]:
    """Re-verifies one candidate, then repairs it if it really fails."""
    res = pipeline.verifier.verify(sample["code"])
    if res.status == "CRASH":
        return {"status": STATUS_VERIFIER_ERROR, "sample": sample, "outcome": None}
    if res.proved and audit(sample["code"], res, sample["statement"]).passed:
        return {"status": STATUS_ALREADY_VALID, "sample": sample, "outcome": None}
    sample = dict(sample, diagnostics=res.diagnostics)
    primary = LeanErrorParser.primary(res.diagnostics, sample["code"])
    sample["category"] = primary.category.value if primary else None
    outcome = pipeline.run(sample).to_dict()
    return {"status": STATUS_SUCCESS if outcome["success"] else STATUS_FAILED,
            "sample": sample, "outcome": outcome}


def feedback_row(rec: dict[str, Any], result: dict[str, Any]) -> dict[str, Any]:
    """Contract §5 feedback for Group 5."""
    outcome = result["outcome"] or {}
    attempts = outcome.get("attempts", [])
    last = attempts[-1] if attempts else {}
    engines = {a["engine"] for a in attempts}
    strategy = None
    if result["status"] == STATUS_SUCCESS:
        strategy = "rule_repair" if last.get("engine") == "rule" else "llm_repair"
    return {
        "candidate_id": rec["candidate_id"],
        "problem_id": rec["problem_id"],
        "final_status": result["status"],
        "error_category": result["sample"].get("category"),
        "repaired_code": last.get("candidate_code") if result["status"] == STATUS_SUCCESS else None,
        "repair_strategy": strategy,
        "engines_tried": sorted(engines),
        "attempts_used": outcome.get("attempts_used", 0),
        "stop_reason": outcome.get("stop_reason"),
        "last_audit_reasons": last.get("audit_reasons", []),
        "total_tokens": outcome.get("total_tokens", 0),
    }


def run_batch(records: list[dict[str, Any]], pool: Any) -> dict[str, Any]:
    """Validates, re-verifies and repairs a batch. `pool` yields PoolResult objects."""
    accepted, rejected = validate(records)
    by_id = {r["candidate_id"]: r for r in accepted}
    results: list[dict[str, Any]] = []
    errors = 0
    for pr in pool.imap((to_sample(r), r["candidate_id"]) for r in accepted):
        if isinstance(pr.result, BaseException):
            errors += 1
            results.append({"status": STATUS_VERIFIER_ERROR, "sample": {"error_id": pr.payload},
                            "outcome": None, "error": repr(pr.result)})
            continue
        results.append(pr.result)
    feedback = [feedback_row(by_id[r["sample"]["error_id"]], r) for r in results]
    return {"accepted": accepted, "rejected": rejected, "results": results,
            "feedback": feedback, "worker_errors": errors}


def write_outputs(batch: dict[str, Any], out_dir: Path, provenance: dict[str, Any]) -> dict[str, int]:
    out_dir.mkdir(parents=True, exist_ok=True)
    repaired = [repaired_record(r["outcome"], r["sample"], provenance)
                for r in batch["results"] if r["status"] == STATUS_SUCCESS]
    for name, rows in (("feedback_group5", batch["feedback"]), ("repaired_v1", repaired),
                       ("rejected", batch["rejected"])):
        with open(out_dir / f"{name}.jsonl", "w", encoding="utf-8") as f:
            for row in rows:
                f.write(json.dumps(row, ensure_ascii=False) + "\n")
    if repaired:
        try:
            import pyarrow as pa
            import pyarrow.parquet as pq

            flat = [{**r, "repair_trace": json.dumps(r["repair_trace"])} for r in repaired]
            pq.write_table(pa.Table.from_pylist(flat), out_dir / "repaired_v1.parquet")
        except ImportError:
            pass
    return {"repaired": len(repaired)}


def main() -> None:
    parser = argparse.ArgumentParser(description="Repair a Group 5 batch (Data Contract v0.1)")
    parser.add_argument("--input", required=True)
    parser.add_argument("--out-dir", default=None, help="Default: data/group5_out/<input stem>")
    parser.add_argument("--strategy", default="hybrid",
                        choices=["rule_only", "llm_only", "hybrid", "blind"])
    parser.add_argument("--budget", type=int, default=3)
    parser.add_argument("--workers", type=int, default=2)
    parser.add_argument("--provider", default="gemini")
    parser.add_argument("--model", default="gemini-3.5-flash-lite")
    parser.add_argument("--timeout", type=float, default=60.0)
    parser.add_argument("--run-cap", type=float, default=None, help="USD cap for this batch")
    parser.add_argument("--limit", type=int, default=0)
    args = parser.parse_args()

    from src.cost_guard import CostGuard, GuardedClient, ResponseCache
    from src.lean_repl import LeanREPLVerifier
    from src.llm_client import make_client
    from src.llm_repair import LLMRepairEngine
    from src.provenance import RAW_DIR, git_commit, new_run_id, software_info, write_run_record
    from src.repair_pipeline import RepairPipeline, RepairPolicy
    from src.verifier_pool import VerifierPool

    in_path = Path(args.input)
    records = read_input(in_path)
    if args.limit:
        records = records[: args.limit]
    out_dir = Path(args.out_dir or f"data/group5_out/{in_path.stem}")
    run_id = new_run_id(f"group5-batch-{args.strategy}-b{args.budget}")
    needs_llm = args.strategy != "rule_only" and args.budget > 0
    guard = CostGuard(run_id, run_cap_usd=args.run_cap) if needs_llm else None
    cache = ResponseCache() if needs_llm else None

    def factory() -> RepairPipeline:
        blind = diag = None
        if needs_llm:
            assert guard is not None
            client = GuardedClient(make_client(args.provider, args.model), guard, cache)
            blind = LLMRepairEngine(client, "blind")
            diag = LLMRepairEngine(client, "diagnostic")
        return RepairPipeline(LeanREPLVerifier(timeout_s=args.timeout),
                              RepairPolicy(args.strategy, args.budget), blind, diag)

    pool = VerifierPool(factory, args.workers, task=process)
    data_version = f"{in_path.name}@{sha256(in_path.read_bytes().decode('utf-8', 'ignore'))[:12]}"
    t0 = time.perf_counter()
    try:
        batch = run_batch(records, pool)
    except Exception as exc:  # worker startup failure: keep a FAILED record, spend nothing more
        write_run_record("group5-batch", vars(args), {"error": repr(exc)}, data_version,
                         seed=42, timeout=args.timeout, status="FAILED", run_id=run_id)
        raise
    wall = time.perf_counter() - t0

    provenance = {"verified_by": software_info().get("lean"), "run_id": run_id,
                  "git_commit": git_commit(), "strategy": args.strategy,
                  "model": args.model if needs_llm else None}
    counts = write_outputs(batch, out_dir, provenance)

    (RAW_DIR / "logs").mkdir(parents=True, exist_ok=True)
    with gzip.open(RAW_DIR / "logs" / f"{run_id}.jsonl.gz", "wt", encoding="utf-8") as log:
        for r in batch["results"]:
            log.write(json.dumps({"error_id": r["sample"].get("error_id"), "status": r["status"],
                                  **(r["outcome"] or {})}, ensure_ascii=False) + "\n")
    statuses = collections.Counter(f["final_status"] for f in batch["feedback"])
    metrics = {
        "input_records": len(records),
        "accepted": len(batch["accepted"]),
        "rejected": dict(collections.Counter(r["reason"] for r in batch["rejected"])),
        "final_status": dict(statuses),
        "repair_success_rate_of_failing": round(
            statuses[STATUS_SUCCESS] / max(1, statuses[STATUS_SUCCESS] + statuses[STATUS_FAILED]), 4),
        "repaired_exported": counts["repaired"],
        "worker_errors": batch["worker_errors"],
        "wall_time_s": round(wall, 1),
        "real_spend_usd": round(guard.run_spent, 6) if guard else 0.0,
    }
    path = write_run_record("group5-batch", vars(args), metrics, data_version,
                            seed=42, timeout=args.timeout, run_id=run_id)
    print(json.dumps(metrics, ensure_ascii=False))
    print(f"[OK] outputs -> {out_dir}  |  run record: {path}")


if __name__ == "__main__":
    main()
