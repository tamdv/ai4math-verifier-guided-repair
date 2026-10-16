"""Unit tests for LeanErrorParser."""

import unittest
from src.error_parser import LeanErrorParser, ErrorCategory, RepairRoute


class TestErrorParser(unittest.TestCase):
    def test_syntax_error_classification(self):
        diag = {"line": 1, "column": 10, "message": "unexpected token ':', expected ')'"}
        record = LeanErrorParser.parse_diagnostic(diag)
        self.assertEqual(record.category, ErrorCategory.SYNTAX_ERROR)
        self.assertEqual(record.route, RepairRoute.RULE_REPAIR)

    def test_missing_import_classification(self):
        diag = {"line": 1, "column": 1, "message": "unknown package 'Mathlib.Data.Real.Basic'"}
        record = LeanErrorParser.parse_diagnostic(diag)
        self.assertEqual(record.category, ErrorCategory.MISSING_IMPORT)
        self.assertEqual(record.route, RepairRoute.RULE_REPAIR)

    def test_type_mismatch_classification(self):
        diag = {"line": 2, "column": 15, "message": "type mismatch at term 3, has type Nat but expected Int"}
        record = LeanErrorParser.parse_diagnostic(diag)
        self.assertEqual(record.category, ErrorCategory.TYPE_MISMATCH)
        self.assertEqual(record.route, RepairRoute.LLM_REPAIR)

    def test_timeout_classification(self):
        diag = {"line": 5, "column": 1, "message": "maximum heartbeats exceeded (200000)"}
        record = LeanErrorParser.parse_diagnostic(diag)
        self.assertEqual(record.category, ErrorCategory.TIMEOUT_EXCEEDED)
        self.assertEqual(record.route, RepairRoute.SYSTEM_CONTROL)


class TestRealLeanMessages(unittest.TestCase):
    """Messages captured verbatim from Lean 4.35 + Mathlib on the 50-sample set."""

    CASES = [
        ("unexpected token 'in'; expected ','", "SYN_01"),
        ("unexpected end of input; expected ':=', 'where' or '|'", "SYN_01"),
        ("unknown module prefix 'Mathlib'\n\nNo directory 'Mathlib'", "IMP_02"),
        ("object file '/x/Mathlib/Data/Nat/Prime.olean' of module Mathlib.Data.Nat.Prime "
         "does not exist", "IMP_02"),
        ("Unknown identifier `le_div_iff`", "ID_03"),
        ("Unknown constant `Nat.add_com`", "ID_03"),
        ("Invalid field `len`: The environment does not contain `List.len`", "ID_03"),
        ("Invalid field notation: Field projection operates on types of the form `C ...`",
         "TYP_04"),
        ("failed to synthesize instance of type class\n  HAdd Real Float Real", "TYP_04"),
        ("type mismatch\n  h\nhas type\n  a = b", "TYP_04"),
        ("(deterministic) timeout at `whnf`, maximum number of heartbeats (400000)",
         "TMO_05"),
        ("unsolved goals\nn : ℕ\n⊢ n + 0 = n", "TAC_07"),
        ("linarith failed to find a contradiction", "TAC_07"),
        ("omega could not prove the goal:\nNo usable constraints found.", "TAC_07"),
        ("Tactic `decide` proved that the proposition\n  7 < 5\nis false", "TAC_07"),
        ("declaration uses `sorry`", "SEM_06"),
        ("not a positivity goal", "TAC_07"),
        ("No goals to be solved", "TAC_07"),
        ("Alternative `succ` has not been provided", "TAC_07"),
    ]

    def test_cases(self):
        for message, expected in self.CASES:
            cat, _ = LeanErrorParser.classify_message(message)
            self.assertEqual(cat.value, expected, message)

    def test_missing_import_inferred_from_code(self):
        code = "theorem t (x : ℝ) : 0 ≤ x ^ 2 := by positivity"
        cat, route = LeanErrorParser.classify_message("Unknown identifier `x`", code)
        self.assertEqual(cat, ErrorCategory.MISSING_IMPORT)
        cat, _ = LeanErrorParser.classify_message("Unknown identifier `x`", "import Mathlib\n" + code)
        self.assertEqual(cat, ErrorCategory.UNKNOWN_IDENTIFIER)

    def test_primary_prefers_first_error(self):
        diags = [
            {"severity": "warning", "line": 1, "column": 0, "message": "declaration uses `sorry`"},
            {"severity": "error", "line": 3, "column": 2, "message": "unsolved goals"},
            {"severity": "error", "line": 2, "column": 5, "message": "unknown tactic"},
        ]
        self.assertEqual(LeanErrorParser.primary(diags).category, ErrorCategory.UNKNOWN_IDENTIFIER)
        self.assertEqual(LeanErrorParser.primary(diags[:1]).category,
                         ErrorCategory.SEMANTIC_MISMATCH)
        self.assertIsNone(LeanErrorParser.primary([]))

    def test_unsolved_goals_is_a_consequence(self):
        # Real Kaggle case: misspelt tactic at line 17, `unsolved goals` at the declaration.
        diags = [
            {"severity": "error", "line": 17, "column": 31, "message": "unknown tactic"},
            {"severity": "error", "line": 9, "column": 147, "message": "unsolved goals\nx : ℝ"},
        ]
        self.assertEqual(LeanErrorParser.primary(diags).category, ErrorCategory.UNKNOWN_IDENTIFIER)
        only = [diags[1]]
        self.assertEqual(LeanErrorParser.primary(only).category, ErrorCategory.TACTIC_FAILURE)


if __name__ == "__main__":
    unittest.main()
