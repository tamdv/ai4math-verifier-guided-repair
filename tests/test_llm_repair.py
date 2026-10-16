"""Unit tests for LLM repair prompts and code extraction (MockClient, 0 tokens)."""

import unittest

from src.llm_client import MockClient
from src.llm_repair import LLMRepairEngine, extract_code, number_lines

CODE = "import Mathlib\ntheorem t (n : ℕ) : n + 0 = n := by\n  simpp\n"
DIAGS = [
    {"severity": "error", "line": 3, "column": 2, "message": "unknown tactic"},
    {"severity": "error", "line": 2, "column": 35, "message": "unsolved goals\nn : ℕ\n⊢ n + 0 = n"},
]


class TestLLMRepair(unittest.TestCase):
    def test_blind_prompt_has_no_diagnostics(self) -> None:
        engine = LLMRepairEngine(MockClient(), mode="blind")
        prompt = engine.build_prompt(CODE, DIAGS)
        self.assertIn("simpp", prompt)
        self.assertNotIn("unknown tactic", prompt)
        self.assertNotIn("ID_03", prompt)

    def test_diagnostic_prompt_has_labels_and_line_numbers(self) -> None:
        engine = LLMRepairEngine(MockClient(), mode="diagnostic")
        prompt = engine.build_prompt(CODE, DIAGS)
        self.assertIn("3:2 [ID_03] unknown tactic", prompt)
        self.assertIn("[TAC_07] unsolved goals", prompt)
        self.assertIn("  3|   simpp", prompt)

    def test_repair_extracts_code_and_counts_tokens(self) -> None:
        reply = "Here:\n```lean\ntheorem t (n : ℕ) : n + 0 = n := by\n  simp\n```"
        client = MockClient(reply=reply)
        attempt = LLMRepairEngine(client, mode="diagnostic").repair(CODE, DIAGS)
        self.assertEqual(attempt.repaired_code, "theorem t (n : ℕ) : n + 0 = n := by\n  simp\n")
        self.assertGreater(attempt.input_tokens, 0)
        self.assertEqual(attempt.prompt_version, "repair_v1")
        self.assertEqual(len(client.calls), 1)

    def test_extract_code_fallbacks(self) -> None:
        self.assertEqual(extract_code("plain text"), "plain text\n")
        self.assertEqual(extract_code("```\na\n```\n```lean4\nb\n```"), "b\n")

    def test_number_lines(self) -> None:
        self.assertEqual(number_lines("a\nb"), "  1| a\n  2| b")

    def test_invalid_mode(self) -> None:
        with self.assertRaises(ValueError):
            LLMRepairEngine(MockClient(), mode="magic")



class TestStripComments(unittest.TestCase):
    SRC = ("import Mathlib\n/- doc\n  spans /- nested -/ lines -/\n"
           "theorem t (x : ℝ) : 0 ≤ x^2 := by -- trailing\n  /- inline -/ positivity\n")

    def test_removes_comments_keeps_lines_and_columns(self) -> None:
        from src.llm_repair import strip_comments

        out = strip_comments(self.SRC)
        self.assertNotIn("doc", out)
        self.assertNotIn("trailing", out)
        self.assertNotIn("inline", out)
        src_lines, out_lines = self.SRC.split("\n"), out.split("\n")
        self.assertEqual(len(src_lines), len(out_lines))
        self.assertEqual(src_lines[4].index("positivity"), out_lines[4].index("positivity"))
        self.assertEqual(out_lines[1], "")
        self.assertEqual(out_lines[3], "theorem t (x : ℝ) : 0 ≤ x^2 := by")


if __name__ == "__main__":
    unittest.main()
