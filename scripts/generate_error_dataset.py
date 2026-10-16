"""Generates the labeled Lean error dataset (synthetic mutations + natural drift errors).

Pipeline:
1. For every verified seed proof, apply up to `--max-per-seed` applicable mutation
   operators (src/mutations.py), chosen with a per-seed deterministic RNG.
2. Verify each mutant with the REPL pool; keep it only if Lean really reports an
   error (or, for `sem_sorry`, the `sorry` warning). Labels come from the real
   diagnostics via LeanErrorParser, not from the operator.
3. Add natural errors (seed proofs broken by Lean/Mathlib drift).
4. Deduplicate by SHA-256, assign train/holdout by seed (70/30, no seed leaks
   across splits), and write nested tiers (1K subset of 10K subset of all).

Usage:
    python3 scripts/generate_error_dataset.py --workers 2 --max-per-seed 5
"""

import argparse
import collections
import hashlib
import json
import random
import sys
import time
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.error_parser import LeanErrorParser  # noqa: E402
from src.lean_repl import LeanREPLVerifier  # noqa: E402
from src.mutations import MUTATIONS, theorem_statement  # noqa: E402
from src.provenance import percentile, write_run_record  # noqa: E402
from src.verifier_pool import VerifierPool  # noqa: E402

DATA_VERSION = "v1.0-mutation+natural"
HOLDOUT_FRACTION = 0.3


def split_for(seed_id: str) -> str:
    """Deterministic 70/30 split keyed on the seed theorem (prevents leakage)."""
    bucket = int(hashlib.sha256(seed_id.encode()).hexdigest(), 16) % 1000
    return "holdout" if bucket < HOLDOUT_FRACTION * 1000 else "train"


def sha(code: str) -> str:
    return hashlib.sha256(code.encode()).hexdigest()


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    with open(path, encoding="utf-8") as f:
        return [json.loads(line) for line in f if line.strip()]


def build_candidates(
    seeds: list[dict[str, Any]], max_per_seed: int, seed: int
) -> list[dict[str, Any]]:
    """Applies mutation operators to seeds; returns unverified candidate records."""
    out = []
    for s in sorted(seeds, key=lambda r: r["seed_id"]):
        rng = random.Random(f"{seed}:{s['seed_id']}")
        ops = list(MUTATIONS)
        rng.shuffle(ops)
        made = 0
        for op in ops:
            if made >= max_per_seed:
                break
            mutated = op.fn(s["code"], rng)
            if mutated is None or mutated == s["code"]:
                continue
            out.append(
                {
                    "source": "synthetic",
                    "seed_id": s["seed_id"],
                    "mutation_op": op.name,
                    "intended_category": op.category,
                    "code": mutated,
                    "original_code": s["code"],
                }
            )
            made += 1
    return out


