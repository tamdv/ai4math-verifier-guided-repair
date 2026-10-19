"""Unit tests for the parser-ablation label variants (pure, no logs or Lean)."""

import unittest

from scripts.parser_ablation import label
from src.error_parser import ErrorCategory

NO_IMPORT = "theorem t (x : ℝ) : 0 ≤ x ^ 2 := by\n  positivity\n"
DIAGS = [
    {"severity": "error", "line": 1, "column": 0, "message": "unsolved goals\nx : ℝ"},
    {"severity": "error", "line": 2, "column": 2, "message": "unknown identifier 'positivity'"},
]


class TestLabelVariants(unittest.TestCase):
    def test_full_skips_consequence_and_infers_import(self) -> None:
        self.assertEqual(label(DIAGS, NO_IMPORT, "full")[0], ErrorCategory.MISSING_IMPORT)

    def test_no_import_infer_reads_message_only(self) -> None:
        self.assertEqual(label(DIAGS, NO_IMPORT, "no_import_infer")[0],
                         ErrorCategory.UNKNOWN_IDENTIFIER)

    def test_no_consequence_takes_earliest_error(self) -> None:
        self.assertEqual(label(DIAGS, NO_IMPORT, "naive")[0], ErrorCategory.TACTIC_FAILURE)

    def test_no_parser(self) -> None:
        self.assertEqual(label(DIAGS, NO_IMPORT, "no_parser"), (None, None))


if __name__ == "__main__":
    unittest.main()
