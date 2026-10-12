"""Comprehensive Unit & Integration Test Suite for Queue & Worker System.

Tests cover:
- FIFO vs Priority Queue scheduling disciplines
- Task acknowledgment, in-flight recovery, and Dead Letter Queue (DLQ)
- Lean 4 Verifier Worker Pool concurrent execution and timeout enforcement
- Bounded Retry Controller closed-loop lifecycle and budget limits
- Integration with sample error dataset (Phụ lục B metrics validation)
"""

import os
import time
import unittest

from src.bounded_controller import BoundedRetryController
from src.rule_repair import RuleRepairEngine
from src.verifier_pool import LeanVerifierWorker, VerifierWorkerPool
from src.worker_queue import QueueMode, WorkerQueue


class TestWorkerQueue(unittest.TestCase):
    """Unit tests for WorkerQueue operations."""

    def setUp(self):
        """Initializes a fresh in-memory / test queue before each test."""
        self.queue = WorkerQueue(
            prefix="test:ai4math:queue",
            use_fallback=True,
        )
        self.queue.clear()

    def tearDown(self):
        """Cleans up queue resources."""
        self.queue.clear()
        self.queue.close()

    def test_fifo_ordering(self):
        """Validates that FIFO mode pops tasks in exact order of arrival."""
        self.queue.enqueue({"id": "A"}, mode=QueueMode.FIFO)
        self.queue.enqueue({"id": "B"}, mode=QueueMode.FIFO)
        self.queue.enqueue({"id": "C"}, mode=QueueMode.FIFO)

        self.assertEqual(self.queue.get_length(QueueMode.FIFO), 3)

        t1 = self.queue.dequeue(timeout=0.1, mode=QueueMode.FIFO)
        t2 = self.queue.dequeue(timeout=0.1, mode=QueueMode.FIFO)
        t3 = self.queue.dequeue(timeout=0.1, mode=QueueMode.FIFO)

        self.assertIsNotNone(t1)
        self.assertIsNotNone(t2)
        self.assertIsNotNone(t3)

        self.assertEqual(t1.payload["id"], "A")
        self.assertEqual(t2.payload["id"], "B")
        self.assertEqual(t3.payload["id"], "C")
        self.assertEqual(self.queue.get_length(QueueMode.FIFO), 0)

    def test_priority_ordering(self):
        """Validates that Priority mode pops highest-priority tasks first (lower score)."""
        # Enqueue with different priorities out of order
        self.queue.enqueue({"id": "LOW"}, priority=10, mode=QueueMode.PRIORITY)
        self.queue.enqueue({"id": "HIGH"}, priority=1, mode=QueueMode.PRIORITY)
        self.queue.enqueue({"id": "MED"}, priority=5, mode=QueueMode.PRIORITY)

        self.assertEqual(self.queue.get_length(QueueMode.PRIORITY), 3)

        t1 = self.queue.dequeue(timeout=0.1, mode=QueueMode.PRIORITY)
        t2 = self.queue.dequeue(timeout=0.1, mode=QueueMode.PRIORITY)
        t3 = self.queue.dequeue(timeout=0.1, mode=QueueMode.PRIORITY)

        self.assertEqual(t1.payload["id"], "HIGH")
        self.assertEqual(t2.payload["id"], "MED")
        self.assertEqual(t3.payload["id"], "LOW")

    def test_ack_workflow(self):
        """Validates in-flight tracking and acknowledgment."""
        self.queue.enqueue({"task": "verify"}, mode=QueueMode.FIFO)
        task = self.queue.dequeue(timeout=0.1, mode=QueueMode.FIFO)

        self.assertIsNotNone(task)
        self.assertEqual(self.queue.get_inflight_length(), 1)

        success = self.queue.ack(task.task_id)
        self.assertTrue(success)
        self.assertEqual(self.queue.get_inflight_length(), 0)

    def test_nack_requeue_and_priority_bump(self):
        """Validates that nack requeues task with incremented attempt and bumped priority."""
        self.queue.enqueue(
            {"task": "retry_me"}, priority=5, max_attempts=3, mode=QueueMode.FIFO
        )
        task = self.queue.dequeue(timeout=0.1, mode=QueueMode.FIFO)

        handled = self.queue.nack(
            task.task_id,
            requeue=True,
            increase_priority=True,
            error_reason="Compiler Syntax Error",
            mode=QueueMode.FIFO,
        )
        self.assertTrue(handled)
        self.assertEqual(self.queue.get_inflight_length(), 0)
        self.assertEqual(self.queue.get_length(QueueMode.FIFO), 1)

        # Dequeue the retried task
        retried = self.queue.dequeue(timeout=0.1, mode=QueueMode.FIFO)
        self.assertIsNotNone(retried)
        self.assertEqual(retried.attempts, 1)
        self.assertEqual(retried.priority, 4)  # Priority bumped from 5 to 4
        self.assertEqual(retried.error_reason, "Compiler Syntax Error")

    def test_dead_letter_queue_on_exhaustion(self):
        """Validates that exceeding max_attempts routes task to Dead Letter Queue."""
        self.queue.enqueue({"task": "failing"}, max_attempts=2, mode=QueueMode.FIFO)

        # Attempt 1
        t1 = self.queue.dequeue(timeout=0.1, mode=QueueMode.FIFO)
        self.queue.nack(t1.task_id, requeue=True, mode=QueueMode.FIFO)
        self.assertEqual(self.queue.get_dlq_length(), 0)

        # Attempt 2 (budget exhausted)
        t2 = self.queue.dequeue(timeout=0.1, mode=QueueMode.FIFO)
        self.queue.nack(
            t2.task_id, requeue=True, error_reason="Hard Failure", mode=QueueMode.FIFO
        )

        self.assertEqual(self.queue.get_length(QueueMode.FIFO), 0)
        self.assertEqual(self.queue.get_dlq_length(), 1)

    def test_metrics_calculation(self):
        """Validates queue wait time and throughput metrics."""
        self.queue.enqueue({"id": "M1"}, mode=QueueMode.FIFO)
        time.sleep(0.01)
        t = self.queue.dequeue(timeout=0.1, mode=QueueMode.FIFO)
        self.queue.ack(t.task_id)

        metrics = self.queue.get_metrics()
        self.assertGreaterEqual(metrics["enqueued_total"], 1)
        self.assertGreaterEqual(metrics["dequeued_total"], 1)
        self.assertGreaterEqual(metrics["acked_total"], 1)
        self.assertGreater(metrics["wait_time_p50_ms"], 0.0)


