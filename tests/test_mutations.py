"""Unit tests for error-injection operators (pure text, no Lean)."""

import random
import unittest

from src.mutations import (
    MUTATIONS,
    id_lemma_typo,
    id_tactic_typo,
    imp_drop_import,
    sem_sorry,
    syn_drop_assign,
    syn_drop_paren,
    tac_weaken,
    theorem_statement,
    tmo_low_heartbeats,
    typ_change_type,
)

SEED = """import Mathlib
import Aesop

set_option maxHeartbeats 400000

open Real

/- comment with mul_pos_iff inside -/
theorem lw_1 (x : ℝ) (h : 0 < x) : 0 < x * x := by
  /- proof sketch using sq_nonneg -/
  nlinarith [mul_pos h h, sq_nonneg x]
"""


class TestMutations(unittest.TestCase):
    def setUp(self) -> None:
        self.rng = random.Random(0)

    def test_every_operator_changes_seed(self) -> None:
        for m in MUTATIONS:
            out = m.fn(SEED, random.Random(1))
            self.assertIsNotNone(out, m.name)
            self.assertNotEqual(out, SEED, m.name)

    def test_syn_drop_paren_only_touches_statement(self) -> None:
        out = syn_drop_paren(SEED, self.rng)
        self.assertEqual(out.count(")"), SEED.count(")") - 1)
        self.assertIn("nlinarith [mul_pos h h, sq_nonneg x]", out)

    def test_syn_drop_assign(self) -> None:
        out = syn_drop_assign(SEED, self.rng)
        self.assertIn("0 < x * x  by", out)

    def test_imp_drop_import(self) -> None:
        out = imp_drop_import(SEED, self.rng)
        self.assertNotIn("import", out)
        self.assertTrue(out.startswith("set_option"))

    def test_lemma_typo_ignores_comments_and_tactics(self) -> None:
        out = id_lemma_typo(SEED, self.rng)
        self.assertTrue("mul_pos h h" not in out or "sq_nonneg x" not in out)
        self.assertIn("mul_pos_iff", out)  # comment untouched
        self.assertIn("nlinarith", out)

    def test_tactic_typo(self) -> None:
        self.assertIn("nlinarth", id_tactic_typo(SEED, self.rng))

    def test_typ_change_type(self) -> None:
        out = typ_change_type(SEED, self.rng)
        self.assertIn("(x : ℕ)", out)

    def test_tac_weaken_drops_hints(self) -> None:
        out = tac_weaken(SEED, self.rng)
        self.assertIn("  linarith\n", out)
        self.assertNotIn("sq_nonneg x]", out)

    def test_tmo_and_sorry(self) -> None:
        self.assertIn("maxHeartbeats 500", tmo_low_heartbeats(SEED, self.rng))
        out = sem_sorry(SEED, self.rng)
        self.assertTrue(out.rstrip().endswith("sorry"))
        self.assertEqual(theorem_statement(out), theorem_statement(SEED))

    def test_statement_extraction(self) -> None:
        self.assertEqual(theorem_statement(SEED), "theorem lw_1 (x : ℝ) (h : 0 < x) : 0 < x * x")

    def test_not_applicable_returns_none(self) -> None:
        self.assertIsNone(tac_weaken("theorem t : True := trivial", self.rng))
        self.assertIsNone(imp_drop_import("theorem t : True := trivial", self.rng))


if __name__ == "__main__":
    unittest.main()
