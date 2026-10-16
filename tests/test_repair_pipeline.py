"""Unit tests for the bounded repair loop (stub verifier + MockClient)."""

import unittest

from src.lean_verifier import STATUS_ERROR, STATUS_OK, VerificationResult
from src.llm_client import MockClient
from src.llm_repair import LLMRepairEngine
from src.repair_pipeline import RepairPipeline, RepairPolicy

ORIGINAL = "import Mathlib\nimport Aesop\n\ntheorem t (x : ℝ) : 0 ≤ x ^ 2 := by\n  positivity\n"
STATEMENT = "theorem t (x : ℝ) : 0 ≤ x ^ 2"


def sample(code: str, message: str, error_id: str = "E1") -> dict:
    return {
        "error_id": error_id,
        "code": code,
        "statement": STATEMENT,
        "diagnostics": [{"severity": "error", "line": 4, "column": 2, "message": message}],
    }


class TableVerifier:
    """Compiles exactly the codes in `good`; counts calls."""

    def __init__(self, good: set[str]) -> None:
        self.good = good
        self.calls = 0

    def verify(self, code: str) -> VerificationResult:
        self.calls += 1
        if code in self.good:
            return VerificationResult(status=STATUS_OK)
        return VerificationResult(
            status=STATUS_ERROR,
            diagnostics=[{"severity": "error", "line": 4, "column": 2, "message": "unsolved goals"}],
        )


def llm(reply: str, mode: str) -> LLMRepairEngine:
    return LLMRepairEngine(MockClient(reply=f"```lean\n{reply}```"), mode=mode)


class TestRepairPipeline(unittest.TestCase):
    def test_rule_fixes_missing_import_without_tokens(self) -> None:
        broken = ORIGINAL.replace("import Mathlib\nimport Aesop\n\n", "")
        v = TableVerifier({ORIGINAL})
        out = RepairPipeline(v, RepairPolicy("hybrid", 3), llm_diag=llm("x", "diagnostic")).run(
            sample(broken, "Unknown identifier `x`"))
        self.assertTrue(out.success)
        self.assertEqual(out.attempts[0].rule, "R0_restore_mathlib_import")
        self.assertEqual(out.total_tokens, 0)
        self.assertEqual(out.llm_calls, 0)

    def test_hybrid_falls_back_to_llm(self) -> None:
        broken = ORIGINAL.replace("positivity", "linarith")
        v = TableVerifier({ORIGINAL})
        out = RepairPipeline(v, RepairPolicy("hybrid", 3),
                             llm_diag=llm(ORIGINAL, "diagnostic")).run(
            sample(broken, "linarith failed to find a contradiction"))
        self.assertTrue(out.success)
        self.assertEqual(out.attempts[0].engine, "llm_diagnostic")
        self.assertGreater(out.total_tokens, 0)

    def test_statement_change_is_not_success(self) -> None:
        cheat = ORIGINAL.replace("0 ≤ x ^ 2", "True").replace("positivity", "trivial")
        v = TableVerifier({cheat})
        out = RepairPipeline(v, RepairPolicy("llm_only", 1),
                             llm_diag=llm(cheat, "diagnostic")).run(
            sample(ORIGINAL.replace("positivity", "linarith"), "linarith failed"))
        self.assertFalse(out.success)
        self.assertTrue(out.compiled)
        self.assertIn("statement_changed", out.attempts[0].audit_reasons)

    def test_duplicate_candidate_stops_loop(self) -> None:
        bad = ORIGINAL.replace("positivity", "simp")
        v = TableVerifier(set())
        out = RepairPipeline(v, RepairPolicy("llm_only", 5),
                             llm_diag=llm(bad, "diagnostic")).run(
            sample(ORIGINAL.replace("positivity", "linarith"), "linarith failed"))
        self.assertFalse(out.success)
        self.assertEqual(out.stop_reason, "duplicate")
        self.assertEqual(out.attempts_used, 2)
        self.assertEqual(v.calls, 1)

    def test_budget_zero_and_none(self) -> None:
        v = TableVerifier(set())
        for policy in (RepairPolicy("none", 3), RepairPolicy("rule_only", 0)):
            out = RepairPipeline(v, policy).run(sample(ORIGINAL, "unsolved goals"))
            self.assertEqual(out.attempts_used, 0)
            self.assertEqual(out.stop_reason, "no_repair")
        self.assertEqual(v.calls, 0)

    def test_rule_only_stops_when_no_rule(self) -> None:
        out = RepairPipeline(TableVerifier(set()), RepairPolicy("rule_only", 3)).run(
            sample(ORIGINAL, "unsolved goals"))
        self.assertEqual(out.stop_reason, "no_rule")

    def test_blind_requires_engine(self) -> None:
        with self.assertRaises(ValueError):
            RepairPipeline(TableVerifier(set()), RepairPolicy("blind", 1))


if __name__ == "__main__":
    unittest.main()