class TestVerifierWorkerPool(unittest.TestCase):
    """Unit tests for Lean 4 Verifier Worker Pool."""

    def setUp(self):
        self.pool = VerifierWorkerPool(num_workers=2, default_timeout=15.0)

    def tearDown(self):
        self.pool.close()

    def test_verify_valid_code(self):
        """Verifies that syntactically valid Lean code passes."""
        valid_code = "theorem test_thm (n : Nat) : n = n := by rfl"
        res = self.pool.verify(valid_code)
        self.assertTrue(res.success)
        self.assertEqual(len(res.diagnostics), 0)
        self.assertGreater(res.duration_ms, 0.0)

    def test_verify_invalid_brackets(self):
        """Verifies that unmatched brackets produce structured compiler diagnostics."""
        broken_code = "theorem test_thm (a b : Real) (h : (a + b = 2 : a = 2 - b"
        res = self.pool.verify(broken_code)
        self.assertFalse(res.success)
        self.assertGreater(len(res.diagnostics), 0)
        self.assertEqual(res.diagnostics[0]["severity"], "error")

    def test_verify_timeout_enforcement(self):
        """Verifies strict timeout enforcement at worker level."""
        # Use a worker with artificially small timeout
        worker = LeanVerifierWorker(
            worker_id="test-timeout",
            default_timeout=0.0001,
            enable_simulation_fallback=False,  # If native Lean is invoked with 0.0001s, it must timeout
        )
        if worker.has_native_lean:
            res = worker.verify_code("theorem hang : True := by sorry", timeout=0.0001)
            self.assertTrue(res.timed_out)
            self.assertFalse(res.success)

    def test_verify_batch_concurrency(self):
        """Verifies concurrent batch verification across multiple worker threads."""
        codes = [
            "theorem t1 : True := by trivial",
            "theorem t2 (n : Nat) n > 0",  # Missing colon
            "theorem t3 : 1 + 1 = 2 := by rfl",
        ]
        results = self.pool.verify_batch(codes)
        self.assertEqual(len(results), 3)
        self.assertTrue(results[0].success)
        self.assertFalse(results[1].success)
        self.assertTrue(results[2].success)

        metrics = self.pool.get_metrics()
        self.assertEqual(metrics["total_verified"], 3)
        self.assertEqual(metrics["success_count"], 2)


