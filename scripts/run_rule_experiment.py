"""Benchmark and Rule Coverage Experiment Runner for Rule-based Repair."""

import argparse
import datetime
import json
import os
import platform
import subprocess
import sys
import time
import uuid
from pathlib import Path

# Add project root to sys.path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.lean_verifier import LeanVerifier
from src.rule_repair import RuleRepairEngine


def _git_commit() -> str:
    try:
        return subprocess.run(
            ["git", "rev-parse", "HEAD"], capture_output=True, text=True, check=True
        ).stdout.strip()
    except (OSError, subprocess.CalledProcessError):
        return "unknown"


def _percentile(values: list[float], q: float) -> float:
    if not values:
        return 0.0
    ordered = sorted(values)
    return float(ordered[min(int(len(ordered) * q), len(ordered) - 1)])


def _lean_version() -> str:
    from src.lean_verifier import _find_executable

    lean = _find_executable("lean")
    if not lean:
        return "missing"
    out = subprocess.run([lean, "--version"], capture_output=True, text=True, check=False)
    return out.stdout.strip()


def run_rule_benchmark(
    dataset_path: str,
    seed: int = 42,
    verifier: LeanVerifier | None = None,
) -> dict:
    """Executes the Rule-based Repair Benchmark on the candidate dataset.

    If `verifier` is given, both the original snippet and the rule output are
    compiled with Lean 4, so `rule_hit_rate` (a rule fired) is reported alongside
    `compile_rate` (Lean accepted the repaired code).
    """
    engine = RuleRepairEngine()

    with open(dataset_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    total_samples = len(data)
    latencies = []
    rule_repaired_count = 0
    tokens_saved = 0
    category_breakdown = {}
    verify_latencies = []
    per_sample = []
    original_compiled = 0
    repaired_compiled = 0
    repaired_proved = 0
    compiled_by_category: dict[str, int] = {}

    for item in data:
        cat = item.get("category_code", "UNKNOWN")
        msg = item.get("compiler_log", {}).get("message", "")
        code = item.get("code_snippet", "")
        line = item.get("compiler_log", {}).get("line", 1)
        col = item.get("compiler_log", {}).get("column", 1)

        t0 = time.perf_counter()
        res = engine.repair_candidate(code, cat, msg, line, col)
        elapsed_ms = (time.perf_counter() - t0) * 1000.0

        latencies.append(elapsed_ms)
        if res:
            rule_repaired_count += 1
            category_breakdown[cat] = category_breakdown.get(cat, 0) + 1
            tokens_saved += 550  # Average tokens per sample saved

        if verifier is not None:
            before = verifier.verify(code)
            after = verifier.verify(res.repaired_code) if res else None
            verify_latencies.append(before.latency_ms)
            original_compiled += before.compiled
            if after is not None:
                verify_latencies.append(after.latency_ms)
                repaired_compiled += after.compiled
                repaired_proved += after.proved
                if after.compiled:
                    compiled_by_category[cat] = compiled_by_category.get(cat, 0) + 1
            per_sample.append(
                {
                    "error_id": item.get("error_id"),
                    "category_code": cat,
                    "rule_applied": res.rule_applied if res else None,
                    "original": before.to_dict(),
                    "repaired_code": res.repaired_code if res else None,
                    "repaired": after.to_dict() if after else None,
                }
            )

    p50_latency = _percentile(latencies, 0.50)
    p95_latency = _percentile(latencies, 0.95)
    hit_rate = round(rule_repaired_count / total_samples, 4) if total_samples > 0 else 0.0
    total_time_s = sum(latencies) / 1000.0
    throughput_qps = round(total_samples / total_time_s, 2) if total_time_s > 0 else 0.0

    run_id = f"rule-repair-eval-{datetime.datetime.now(datetime.timezone.utc).strftime('%Y%m%d%H%M%S')}-{uuid.uuid4().hex[:6]}"

    record = {
        "run_id": run_id,
        "timestamp": datetime.datetime.now(datetime.timezone.utc).isoformat(),
        "git_commit": _git_commit(),
        "data_version": "v0.1-50-errors",
        "machine": {
            "os": platform.platform(),
            "cpu": platform.processor(),
            "python": platform.python_version()
        },
        "parameters": {
            "dataset_path": dataset_path,
            "total_candidates": total_samples,
            "engine": "RuleRepairEngine",
            "token_cost_per_repair": 0,
            "seed": seed,
            "lean_verify": verifier is not None,
            "lean_project_dir": verifier.project_dir if verifier else None,
        },
        "seed": seed,
        "timeout": verifier.timeout_s if verifier else 5,
        "metrics": {
            "total_samples": total_samples,
            "rule_repaired_count": rule_repaired_count,
            "rule_hit_rate": hit_rate,
            "category_breakdown": category_breakdown,
            "latency_p50_ms": round(p50_latency, 3),
            "latency_p95_ms": round(p95_latency, 3),
            "throughput_qps": throughput_qps,
            "total_tokens_saved": tokens_saved,
            "avg_tokens_saved_per_sample": round(tokens_saved / total_samples, 1)
        },
        "status": "SUCCESS",
        "log_path": f"logs/{run_id}.log"
    }

    if verifier is not None:
        record["software"] = {"lean": _lean_version()}
        record["metrics"].update(
            {
                "original_compiled_count": original_compiled,
                "repaired_compiled_count": repaired_compiled,
                "repaired_proved_count": repaired_proved,
                "compile_rate": round(repaired_compiled / total_samples, 4),
                "compile_rate_given_rule": (
                    round(repaired_compiled / rule_repaired_count, 4)
                    if rule_repaired_count
                    else 0.0
                ),
                "compiled_by_category": compiled_by_category,
                "verify_latency_p50_ms": round(_percentile(verify_latencies, 0.50), 3),
                "verify_latency_p95_ms": round(_percentile(verify_latencies, 0.95), 3),
            }
        )
        record["samples"] = per_sample

    os.makedirs("results/raw", exist_ok=True)
    out_file = os.path.join("results/raw", f"run_{run_id}.json")
    with open(out_file, "w", encoding="utf-8") as f:
        json.dump(record, f, indent=2)

    print(f"[OK] Rule Repair Benchmark Completed:")
    print(f"     Total samples: {total_samples}")
    print(f"     Rule Repaired: {rule_repaired_count} ({hit_rate * 100:.1f}%)")
    print(f"     Category breakdown: {category_breakdown}")
    print(f"     Latency P50: {p50_latency:.3f}ms | Latency P95: {p95_latency:.3f}ms")
    print(f"     Throughput: {throughput_qps:.1f} qps")
    print(f"     Total Tokens Saved: ~{tokens_saved:,} tokens (0 token API cost)")
    if verifier is not None:
        m = record["metrics"]
        print(f"     Lean: original compiled {m['original_compiled_count']}/{total_samples}")
        print(
            f"     Lean: repaired compiled {m['repaired_compiled_count']}/{total_samples} "
            f"(compile_rate={m['compile_rate']:.2%}, proved={m['repaired_proved_count']})"
        )
        print(
            f"     Verify latency P50: {m['verify_latency_p50_ms']:.0f}ms | "
            f"P95: {m['verify_latency_p95_ms']:.0f}ms"
        )
    print(f"     Result saved to: {out_file}")
    return record


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Run Rule Repair Benchmark")
    parser.add_argument("--data", default="data_sample/error_dataset_50.json", help="Path to error dataset")
    parser.add_argument("--seed", type=int, default=42, help="Random seed")
    parser.add_argument("--verify", action="store_true", help="Compile outputs with Lean 4")
    parser.add_argument("--lean-project", default=None, help="Lake project dir (for Mathlib)")
    parser.add_argument("--timeout", type=float, default=15.0, help="Lean timeout per file (s)")
    args = parser.parse_args()
    lean = None
    if args.verify:
        lean = LeanVerifier(project_dir=args.lean_project, timeout_s=args.timeout)
        if not lean.available:
            sys.exit("Lean toolchain not found (run scripts/install_lean4.sh)")
    run_rule_benchmark(args.data, args.seed, lean)