def finalize(rec: dict[str, Any], diagnostics: list[dict[str, Any]]) -> dict[str, Any]:
    """Adds real-diagnostic labels, statement hash, split and checksum."""
    primary = LeanErrorParser.primary(diagnostics, rec["code"])
    original = rec.get("original_code")
    stmt = theorem_statement(original) if original else theorem_statement(rec["code"])
    rec.update(
        {
            "diagnostics": diagnostics,
            "primary_message": primary.message if primary else None,
            "category": primary.category.value if primary else None,
            "route": primary.route.value if primary else None,
            "statement": stmt,
            "split": split_for(rec["seed_id"]),
            "sha256": sha(rec["code"]),
        }
    )
    return rec


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate labeled Lean error dataset")
    parser.add_argument("--seeds", default="data/seeds/seeds_verified.jsonl")
    parser.add_argument("--natural", default="data/seeds/natural_errors.jsonl")
    parser.add_argument("--out-dir", default="data/errors")
    parser.add_argument("--sample-out", default="data_sample/errors_sample_100.jsonl")
    parser.add_argument("--max-per-seed", type=int, default=5)
    parser.add_argument("--workers", type=int, default=2)
    parser.add_argument("--timeout", type=float, default=60.0)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--limit-seeds", type=int, default=0, help="Debug: use first N seeds")
    args = parser.parse_args()

    seeds = read_jsonl(Path(args.seeds))
    if args.limit_seeds:
        seeds = seeds[: args.limit_seeds]
    candidates = build_candidates(seeds, args.max_per_seed, args.seed)
    print(f"[..] {len(seeds)} seeds -> {len(candidates)} mutation candidates", flush=True)

    pool = VerifierPool(lambda: LeanREPLVerifier(timeout_s=args.timeout), args.workers)
    kept: list[dict[str, Any]] = []
    rejected = collections.Counter()
    service: list[float] = []
    t0 = time.perf_counter()
    for i, pr in enumerate(pool.imap((c["code"], c) for c in candidates), 1):
        rec, res = pr.payload, pr.result
        service.append(pr.service_ms)
        is_sorry_op = rec["mutation_op"] == "sem_sorry"
        if res.status == "TIMEOUT":
            rec_diags = [{"severity": "error", "line": 0, "column": 0,
                          "message": "(deterministic) timeout: wall-clock limit exceeded"}]
            kept.append(finalize(rec, rec_diags))
        elif res.errors or (is_sorry_op and res.uses_sorry):
            kept.append(finalize(rec, res.diagnostics))
        else:
            rejected[rec["mutation_op"]] += 1  # mutation did not break the proof
        if i % 500 == 0:
            rate = i / (time.perf_counter() - t0)
            print(f"  {i}/{len(candidates)} kept={len(kept)} ({rate:.1f}/s)", flush=True)
    wall = time.perf_counter() - t0

    for nat in read_jsonl(Path(args.natural)):
        rec = {
            "source": "natural",
            "seed_id": nat["seed_id"],
            "mutation_op": None,
            "intended_category": None,
            "code": nat["code"],
            "original_code": None,
        }
        kept.append(finalize(rec, nat["diagnostics"]))

    # Deduplicate, then order deterministically before assigning ids and tiers.
    unique: dict[str, dict[str, Any]] = {}
    for rec in sorted(kept, key=lambda r: (r["seed_id"], r["mutation_op"] or "", r["sha256"])):
        unique.setdefault(rec["sha256"], rec)
    records = list(unique.values())
    random.Random(args.seed).shuffle(records)
    for i, rec in enumerate(records):
        rec["error_id"] = f"E{i:06d}"

    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    tiers = {"all": records, "10k": records[:10000], "1k": records[:1000]}
    checksums = {}
    for name, rows in tiers.items():
        path = out_dir / f"errors_{name}.jsonl"
        with open(path, "w", encoding="utf-8") as f:
            for r in rows:
                f.write(json.dumps(r, ensure_ascii=False) + "\n")
        checksums[path.name] = {"rows": len(rows), "sha256": hashlib.sha256(path.read_bytes()).hexdigest()}

    sample_path = Path(args.sample_out)
    with open(sample_path, "w", encoding="utf-8") as f:
        for r in records[:100]:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")

    confusion = collections.Counter(
        f"{r['intended_category']}->{r['category']}" for r in records if r["source"] == "synthetic"
    )
    metrics = {
        "seeds": len(seeds),
        "candidates": len(candidates),
        "kept_synthetic": sum(r["source"] == "synthetic" for r in records),
        "kept_natural": sum(r["source"] == "natural" for r in records),
        "total_unique": len(records),
        "duplicates_removed": len(kept) - len(records),
        "rejected_not_broken": dict(rejected),
        "category_counts": dict(collections.Counter(r["category"] for r in records)),
        "split_counts": dict(collections.Counter(r["split"] for r in records)),
        "intended_vs_lean": dict(sorted(confusion.items())),
        "verify_wall_s": round(wall, 1),
        "verify_throughput_per_s": round(len(candidates) / wall, 2) if wall else 0.0,
        "service_p50_ms": percentile(service, 0.5),
        "service_p95_ms": percentile(service, 0.95),
        "worker_startup_ms": pool.startup_ms,
        "files": checksums,
    }
    path = write_run_record(
        "gen-errors",
        parameters=vars(args),
        metrics=metrics,
        data_version=DATA_VERSION,
        seed=args.seed,
        timeout=args.timeout,
    )
    print(f"[OK] {len(records)} unique error samples -> {out_dir}")
    print(json.dumps({k: metrics[k] for k in ("category_counts", "split_counts",
                                               "rejected_not_broken")}, ensure_ascii=False))
    print(f"     run record: {path}")


if __name__ == "__main__":
    main()