class TestBoundedRetryController(unittest.TestCase):
    """Unit tests for Bounded Retry Controller."""

    def setUp(self):
        self.queue = WorkerQueue(prefix="test:bounded:queue", use_fallback=True)
        self.pool = VerifierWorkerPool(num_workers=2, default_timeout=15.0)
        self.rule_engine = RuleRepairEngine()
        self.controller = BoundedRetryController(
            queue=self.queue,
            verifier_pool=self.pool,
            rule_engine=self.rule_engine,
            max_attempts=3,
            timeout_per_attempt=15.0,
        )

    def tearDown(self):
        self.queue.clear()
        self.queue.close()
        self.pool.close()

    def test_repair_syntax_error_success(self):
        """Verifies that a bracket syntax error is repaired on attempt 1."""
        broken_code = "theorem bar (a b : Real) (h : (a + b = 2 : a = 2 - b"
        diagnostics = [
            {
                "severity": "error",
                "line": 1,
                "column": 41,
                "message": "unexpected token ':', expected ')'",
            }
        ]

        res = self.controller.repair_candidate_sync(
            candidate_id="ERR-002",
            problem_id="PROB-002",
            initial_code=broken_code,
            initial_diagnostics=diagnostics,
        )

        self.assertEqual(res.status, "REPAIRED")
        self.assertEqual(res.attempts_used, 1)
        self.assertIn(")", res.final_code)
        self.assertEqual(len(res.history), 1)
        self.assertTrue(res.history[0].verification_success)

    def test_repair_missing_colon_success(self):
        """Verifies that missing colon in theorem definition is repaired."""
        broken_code = "theorem foo (n : Nat) n > 0"
        diagnostics = [
            {
                "severity": "error",
                "line": 1,
                "column": 23,
                "message": "expected ':'",
            }
        ]

        res = self.controller.repair_candidate_sync(
            candidate_id="ERR-001",
            problem_id="PROB-001",
            initial_code=broken_code,
            initial_diagnostics=diagnostics,
        )

        self.assertEqual(res.status, "REPAIRED")
        self.assertIn(":", res.final_code)

    def test_exhausted_retry_budget_to_unrepairable(self):
        """Verifies that unfixable syntax respects max_attempts bound and marks UNREPAIRABLE."""
        # Unfixable gibberish with high error
        unfixable_code = "xyz_invalid_keyword_non_existent @@@ 123"
        diagnostics = [
            {
                "severity": "error",
                "line": 1,
                "column": 1,
                "message": "fatal unexpected non-lean symbol",
            }
        ]

        res = self.controller.repair_candidate_sync(
            candidate_id="ERR-UNFIXABLE",
            problem_id="PROB-UNFIXABLE",
            initial_code=unfixable_code,
            initial_diagnostics=diagnostics,
        )

        self.assertEqual(res.status, "UNREPAIRABLE")
        self.assertEqual(res.attempts_used, 3)  # Exhausted max_attempts = 3
        self.assertEqual(len(res.history), 3)

    def test_dataset_process_end_to_end(self):
        """Runs complete closed-loop repair over sample dataset."""
        dataset_path = "data_sample/error_dataset_50.json"
        if not os.path.exists(dataset_path):
            self.skipTest(f"Dataset {dataset_path} not found.")

        record = self.controller.process_dataset(
            dataset_path=dataset_path,
            queue_mode=QueueMode.PRIORITY,
            save_results=False,
        )

        self.assertEqual(record["status"], "SUCCESS")
        metrics = record["metrics"]
        self.assertEqual(metrics["total_samples"], 50)
        self.assertGreater(metrics["repaired_count"], 0)
        self.assertGreater(metrics["throughput_qps"], 0.0)
        self.assertIn("attempts_histogram", metrics)
        self.assertIn("queue_wait_p95_ms", metrics)


if __name__ == "__main__":
    unittest.main()
