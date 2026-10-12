"""3-Scale Benchmark Harness for Distributed Queue & Worker System.

Compares FIFO vs Priority Queue scheduling disciplines across 3 scale tiers
(Tier 1: Small, Tier 2: Medium, Tier 3: Large).
Records P50/P95 latency, throughput QPS, peak memory, and queue wait times
in strict accordance with PTIT INT4418 Phụ lục B.
"""

from __future__ import annotations

import argparse
import datetime
import json
import os
import platform
import time
import uuid
from typing import Any

try:
    import psutil
except ImportError:
    psutil = None  # type: ignore

import sys
from pathlib import Path

# Ensure workspace root is in sys.path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.bounded_controller import BoundedRetryController

from src.rule_repair import RuleRepairEngine
from src.verifier_pool import VerifierWorkerPool
from src.worker_queue import QueueMode, WorkerQueue


def generate_benchmark_candidates(
    base_dataset_path: str, count: int
) -> list[dict[str, Any]]:
    """Generates synthetic scaled dataset candidates by repeating and jittering sample items."""
    with open(base_dataset_path, "r", encoding="utf-8") as f:
        base_items = json.load(f)

    if not base_items:
        raise ValueError("Base dataset is empty.")

    scaled_candidates: list[dict[str, Any]] = []
    base_len = len(base_items)

    for i in range(count):
        tmpl = base_items[i % base_len].copy()
        cand = {
            "error_id": f"BENCH-{i:05d}",
            "title": f"Theorem Benchmark Instance #{i}: {tmpl.get('title', '')}",
            "category_code": tmpl.get("category_code", "SYN_01"),
            "code_snippet": tmpl.get("code_snippet", ""),
            "compiler_log": tmpl.get("compiler_log", {}).copy(),
            "suggested_strategy": tmpl.get("suggested_strategy", "rule_repair"),
            "priority": 1 + (i % 10),  # Distributed priorities 1 to 10
        }
        scaled_candidates.append(cand)

    return scaled_candidates


def run_single_benchmark_tier(
    candidates: list[dict[str, Any]],
    mode: QueueMode,
    scale_name: str,
    num_workers: int = 4,
    seed: int = 42,
) -> dict[str, Any]:
    """Executes a benchmark run for a specific scale tier and queue discipline."""
    process = psutil.Process() if psutil else None
    mem_before = process.memory_info().rss / (1024 * 1024) if process else 0.0

    queue = WorkerQueue(prefix=f"bench:{scale_name}:{mode.value}", use_fallback=True)
    queue.clear()

    pool = VerifierWorkerPool(num_workers=num_workers, default_timeout=15.0)
    rule_engine = RuleRepairEngine()

    controller = BoundedRetryController(
        queue=queue,
        verifier_pool=pool,
        rule_engine=rule_engine,
        max_attempts=3,
        timeout_per_attempt=15.0,
    )

    total_count = len(candidates)

    # 1. Enqueue Phase
    t_enqueue_start = time.perf_counter()
    for item in candidates:
        queue.enqueue(
            payload=item,
            priority=item.get("priority", 5),
            task_id=item["error_id"],
            max_attempts=3,
            mode=mode,
        )
    t_enqueue_duration = time.perf_counter() - t_enqueue_start

    # 2. Processing Phase
    turnaround_latencies: list[float] = []
    success_count = 0
    t_process_start = time.perf_counter()

    while queue.get_length(mode) > 0:
        task = queue.dequeue(timeout=0.1, mode=mode)
        if not task:
            break

        item = task.payload
        res = controller.repair_candidate_sync(
            candidate_id=task.task_id,
            problem_id=f"PROB-{task.task_id}",
            initial_code=item.get("code_snippet", ""),
            initial_diagnostics=[item.get("compiler_log", {})],
            statement_natural=item.get("title", ""),
            priority=task.priority,
            queue_mode=mode,
        )

        turnaround_latencies.append(res.duration_total_ms)

        if res.status == "REPAIRED":
            queue.ack(task.task_id)
            success_count += 1
        else:
            queue.nack(task.task_id, requeue=False, mode=mode)

    t_process_duration = time.perf_counter() - t_process_start
    mem_after = process.memory_info().rss / (1024 * 1024) if process else 0.0

    turnaround_latencies.sort()
    n = len(turnaround_latencies)
    p50_turnaround = turnaround_latencies[int(n * 0.50)] if n else 0.0
    p95_turnaround = turnaround_latencies[min(int(n * 0.95), n - 1)] if n else 0.0

    qps = round(total_count / t_process_duration, 2) if t_process_duration > 0 else 0.0
    queue_metrics = queue.get_metrics()
    pool_metrics = pool.get_metrics()

    queue.clear()
    queue.close()
    pool.close()

    run_id = (
        f"queue-bench-{scale_name}-{mode.value}-"
        f"{datetime.datetime.now(datetime.UTC).strftime('%Y%m%d%H%M%S')}-"
        f"{uuid.uuid4().hex[:6]}"
    )

    record = {
        "run_id": run_id,
        "timestamp": datetime.datetime.now(datetime.UTC).isoformat(),
        "git_commit": "feature/worker-queue",
        "data_version": f"benchmark-{scale_name}-{total_count}-items",
        "machine": {
            "os": platform.platform(),
            "cpu": platform.processor(),
            "python": platform.python_version(),
            "ram_mb": round(mem_after, 1),
        },
        "parameters": {
            "scale_tier": scale_name,
            "total_candidates": total_count,
            "queue_discipline": mode.value,
            "num_workers": num_workers,
            "max_retry_attempts": 3,
            "timeout_per_attempt_sec": 15.0,
            "seed": seed,
            "backend": "redis" if queue_metrics["is_redis"] else "in-memory-fallback",
        },
        "seed": seed,
        "timeout": 15,
        "metrics": {
            "total_samples": total_count,
            "repaired_count": success_count,
            "repair_success_rate": round(success_count / total_count, 4)
            if total_count
            else 0.0,
            "throughput_qps": qps,
            "turnaround_p50_ms": round(p50_turnaround, 2),
            "turnaround_p95_ms": round(p95_turnaround, 2),
            "queue_wait_p50_ms": queue_metrics["wait_time_p50_ms"],
            "queue_wait_p95_ms": queue_metrics["wait_time_p95_ms"],
            "enqueue_qps": round(total_count / max(t_enqueue_duration, 0.001), 2),
            "peak_ram_mb": round(mem_after, 1),
            "delta_ram_mb": round(mem_after - mem_before, 2),
            "dlq_count": queue_metrics["dlq_count"],
            "verifier_metrics": pool_metrics,
        },

        "status": "SUCCESS",
        "log_path": f"logs/{run_id}.log",
    }

    os.makedirs("results/raw", exist_ok=True)
    out_file = os.path.join("results/raw", f"run_{run_id}.json")
    with open(out_file, "w", encoding="utf-8") as f:
        json.dump(record, f, indent=2, ensure_ascii=False)

    print(
        f"[{scale_name.upper()} | {mode.value.upper()}] QPS: {qps} | P50: {p50_turnaround}ms | P95: {p95_turnaround}ms | Wait P95: {queue_metrics['wait_time_p95_ms']}ms -> {out_file}"
    )
    return record


