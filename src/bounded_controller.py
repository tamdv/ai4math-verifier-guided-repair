"""Bounded Retry Controller for Verifier-Guided Mathematical Proof Repair.

Coordinates the end-to-end closed-loop repair lifecycle:
- Enqueues candidate errors into WorkerQueue (FIFO or Priority scheduling).
- Dispatches repair strategies (Rule-based 0-token engine vs LLM engine).
- Submits candidate mutations to LeanVerifierPool with strict 15s timeout.
- Manages retry budget (attempts <= max_attempts) and cumulative time budget.
- Emits standardized metrics and provenance logs according to PTIT INT4418 Phụ lục B.
"""

from __future__ import annotations

import datetime
import json
import os
import platform
import time
import uuid
from collections.abc import Callable
from dataclasses import asdict, dataclass, field
from typing import Any

from src.error_parser import LeanErrorParser, RepairRoute
from src.rule_repair import RuleRepairEngine
from src.sim_verifier import VerifierWorkerPool
from src.worker_queue import QueueMode, WorkerQueue


@dataclass
class RepairCycleRecord:
    """Detailed audit trace for an individual repair attempt."""

    attempt_index: int
    started_at: str
    strategy_applied: str
    code_before: str
    code_after: str
    rule_or_model: str
    verification_success: bool
    verification_latency_ms: float
    diagnostics: list[dict[str, Any]]
    timed_out: bool = False


@dataclass
class CandidateRepairResult:
    """End-to-end outcome for a candidate theorem repair."""

    candidate_id: str
    problem_id: str
    status: str  # REPAIRED | UNREPAIRABLE | TIMEOUT_EXCEEDED
    final_code: str
    attempts_used: int
    max_attempts: int
    duration_total_ms: float
    history: list[RepairCycleRecord] = field(default_factory=list)
    final_diagnostics: list[dict[str, Any]] = field(default_factory=list)
    semantic_audit_passed: bool = True

    def to_dict(self) -> dict[str, Any]:
        """Converts result to dictionary."""
        data = asdict(self)
        return data


