"""Unit tests for the Group 5 gateway (stub verifier + MockClient, no Lean, no tokens)."""

import hashlib
import json
import tempfile
import unittest
from pathlib import Path

from scripts.repair_batch import (
    STATUS_ALREADY_VALID,
    STATUS_FAILED,
    STATUS_SUCCESS,
    process,
    read_input,
    run_batch,
    validate,
    write_outputs,
)
from src.lean_verifier import STATUS_ERROR, STATUS_OK, VerificationResult
from src.llm_client import MockClient
from src.llm_repair import LLMRepairEngine
from src.repair_pipeline import RepairPipeline, RepairPolicy
from src.verifier_pool import VerifierPool

GOOD = "import Mathlib\nimport Aesop\n\ntheorem t (x : ℝ) : 0 ≤ x ^ 2 := by\n  positivity\n"
NO_IMPORT = GOOD.replace("import Mathlib\nimport Aesop\n\n", "")
BAD_TACTIC = GOOD.replace("positivity", "linarith")
USES_AXIOM = "axiom cheat : False\n" + GOOD


class TableVerifier:
    """Compiles exactly the codes in `good`; everything else fails with `message`."""

    def __init__(self, good: set[str], message: str = "linarith failed") -> None:
        self.good, self.message = good, message

    def verify(self, code: str) -> VerificationResult:
        if code in self.good:
            return VerificationResult(status=STATUS_OK)
        return VerificationResult(status=STATUS_ERROR, diagnostics=[
            {"severity": "error", "line": 4, "column": 2, "message": self.message}])


def record(cid: str, code: str, **extra: object) -> dict:
    return {"candidate_id": cid, "problem_id": "P" + cid, "candidate_code": code,
            "statement_natural": "x squared is nonnegative", "split": "test",
            "source_dataset": "minif2f", **extra}


def pipeline(verifier: TableVerifier, strategy: str = "hybrid", reply: str = GOOD) -> RepairPipeline:
    diag = LLMRepairEngine(MockClient(reply=f"```lean\n{reply}```"), mode="diagnostic")
    return RepairPipeline(verifier, RepairPolicy(strategy, 3), llm_diag=diag)


class TestValidate(unittest.TestCase):
    def test_rejects_missing_checksum_mismatch_and_duplicates(self) -> None:
        recs = [
            record("A", GOOD, checksum_sha256=hashlib.sha256(GOOD.encode()).hexdigest()),
            record("B", GOOD),
            record("C", BAD_TACTIC, checksum_sha256="0" * 64),
            {**record("D", BAD_TACTIC), "split": ""},
        ]
        accepted, rejected = validate(recs)
        self.assertEqual([r["candidate_id"] for r in accepted], ["A"])
        self.assertEqual({r["candidate_id"]: r["reason"] for r in rejected},
                         {"B": "duplicate_code", "C": "checksum_mismatch", "D": "missing_fields"})
        self.assertEqual(rejected[-1]["fields"], ["split"])


class TestProcess(unittest.TestCase):
    def test_valid_candidate_is_not_repaired(self) -> None:
        from scripts.repair_batch import to_sample

        out = process(pipeline(TableVerifier({GOOD})), to_sample(record("A", GOOD)))
        self.assertEqual(out["status"], STATUS_ALREADY_VALID)
        self.assertIsNone(out["outcome"])

    def test_axiom_is_not_already_valid(self) -> None:
        from scripts.repair_batch import to_sample

        v = TableVerifier({GOOD, USES_AXIOM})
        out = process(pipeline(v, reply=GOOD), to_sample(record("A", USES_AXIOM)))
        self.assertNotEqual(out["status"], STATUS_ALREADY_VALID)

    def test_rule_repair_uses_fresh_diagnostics(self) -> None:
        from scripts.repair_batch import to_sample

        v = TableVerifier({GOOD}, message="unknown identifier 'positivity'")
        out = process(pipeline(v, strategy="rule_only"), to_sample(record("A", NO_IMPORT)))
        self.assertEqual(out["status"], STATUS_SUCCESS)
        self.assertEqual(out["sample"]["category"], "IMP_02")
        self.assertEqual(out["outcome"]["total_tokens"], 0)


class TestRunBatch(unittest.TestCase):
    def run_all(self, strategy: str, reply: str = GOOD) -> dict:
        recs = [record("A", GOOD), record("B", BAD_TACTIC), record("C", BAD_TACTIC + "\n")]
        pool = VerifierPool(lambda: pipeline(TableVerifier({GOOD}), strategy, reply), 2,
                            task=process)
        return run_batch(recs, pool)

    def test_feedback_statuses_and_strategy(self) -> None:
        batch = self.run_all("llm_only")
        fb = {f["candidate_id"]: f for f in batch["feedback"]}
        self.assertEqual(fb["A"]["final_status"], STATUS_ALREADY_VALID)
        self.assertEqual(fb["B"]["final_status"], STATUS_SUCCESS)
        self.assertEqual(fb["B"]["repair_strategy"], "llm_repair")
        self.assertEqual(fb["B"]["repaired_code"], GOOD)
        self.assertGreater(fb["B"]["total_tokens"], 0)

    def test_failed_repair_has_no_code(self) -> None:
        batch = self.run_all("llm_only", reply=BAD_TACTIC.replace("linarith", "simp"))
        fb = {f["candidate_id"]: f for f in batch["feedback"]}
        self.assertEqual(fb["B"]["final_status"], STATUS_FAILED)
        self.assertIsNone(fb["B"]["repaired_code"])
        self.assertIsNone(fb["B"]["repair_strategy"])

    def test_outputs_written(self) -> None:
        batch = self.run_all("llm_only")
        with tempfile.TemporaryDirectory() as tmp:
            out = Path(tmp)
            counts = write_outputs(batch, out, {"verified_by": "lean-test", "run_id": "R",
                                                "git_commit": "abc", "strategy": "llm_only",
                                                "model": "mock"})
            self.assertEqual(counts["repaired"], 2)
            rows = [json.loads(x) for x in (out / "repaired_v1.jsonl").read_text().splitlines()]
            self.assertEqual({r["error_id"] for r in rows}, {"B", "C"})
            self.assertEqual(rows[0]["source"], "group5:minif2f")
            self.assertEqual(rows[0]["seed_id"], "P" + rows[0]["error_id"])
            self.assertEqual(len(read_input(out / "feedback_group5.jsonl")), 3)


if __name__ == "__main__":
    unittest.main()
