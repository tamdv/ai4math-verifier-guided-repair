"""Builds the verified seed set: correct Lean proofs that compile with current Mathlib.

Seeds come from Goedel-LM/Lean-workbook-proofs (MIT). Proofs were produced for
an older Lean/Mathlib, so each candidate is re-verified with the REPL pool and
only clean (no error, no sorry) proofs are kept as seeds. Proofs that no longer
compile (renamed lemmas, deprecated syntax, timeouts) are kept separately as
*natural* errors with their real Lean diagnostics. `maxHeartbeats 0` (unbounded)
is capped so a single proof cannot stall a worker.

Usage:
    python3 scripts/build_seeds.py --n 3000 --workers 2
"""

import argparse
import hashlib
import json
import random
import re
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.lean_repl import LeanREPLVerifier  # noqa: E402
from src.provenance import percentile, write_run_record  # noqa: E402
from src.verifier_pool import VerifierPool  # noqa: E402

SOURCE = Path("data/raw/goedel_lean_workbook_proofs.parquet")
SOURCE_SHA256 = "24fcb50eecc2ccbcc52a58c6412c6d10edbeaa9483a97d30e207fb20ef6e2677"
HEARTBEATS = 400000


def normalize(code: str) -> str:
    """Caps unbounded heartbeats so proofs terminate deterministically."""
    return re.sub(r"set_option maxHeartbeats 0\b", f"set_option maxHeartbeats {HEARTBEATS}", code)


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def main() -> None:
    parser = argparse.ArgumentParser(description="Verify seed proofs with Lean REPL")
    parser.add_argument("--n", type=int, default=3000, help="Candidates to try")
    parser.add_argument("--workers", type=int, default=2)
    parser.add_argument("--timeout", type=float, default=60.0)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--out", default="data/seeds/seeds_verified.jsonl")
    parser.add_argument("--natural-out", default="data/seeds/natural_errors.jsonl")
    args = parser.parse_args()

    if sha256_file(SOURCE) != SOURCE_SHA256:
        sys.exit(f"Checksum mismatch for {SOURCE}; re-run scripts/download_data.sh")

    import pyarrow.parquet as pq

    rows = pq.read_table(SOURCE).to_pylist()
    random.Random(args.seed).shuffle(rows)
    rows = rows[: args.n]

    items = [(normalize(r["full_proof"]), r["problem_id"]) for r in rows]
    pool = VerifierPool(lambda: LeanREPLVerifier(timeout_s=args.timeout), args.workers)

    out_path = Path(args.out)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    kept, failed, timeouts, sorry, crashes = 0, 0, 0, 0, 0
    service, waits = [], []
    t0 = time.perf_counter()
    with open(out_path, "w", encoding="utf-8") as out, open(
        args.natural_out, "w", encoding="utf-8"
    ) as natural:
        for i, pr in enumerate(pool.imap(items), 1):
            res = pr.result
            service.append(pr.service_ms)
            if isinstance(res, BaseException) or res.status == "CRASH":
                crashes += 1  # verifier failure, not a property of the proof: skip
                continue
            waits.append(pr.queue_wait_ms)
            code = items[pr.index][0]
            if res.status == "TIMEOUT":
                timeouts += 1
            elif res.errors:
                failed += 1
                natural.write(
                    json.dumps(
                        {
                            "seed_id": pr.payload,
                            "code": code,
                            "sha256": hashlib.sha256(code.encode()).hexdigest(),
                            "diagnostics": res.errors,
                        },
                        ensure_ascii=False,
                    )
                    + "\n"
                )
            elif res.uses_sorry:
                sorry += 1
            else:
                kept += 1
                out.write(
                    json.dumps(
                        {
                            "seed_id": pr.payload,
                            "code": code,
                            "sha256": hashlib.sha256(code.encode()).hexdigest(),
                            "verify_ms": res.latency_ms,
                        },
                        ensure_ascii=False,
                    )
                    + "\n"
                )
            if i % 100 == 0:
                rate = i / (time.perf_counter() - t0)
                print(f"  {i}/{len(items)} kept={kept} fail={failed} tmo={timeouts} ({rate:.1f}/s)",
                      flush=True)
    wall = time.perf_counter() - t0

    metrics = {
        "candidates": len(items),
        "kept": kept,
        "failed": failed,
        "timeouts": timeouts,
        "sorry": sorry,
        "verifier_crashes": crashes,
        "keep_rate": round(kept / len(items), 4),
        "wall_time_s": round(wall, 1),
        "throughput_per_s": round(len(items) / wall, 2),
        "service_p50_ms": percentile(service, 0.5),
        "service_p95_ms": percentile(service, 0.95),
        "queue_wait_p95_ms": percentile(waits, 0.95),
        "worker_startup_ms": pool.startup_ms,
    }
    path = write_run_record(
        "build-seeds",
        parameters={"source": str(SOURCE), "source_sha256": SOURCE_SHA256, "n": args.n,
                    "workers": args.workers, "heartbeats": HEARTBEATS, "out": args.out},
        metrics=metrics,
        data_version="goedel-lean-workbook-proofs@main",
        seed=args.seed,
        timeout=args.timeout,
    )
    print(f"[OK] kept {kept}/{len(items)} seeds -> {out_path}")
    print(f"     {json.dumps(metrics)}")
    print(f"     run record: {path}")


if __name__ == "__main__":
    main()