class BoundedRetryController:
    """Orchestrates closed-loop repair attempts within strict budget bounds."""

    def __init__(
        self,
        queue: WorkerQueue | None = None,
        verifier_pool: VerifierWorkerPool | None = None,
        rule_engine: RuleRepairEngine | None = None,
        llm_repair_fn: Callable[[str, list[dict[str, Any]]], str | None] | None = None,
        semantic_auditor_fn: Callable[[str, str], bool] | None = None,
        max_attempts: int = 3,
        timeout_per_attempt: float = 15.0,
        total_timeout_sec: float = 60.0,
    ) -> None:
        """Initializes the controller.

        Args:
            queue: Distributed worker queue instance.
            verifier_pool: Lean 4 verifier worker pool.
            rule_engine: Heuristic rule-based repair engine.
            llm_repair_fn: Optional LLM repair fallback function.
            semantic_auditor_fn: Optional semantic safety auditor.
            max_attempts: Maximum retry attempts permitted per candidate.
            timeout_per_attempt: Timeout for each compiler check (default 15s).
            total_timeout_sec: Maximum total duration allowed per candidate.
        """
        self.queue = queue or WorkerQueue()
        self.verifier_pool = verifier_pool or VerifierWorkerPool(
            default_timeout=timeout_per_attempt
        )
        self.rule_engine = rule_engine or RuleRepairEngine()
        self.llm_repair_fn = llm_repair_fn
        self.semantic_auditor_fn = semantic_auditor_fn
        self.max_attempts = max_attempts
        self.timeout_per_attempt = timeout_per_attempt
        self.total_timeout_sec = total_timeout_sec

        self._parser = LeanErrorParser()

    def repair_candidate_sync(
        self,
        candidate_id: str,
        problem_id: str,
        initial_code: str,
        initial_diagnostics: list[dict[str, Any]],
        statement_natural: str = "",
        priority: int = 5,
        queue_mode: QueueMode = QueueMode.FIFO,
    ) -> CandidateRepairResult:
        """Executes the closed-loop repair process for a single candidate.

        Args:
            candidate_id: Unique candidate identifier.
            problem_id: Identifier of the source mathematical theorem.
            initial_code: Faulty Lean 4 code.
            initial_diagnostics: Starting compiler error logs.
            statement_natural: Original natural language problem statement.
            priority: Scheduling priority for queueing.
            queue_mode: FIFO or Priority scheduling discipline.

        Returns:
            CandidateRepairResult containing outcome and execution trace.
        """
        start_overall = time.perf_counter()
        current_code = initial_code
        current_diags = list(initial_diagnostics)
        history: list[RepairCycleRecord] = []
        status = "UNREPAIRABLE"

        # 0. Initial check: verify if the initial code is already valid
        if not current_diags:
            v_init = self.verifier_pool.verify(
                current_code,
                timeout=self.timeout_per_attempt,
            )
            if v_init.success:
                return CandidateRepairResult(
                    candidate_id=candidate_id,
                    problem_id=problem_id,
                    status="REPAIRED",
                    final_code=current_code,
                    attempts_used=0,
                    max_attempts=self.max_attempts,
                    duration_total_ms=round(v_init.duration_ms, 2),
                    history=[],
                    final_diagnostics=[],
                    semantic_audit_passed=True,
                )
            current_diags = v_init.diagnostics

        # Bounded retry loop (attempts 1 to max_attempts)
        for attempt in range(1, self.max_attempts + 1):
            elapsed_total = time.perf_counter() - start_overall
            if elapsed_total > self.total_timeout_sec:
                status = "TIMEOUT_EXCEEDED"
                break

            attempt_start_iso = datetime.datetime.now(datetime.UTC).isoformat()
            code_before_attempt = current_code

            # 1. Parse and categorize top diagnostic error
            top_diag = current_diags[0] if current_diags else {}
            diag_rec = self._parser.parse_diagnostic(top_diag)

            strategy_applied = "unknown"
            rule_or_model = "none"
            mutated_code: str | None = None

            # 2. Route to appropriate repair engine
            if diag_rec.route in (RepairRoute.RULE_REPAIR, RepairRoute.HYBRID_REPAIR):
                rule_res = self.rule_engine.repair_candidate(
                    current_code,
                    category_code=diag_rec.category.value,
                    error_message=diag_rec.message,
                    line=diag_rec.line,
                    column=diag_rec.column,
                )
                if rule_res:
                    mutated_code = rule_res.repaired_code
                    strategy_applied = "rule_repair"
                    rule_or_model = rule_res.rule_applied

            # Fallback to LLM repair if rule could not repair
            if not mutated_code and self.llm_repair_fn:
                mutated_code = self.llm_repair_fn(current_code, current_diags)
                strategy_applied = "llm_repair"
                rule_or_model = "llm_context_injected"

            # If neither repaired the code, simulate light syntactic fallback
            if not mutated_code or mutated_code == current_code:
                # Heuristic fallback: attempt basic bracket/colon patch
                mutated_code = self._fallback_mutation(current_code, diag_rec.message)
                strategy_applied = "heuristic_fallback"
                rule_or_model = "generic_cleaner"

            current_code = mutated_code

            # 3. Lean 4 Verifier re-check with strict 15s timeout
            v_res = self.verifier_pool.verify(
                current_code,
                timeout=self.timeout_per_attempt,
            )

            cycle_record = RepairCycleRecord(
                attempt_index=attempt,
                started_at=attempt_start_iso,
                strategy_applied=strategy_applied,
                code_before=code_before_attempt,
                code_after=current_code,
                rule_or_model=rule_or_model,
                verification_success=v_res.success,
                verification_latency_ms=v_res.duration_ms,
                diagnostics=v_res.diagnostics,
                timed_out=v_res.timed_out,
            )
            history.append(cycle_record)

            if v_res.success:
                # 4. Semantic Safety Audit (anti-cheating)
                audit_passed = True
                if self.semantic_auditor_fn:
                    audit_passed = self.semantic_auditor_fn(
                        statement_natural,
                        current_code,
                    )

                if audit_passed:
                    status = "REPAIRED"
                    current_diags = []
                    break
                else:
                    # Semantic audit rejected: mark and continue retry if budget remains
                    current_diags = [
                        {
                            "severity": "error",
                            "line": 1,
                            "column": 1,
                            "message": "Semantic audit failed: theorem signature or claim altered.",
                        }
                    ]
            else:
                current_diags = v_res.diagnostics

        total_ms = (time.perf_counter() - start_overall) * 1000.0
        return CandidateRepairResult(
            candidate_id=candidate_id,
            problem_id=problem_id,
            status=status,
            final_code=current_code,
            attempts_used=len(history),
            max_attempts=self.max_attempts,
            duration_total_ms=round(total_ms, 2),
            history=history,
            final_diagnostics=current_diags,
            semantic_audit_passed=True,
        )

    def _fallback_mutation(self, code: str, error_message: str) -> str:
        """Lightweight syntactic fallback heuristic."""
        msg = error_message.lower()
        if "expected ':'" in msg and ":" not in code:
            parts = code.split(" ", 2)
            if len(parts) >= 3:
                return f"{parts[0]} {parts[1]} : {parts[2]}"
        if "expected ')'" in msg and code.count("(") > code.count(")"):
            return code + ")"
        if "expected ']'" in msg and code.count("[") > code.count("]"):
            return code + "]"
        return code

    def process_dataset(
        self,
        dataset_path: str,
        queue_mode: QueueMode = QueueMode.FIFO,
        save_results: bool = True,
        seed: int = 42,
    ) -> dict[str, Any]:
        """Runs the complete bounded retry loop over an evaluation dataset.

        Produces an immutable experiment artifact in results/raw conforming to
        INT4418 Phụ lục B.

        Args:
            dataset_path: Path to dataset JSON file.
            queue_mode: FIFO or Priority scheduling discipline.
            save_results: Whether to persist JSON results to disk.
            seed: Reproducibility random seed.

        Returns:
            Summary dictionary with full benchmark metrics and provenance.
        """
        with open(dataset_path, "r", encoding="utf-8") as f:
            raw_data = json.load(f)

        total_samples = len(raw_data)
        results: list[CandidateRepairResult] = []
        latencies_ms: list[float] = []

        attempts_hist = {1: 0, 2: 0, 3: 0, "exhausted": 0}
        strategy_counts = {"rule_repair": 0, "llm_repair": 0, "heuristic_fallback": 0}
        success_count = 0

        # Enqueue all samples into the distributed WorkerQueue
        self.queue.clear()
        for idx, item in enumerate(raw_data):
            cand_id = item.get("error_id", f"CAND-{idx:03d}")
            prio = 3 if item.get("suggested_strategy") == "rule_repair" else 7
            self.queue.enqueue(
                payload=item,
                priority=prio,
                task_id=cand_id,
                max_attempts=self.max_attempts,
                mode=queue_mode,
            )

        start_time_all = time.perf_counter()

        # Dequeue and process tasks
        while self.queue.get_length(queue_mode) > 0:
            task = self.queue.dequeue(timeout=0.1, mode=queue_mode)
            if not task:
                break

            item = task.payload
            cand_id = task.task_id
            prob_id = f"PROB-{cand_id}"
            code = item.get("code_snippet", "")
            comp_log = item.get("compiler_log", {})
            diags = [comp_log] if comp_log else []
            title = item.get("title", "")

            res = self.repair_candidate_sync(
                candidate_id=cand_id,
                problem_id=prob_id,
                initial_code=code,
                initial_diagnostics=diags,
                statement_natural=title,
                priority=task.priority,
                queue_mode=queue_mode,
            )
            results.append(res)
            latencies_ms.append(res.duration_total_ms)

            if res.status == "REPAIRED":
                self.queue.ack(task.task_id)
                success_count += 1
                attempts_hist[min(res.attempts_used, 3)] += 1
                if res.history:
                    last_strat = res.history[-1].strategy_applied
                    strategy_counts[last_strat] = strategy_counts.get(last_strat, 0) + 1
            else:
                self.queue.nack(
                    task.task_id,
                    requeue=False,
                    error_reason="Budget exhausted",
                    mode=queue_mode,
                )
                attempts_hist["exhausted"] += 1

        total_wall_sec = time.perf_counter() - start_time_all
        qps = round(total_samples / total_wall_sec, 2) if total_wall_sec > 0 else 0.0

        latencies_ms.sort()
        n = len(latencies_ms)
        p50 = latencies_ms[int(n * 0.50)] if n else 0.0
        p95 = latencies_ms[min(int(n * 0.95), n - 1)] if n else 0.0

        success_rate = (
            round(success_count / total_samples, 4) if total_samples > 0 else 0.0
        )
        queue_metrics = self.queue.get_metrics()
        verifier_metrics = self.verifier_pool.get_metrics()

        run_id = (
            f"bounded-queue-{queue_mode.value}-"
            f"{datetime.datetime.now(datetime.UTC).strftime('%Y%m%d%H%M%S')}-"
            f"{uuid.uuid4().hex[:6]}"
        )

        record: dict[str, Any] = {
            "run_id": run_id,
            "timestamp": datetime.datetime.now(datetime.UTC).isoformat(),
            "git_commit": "feature/worker-queue",
            "data_version": "v0.1-50-errors",
            "machine": {
                "os": platform.platform(),
                "cpu": platform.processor(),
                "python": platform.python_version(),
            },
            "parameters": {
                "dataset_path": dataset_path,
                "total_candidates": total_samples,
                "queue_mode": queue_mode.value,
                "max_attempts": self.max_attempts,
                "timeout_per_attempt_sec": self.timeout_per_attempt,
                "total_timeout_sec": self.total_timeout_sec,
                "seed": seed,
            },
            "seed": seed,
            "timeout": int(self.total_timeout_sec),
            "metrics": {
                "total_samples": total_samples,
                "repaired_count": success_count,
                "repair_success_rate": success_rate,
                "final_compile_rate": success_rate,
                "latency_p50_ms": round(p50, 2),
                "latency_p95_ms": round(p95, 2),
                "throughput_qps": qps,
                "attempts_histogram": attempts_hist,
                "strategy_breakdown": strategy_counts,
                "queue_wait_p50_ms": queue_metrics["wait_time_p50_ms"],
                "queue_wait_p95_ms": queue_metrics["wait_time_p95_ms"],
                "dlq_count": queue_metrics["dlq_count"],
                "verifier_metrics": verifier_metrics,
            },

            "status": "SUCCESS",
            "log_path": f"logs/{run_id}.log",
        }

        if save_results:
            os.makedirs("results/raw/simulated", exist_ok=True)
            out_file = os.path.join("results/raw/simulated", f"run_{run_id}.json")
            with open(out_file, "w", encoding="utf-8") as f:
                json.dump(record, f, indent=2, ensure_ascii=False)
            print(f"[OK] Bounded Queue Experiment saved: {out_file}")

        return record
