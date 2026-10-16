"""Unit tests for the semantic safety auditor."""

import unittest

from src.lean_verifier import STATUS_ERROR, STATUS_OK, VerificationResult
from src.semantic_auditor import audit, normalize_statement

REF = "theorem t (x : ℝ) (h : 0 < x) : 0 < x * x"
GOOD = "import Mathlib\ntheorem t (x : ℝ) (h : 0 < x) : 0 < x * x := by\n  positivity\n"
OK = VerificationResult(status=STATUS_OK)


class TestAuditor(unittest.TestCase):
    def test_clean_repair_passes(self) -> None:
        self.assertTrue(audit(GOOD, OK, REF).passed)

    def test_whitespace_differences_ignored(self) -> None:
        code = GOOD.replace("(x : ℝ) (h : 0 < x)", "( x : ℝ )\n    (h : 0 < x)")
        self.assertTrue(audit(code, OK, REF).passed)

    def test_changed_type_is_flagged(self) -> None:
        code = GOOD.replace("ℝ", "ℕ")
        res = audit(code, OK, REF)
        self.assertFalse(res.passed)
        self.assertIn("statement_changed", res.reasons)

    def test_weakened_goal_is_flagged(self) -> None:
        code = GOOD.replace("0 < x * x", "0 ≤ x * x")
        self.assertIn("statement_changed", audit(code, OK, REF).reasons)

    def test_sorry_and_axiom_flagged(self) -> None:
        sorry_res = VerificationResult(status=STATUS_OK, uses_sorry=True)
        code = GOOD.replace("positivity", "sorry")
        self.assertIn("uses_sorry", audit(code, sorry_res, REF).reasons)
        code = "axiom cheat : False\n" + GOOD
        self.assertIn("forbidden_construct", audit(code, OK, REF).reasons)

    def test_forbidden_word_in_comment_is_ignored(self) -> None:
        code = GOOD.replace("by\n", "by\n  -- no sorry here\n")
        self.assertTrue(audit(code, OK, REF).passed)

    def test_not_compiled(self) -> None:
        res = audit(GOOD, VerificationResult(status=STATUS_ERROR), REF)
        self.assertEqual(res.reasons, ["does_not_compile"])

    def test_normalize(self) -> None:
        self.assertEqual(normalize_statement("f ( a , b ) :  c"), "f(a,b):c")


if __name__ == "__main__":
    unittest.main()
