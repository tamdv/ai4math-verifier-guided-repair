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


def build_records(run: dict[str, Any], log_entries: list[dict[str, Any]],
                  samples: dict[str, dict[str, Any]]) -> list[dict[str, Any]]:
    """Joins successful log entries with their dataset samples."""
    out = []
    for e in log_entries:
        if not e.get("success") or not e.get("attempts"):
            continue
        s = samples.get(e["error_id"])
        if s is None:
            continue
        final = e["attempts"][-1]
        code = final["candidate_code"]
        out.append({
            "schema_version": SCHEMA_VERSION,
            "error_id": e["error_id"],
            "seed_id": s["seed_id"],
            "source": s["source"],
            "error_category": s["category"],
            "statement": s["statement"],
            "broken_code": s["code"],
            "repaired_code": code,
            "repaired_sha256": hashlib.sha256(code.encode()).hexdigest(),
            "repair_trace": [
                {k: a.get(k) for k in ("attempt", "engine", "rule", "category", "status",
                                        "audit_passed", "audit_reasons", "input_tokens",
                                        "output_tokens", "verify_latency_ms", "llm_latency_ms")}
                for a in e["attempts"]
            ],
            "attempts_used": e["attempts_used"],
            "total_tokens": e["total_tokens"],
            "verified_by": run["software"].get("lean", "unknown"),
            "run_id": run["run_id"],
            "git_commit": run["git_commit"],
            "strategy": run["parameters"]["strategy"],
            "model": run["parameters"]["model"] if e["total_tokens"] else None,
        })
    return out


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
