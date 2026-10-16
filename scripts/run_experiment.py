"""Runs one repair experiment configuration and writes an immutable run record.

Example:
    python3 scripts/run_experiment.py --data data/errors/errors_1k.jsonl --split holdout \
        --strategy hybrid --budget 3 --workers 2 --provider gemini --model gemini-3.5-flash-lite

Outputs:
    results/raw/run_<run_id>.json          metrics + provenance (Rule 3)
    results/raw/logs/<run_id>.jsonl.gz     per-sample replayable attempt log
"""

import argparse
import collections
import gzip
import json
import sys
import threading
import time
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import yaml  # noqa: E402

from src.cost_guard import BudgetExceeded, CostGuard, GuardedClient, ResponseCache  # noqa: E402
from src.lean_repl import LeanREPLVerifier  # noqa: E402
from src.llm_client import make_client  # noqa: E402
from src.llm_repair import LLMRepairEngine  # noqa: E402
from src.provenance import RAW_DIR, new_run_id, percentile, write_run_record  # noqa: E402
from src.repair_pipeline import RepairOutcome, RepairPipeline, RepairPolicy  # noqa: E402
from src.verifier_pool import VerifierPool  # noqa: E402

PRICES_PATH = Path(__file__).resolve().parent.parent / "configs" / "llm_prices.yaml"


class PeakMemory:
    """Samples memory of this process and all descendants (REPL workers) every 0.5 s.

    `peak_mb` sums RSS, which counts the Mathlib .olean files that all workers mmap
    once per worker (over-estimate). `peak_uss_mb` sums USS (pages unique to each
    process) plus the largest shared remainder once: the realistic footprint.
    """

    def __init__(self) -> None:
        self.peak_mb = 0.0
        self.peak_uss_mb = 0.0
        self._stop = threading.Event()
        self._thread = threading.Thread(target=self._loop, daemon=True)

    def _loop(self) -> None:
        import psutil

        me = psutil.Process()
        while not self._stop.is_set():
            total = uss = shared_max = 0
            for p in [me, *me.children(recursive=True)]:
                try:
                    rss = p.memory_info().rss
                    total += rss
                    try:
                        u = p.memory_full_info().uss
                    except (psutil.Error, AttributeError):
                        u = rss
                    uss += u
                    shared_max = max(shared_max, rss - u)
                except psutil.Error:
                    pass
            self.peak_mb = max(self.peak_mb, total / 2**20)
            self.peak_uss_mb = max(self.peak_uss_mb, (uss + shared_max) / 2**20)
            self._stop.wait(0.5)

    def __enter__(self) -> "PeakMemory":
        self._thread.start()
        return self

    def __exit__(self, *exc: object) -> None:
        self._stop.set()
        self._thread.join()


def load_samples(path: str, split: str, limit: int) -> list[dict[str, Any]]:
    with open(path, encoding="utf-8") as f:
        rows = [json.loads(line) for line in f if line.strip()]
    if split != "all":
        rows = [r for r in rows if r["split"] == split]
    return rows[:limit] if limit else rows


def token_cost_usd(model: str, inp: int, out: int, thinking: int) -> float | None:
    """USD cost from configs/llm_prices.yaml (None if the model has no price entry)."""
    if not PRICES_PATH.exists():
        return None
    prices = (yaml.safe_load(PRICES_PATH.read_text()) or {}).get(model)
    if not prices or prices.get("input") is None:
        return None
    return round((inp * prices["input"] + (out + thinking) * prices["output"]) / 1e6, 6)


