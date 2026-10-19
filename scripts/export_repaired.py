"""Exports verified repairs from a run log as the Group 6 deliverable for Groups 7/8.

Only samples whose final attempt passed Lean *and* the semantic audit are exported.
Each record carries the broken input, the repaired proof, the repair trace and the
provenance needed to re-verify it (see docs/output_contract_group6.md).

Usage:
    python3 scripts/export_repaired.py --run-id <run_id> --data data/errors/errors_1k.jsonl \
        [--out data/repaired/] [--sample data_sample/repaired_sample_50.jsonl]
"""

import argparse
import gzip
import hashlib
import json
import sys
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

SCHEMA_VERSION = "repaired-v1"


def repaired_record(entry: dict[str, Any], sample: dict[str, Any],
                    provenance: dict[str, Any]) -> dict[str, Any]:
    """One repaired-v1 record from a successful outcome and its input sample.

    Args:
        entry: RepairOutcome.to_dict() of a successful repair.
        sample: The input record (error_id, seed_id, source, category, statement, code).
        provenance: verified_by, run_id, git_commit, strategy, model.
    """
    code = entry["attempts"][-1]["candidate_code"]
    return {
        "schema_version": SCHEMA_VERSION,
        "error_id": entry["error_id"],
        "seed_id": sample.get("seed_id"),
        "source": sample.get("source"),
        "error_category": sample.get("category"),
        "statement": sample.get("statement"),
        "broken_code": sample["code"],
        "repaired_code": code,
        "repaired_sha256": hashlib.sha256(code.encode()).hexdigest(),
        "repair_trace": [
            {k: a.get(k) for k in ("attempt", "engine", "rule", "category", "status",
                                    "audit_passed", "audit_reasons", "input_tokens",
                                    "output_tokens", "verify_latency_ms", "llm_latency_ms")}
            for a in entry["attempts"]
        ],
        "attempts_used": entry["attempts_used"],
        "total_tokens": entry["total_tokens"],
        "verified_by": provenance.get("verified_by", "unknown"),
        "run_id": provenance.get("run_id"),
        "git_commit": provenance.get("git_commit"),
        "strategy": provenance.get("strategy"),
        "model": provenance.get("model") if entry["total_tokens"] else None,
    }


def build_records(run: dict[str, Any], log_entries: list[dict[str, Any]],
                  samples: dict[str, dict[str, Any]]) -> list[dict[str, Any]]:
    """Joins successful log entries with their dataset samples."""
    provenance = {
        "verified_by": run["software"].get("lean", "unknown"),
        "run_id": run["run_id"],
        "git_commit": run["git_commit"],
        "strategy": run["parameters"]["strategy"],
        "model": run["parameters"]["model"],
    }
    return [repaired_record(e, samples[e["error_id"]], provenance) for e in log_entries
            if e.get("success") and e.get("attempts") and e.get("error_id") in samples]


def main() -> None:
    parser = argparse.ArgumentParser(description="Export verified repairs")
    parser.add_argument("--run-id", required=True)
    parser.add_argument("--raw", default="results/raw")
    parser.add_argument("--data", default="data/errors/errors_1k.jsonl")
    parser.add_argument("--out", default="data/repaired")
    parser.add_argument("--sample", default="", help="Also write the first N=50 to this path")
    args = parser.parse_args()

    raw = Path(args.raw)
    run = json.loads((raw / f"run_{args.run_id}.json").read_text(encoding="utf-8"))
    with gzip.open(raw / "logs" / f"{args.run_id}.jsonl.gz", "rt", encoding="utf-8") as f:
        entries = [json.loads(line) for line in f if line.strip()]
    with open(args.data, encoding="utf-8") as f:
        samples = {r["error_id"]: r for r in map(json.loads, f)}

    records = build_records(run, entries, samples)
    out_dir = Path(args.out)
    out_dir.mkdir(parents=True, exist_ok=True)
    jsonl = out_dir / f"repaired_{args.run_id}.jsonl"
    with open(jsonl, "w", encoding="utf-8") as f:
        for r in records:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")
    try:
        import pyarrow as pa
        import pyarrow.parquet as pq

        flat = [{**r, "repair_trace": json.dumps(r["repair_trace"])} for r in records]
        pq.write_table(pa.Table.from_pylist(flat), out_dir / f"repaired_{args.run_id}.parquet")
    except ImportError:
        pass
    if args.sample:
        with open(args.sample, "w", encoding="utf-8") as f:
            for r in records[:50]:
                f.write(json.dumps(r, ensure_ascii=False) + "\n")
    print(f"[OK] {len(records)}/{len(entries)} verified repairs -> {jsonl}")


if __name__ == "__main__":
    main()