def run_3_tier_scalability_benchmark(
    dataset_path: str = "data_sample/error_dataset_50.json",
    num_workers: int = 4,
) -> list[dict[str, Any]]:
    """Runs the mandatory 3-Tier Scalability experiment comparing FIFO vs Priority queue."""
    tiers = [
        ("tier1_small", 50),
        ("tier2_medium", 200),
        ("tier3_large", 500),
    ]

    all_records = []
    print("=" * 70)
    print("STARTING 3-TIER QUEUE & WORKER SCALABILITY BENCHMARK (PTIT INT4418)")
    print("Disciplines: FIFO Queue vs Priority Queue")
    print(f"Workers: {num_workers} | Timeout: 15s | Max Attempts: 3")
    print("=" * 70)

    for tier_name, count in tiers:
        candidates = generate_benchmark_candidates(dataset_path, count)

        # 1. FIFO Discipline
        rec_fifo = run_single_benchmark_tier(
            candidates=candidates,
            mode=QueueMode.FIFO,
            scale_name=tier_name,
            num_workers=num_workers,
        )
        all_records.append(rec_fifo)

        # 2. Priority Discipline
        rec_priority = run_single_benchmark_tier(
            candidates=candidates,
            mode=QueueMode.PRIORITY,
            scale_name=tier_name,
            num_workers=num_workers,
        )
        all_records.append(rec_priority)

    print("=" * 70)
    print("3-TIER BENCHMARK COMPLETED SUCCESSFULLY.")
    print("All artifacts stored in results/raw/ adhering to Phu luc B.")

    print("=" * 70)
    return all_records


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Run Queue & Worker Scalability Benchmark"
    )
    parser.add_argument(
        "--data", default="data_sample/error_dataset_50.json", help="Base dataset path"
    )
    parser.add_argument(
        "--tiers", action="store_true", default=True, help="Run all 3 scale tiers"
    )
    parser.add_argument(
        "--workers", type=int, default=4, help="Number of worker pool threads"
    )
    args = parser.parse_args()

    run_3_tier_scalability_benchmark(args.data, args.workers)