def summarize(outcomes: list[tuple[RepairOutcome, dict[str, Any], float]], wall_s: float,
              model: str | None) -> dict[str, Any]:
    """Quality / cost / performance metrics for one run."""
    n = len(outcomes)
    succ = [o for o, _, _ in outcomes if o.success]
    e2e = [o.wall_ms + wait for o, _, wait in outcomes]
    service = [o.wall_ms for o, _, _ in outcomes]
    waits = [wait for _, _, wait in outcomes]
    inp = sum(a.input_tokens for o, _, _ in outcomes for a in o.attempts)
    out = sum(a.output_tokens for o, _, _ in outcomes for a in o.attempts)
    think = sum(a.thinking_tokens for o, _, _ in outcomes for a in o.attempts)
    by_cat: dict[str, list[int]] = collections.defaultdict(lambda: [0, 0])
    by_src: dict[str, list[int]] = collections.defaultdict(lambda: [0, 0])
    for o, s, _ in outcomes:
        by_cat[s.get("category") or "NONE"][0] += o.success
        by_cat[s.get("category") or "NONE"][1] += 1
        by_src[s.get("source", "?")][0] += o.success
        by_src[s.get("source", "?")][1] += 1
    compiled = sum(o.compiled for o, _, _ in outcomes)
    cost = token_cost_usd(model, inp, out, think) if model else 0.0
    return {
        "n_samples": n,
        "repair_success_rate": round(len(succ) / n, 4) if n else 0.0,
        "compile_rate": round(compiled / n, 4) if n else 0.0,
        "semantic_pass_given_compiled": round(len(succ) / compiled, 4) if compiled else 0.0,
        "attempts_per_sample": round(sum(o.attempts_used for o, _, _ in outcomes) / n, 3) if n else 0,
        "llm_calls": sum(o.llm_calls for o, _, _ in outcomes),
        "tokens_input": inp,
        "tokens_output": out,
        "tokens_thinking": think,
        "tokens_per_success": round((inp + out + think) / len(succ), 1) if succ else None,
        "cost_usd": cost,
        "cost_per_success_usd": round(cost / len(succ), 6) if succ and cost else None,
        # service = time a worker spends on one sample (repair attempts + Lean checks);
        # latency = service + queue wait (end-to-end sojourn in a batch run).
        "service_p50_ms": round(percentile(service, 0.5), 1),
        "service_p95_ms": round(percentile(service, 0.95), 1),
        "latency_p50_ms": round(percentile(e2e, 0.5), 1),
        "latency_p95_ms": round(percentile(e2e, 0.95), 1),
        "queue_wait_p50_ms": round(percentile(waits, 0.5), 1),
        "queue_wait_p95_ms": round(percentile(waits, 0.95), 1),
        "throughput_samples_per_s": round(n / wall_s, 3) if wall_s else 0.0,
        "wall_time_s": round(wall_s, 1),
        "stop_reasons": dict(collections.Counter(o.stop_reason for o, _, _ in outcomes)),
        "success_by_category": {k: {"success": v[0], "n": v[1], "rate": round(v[0] / v[1], 4)}
                                for k, v in sorted(by_cat.items())},
        "success_by_source": {k: {"success": v[0], "n": v[1]} for k, v in by_src.items()},
        "worker_errors": 0,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Run one repair experiment configuration")
    parser.add_argument("--data", default="data/errors/errors_1k.jsonl")
    parser.add_argument("--split", default="holdout", choices=["train", "holdout", "all"])
    parser.add_argument("--limit", type=int, default=0)
    parser.add_argument("--strategy", default="hybrid",
                        choices=["none", "blind", "llm_only", "rule_only", "hybrid"])
    parser.add_argument("--budget", type=int, default=1, help="Max repair attempts per sample")
    parser.add_argument("--wall-budget", type=float, default=300.0, help="Seconds per sample")
    parser.add_argument("--workers", type=int, default=1)
    parser.add_argument("--provider", default="gemini")
    parser.add_argument("--model", default="gemini-3.5-flash-lite")
    parser.add_argument("--prompt-version", default="repair_v1")
    parser.add_argument("--timeout", type=float, default=60.0, help="Lean timeout per check")
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--repeat-index", type=int, default=0, help="Repetition number (1..3)")
    parser.add_argument("--tag", default="", help="Free-form experiment group label")
    parser.add_argument("--run-cap", type=float, default=None,
                        help="USD cap for this run (default: configs/budget.yaml)")
    parser.add_argument("--keep-comments", action="store_true",
                        help="Send comments to the LLM (default strips them: cost option C)")
    parser.add_argument("--no-cache", action="store_true",
                        help="Bypass the LLM response cache (forces paid calls)")
    args = parser.parse_args()

    samples = load_samples(args.data, args.split, args.limit)
    needs_llm = args.strategy in ("blind", "llm_only", "hybrid") and args.budget > 0
    run_id = new_run_id(f"exp-{args.strategy}-b{args.budget}-w{args.workers}")
    guard = CostGuard(run_id, run_cap_usd=args.run_cap) if needs_llm else None
    cache = ResponseCache() if needs_llm and not args.no_cache else None
    if guard:
        print(f"[$$] month spent ${guard.month_spent:.4f} / cap ${guard.monthly_cap:.2f}; "
              f"run cap ${guard.run_cap:.2f}", flush=True)

    def factory() -> RepairPipeline:
        verifier = LeanREPLVerifier(timeout_s=args.timeout)
        blind = diag = None
        if needs_llm:
            assert guard is not None
            client = GuardedClient(make_client(args.provider, args.model), guard, cache)
            blind = LLMRepairEngine(client, "blind", args.prompt_version)
            diag = LLMRepairEngine(client, "diagnostic", args.prompt_version)
        pipe = RepairPipeline(verifier, RepairPolicy(args.strategy, args.budget, args.wall_budget,
                                                         strip_comments=not args.keep_comments),
                              llm_blind=blind, llm_diag=diag)
        return pipe

    pool = VerifierPool(factory, args.workers, task=lambda pipe, s: pipe.run(s))
    log_dir = RAW_DIR / "logs"
    log_dir.mkdir(parents=True, exist_ok=True)
    log_path = log_dir / f"{run_id}.jsonl.gz"

    outcomes: list[tuple[RepairOutcome, dict[str, Any], float]] = []
    errors = 0
    budget_hit = 0
    print(f"[..] {run_id}: {len(samples)} samples, {args.workers} workers", flush=True)
    with PeakMemory() as mem, gzip.open(log_path, "wt", encoding="utf-8") as log:
        t0 = time.perf_counter()
        for i, pr in enumerate(pool.imap((s, s) for s in samples), 1):
            if isinstance(pr.result, BaseException):
                errors += 1
                budget_hit += isinstance(pr.result, BudgetExceeded)
                log.write(json.dumps({"error_id": pr.payload.get("error_id"),
                                      "worker_error": repr(pr.result)}) + "\n")
                continue
            outcomes.append((pr.result, pr.payload, pr.queue_wait_ms))
            entry = pr.result.to_dict()
            entry.update({"queue_wait_ms": pr.queue_wait_ms, "worker_id": pr.worker_id,
                          "category": pr.payload.get("category"),
                          "source": pr.payload.get("source")})
            log.write(json.dumps(entry, ensure_ascii=False) + "\n")
            if i % 100 == 0:
                ok = sum(o.success for o, _, _ in outcomes)
                print(f"  {i}/{len(samples)} success={ok}", flush=True)
        wall = time.perf_counter() - t0

    metrics = summarize(outcomes, wall, args.model if needs_llm else None)
    metrics["worker_errors"] = errors
    metrics["budget_refusals"] = budget_hit
    if guard:
        metrics["real_spend_usd"] = round(guard.run_spent, 6)
        metrics["paid_calls"] = guard.calls
        metrics["month_spend_usd"] = round(guard.month_spent, 6)
    if cache:
        metrics["cache_hits"], metrics["cache_misses"] = cache.hits, cache.misses
    metrics["peak_rss_mb"] = round(mem.peak_mb, 1)
    metrics["peak_uss_mb"] = round(mem.peak_uss_mb, 1)
    metrics["worker_startup_ms"] = pool.startup_ms
    # Steady-state throughput: exclude the one-off Mathlib import of the workers.
    startup_s = max(pool.startup_ms, default=0.0) / 1000
    steady = wall - startup_s
    metrics["throughput_excl_startup_per_s"] = (
        round(len(outcomes) / steady, 3) if steady > 0 else None)
    status = "SUCCESS" if errors == 0 else ("BUDGET_EXCEEDED" if budget_hit else "PARTIAL")
    path = write_run_record(
        f"exp-{args.strategy}-b{args.budget}-w{args.workers}",
        parameters=vars(args) | {"log_path": str(log_path.relative_to(RAW_DIR.parent.parent))},
        metrics=metrics,
        data_version=Path(args.data).name,
        seed=args.seed,
        timeout=args.timeout,
        status=status,
        run_id=run_id,
    )
    print(json.dumps({k: metrics[k] for k in (
        "n_samples", "repair_success_rate", "compile_rate", "attempts_per_sample",
        "service_p50_ms", "service_p95_ms", "latency_p95_ms", "throughput_samples_per_s", "cost_usd",
        "peak_rss_mb")}, ensure_ascii=False))
    if guard:
        print(f"[$$] real spend this run ${guard.run_spent:.4f} ({guard.calls} paid calls); "
              f"month ${guard.month_spent:.4f} / ${guard.monthly_cap:.2f}")
    print(f"[OK] run record: {path}")


if __name__ == "__main__":
    main()
