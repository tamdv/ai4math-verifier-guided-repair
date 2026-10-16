"""Validates cost option C: every verified seed must still compile after strip_comments.

Usage:
    python3 scripts/check_strip_comments.py --workers 4 [--limit 500]
"""

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.lean_repl import LeanREPLVerifier  # noqa: E402
from src.llm_repair import strip_comments  # noqa: E402
from src.provenance import write_run_record  # noqa: E402
from src.verifier_pool import VerifierPool  # noqa: E402


def main() -> None:
    parser = argparse.ArgumentParser(description="Check stripped seeds still compile")
    parser.add_argument("--seeds", default="data/seeds/seeds_verified.jsonl")
    parser.add_argument("--workers", type=int, default=2)
    parser.add_argument("--limit", type=int, default=0)
    parser.add_argument("--timeout", type=float, default=60.0)
    args = parser.parse_args()

    with open(args.seeds, encoding="utf-8") as f:
        seeds = [json.loads(line) for line in f if line.strip()]
    if args.limit:
        seeds = seeds[: args.limit]

    pool = VerifierPool(lambda: LeanREPLVerifier(timeout_s=args.timeout), args.workers)
    broken = []
    saved_chars = 0
    for pr in pool.imap((strip_comments(s["code"]), s) for s in seeds):
        saved_chars += len(pr.payload["code"]) - len(strip_comments(pr.payload["code"]))
        if not pr.result.proved:
            broken.append({"seed_id": pr.payload["seed_id"], "status": pr.result.status,
                           "errors": pr.result.errors[:1]})

    total_chars = sum(len(s["code"]) for s in seeds)
    metrics = {
        "seeds": len(seeds),
        "still_compile": len(seeds) - len(broken),
        "broken": len(broken),
        "broken_examples": broken[:10],
        "chars_saved_fraction": round(saved_chars / total_chars, 4) if total_chars else 0.0,
    }
    path = write_run_record("check-strip-comments", vars(args), metrics,
                            data_version=Path(args.seeds).name, seed=0, timeout=args.timeout,
                            status="SUCCESS" if not broken else "FAILED")
    print(json.dumps({k: v for k, v in metrics.items() if k != "broken_examples"}))
    print(f"[{'OK' if not broken else 'FAIL'}] run record: {path}")


if __name__ == "__main__":
    main()
