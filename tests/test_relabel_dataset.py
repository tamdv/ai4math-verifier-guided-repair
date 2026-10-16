"""Unit tests for Lean-based dataset relabeling (verifier is stubbed)."""

import unittest

from scripts.relabel_dataset import LABEL_COMPILES, relabel_dataset
from src.lean_verifier import STATUS_ERROR, STATUS_OK, VerificationResult


class StubVerifier:
    """Returns a canned result per code snippet."""

    def __init__(self, results: dict[str, VerificationResult]) -> None:
        self.results = results

    def verify(self, code: str) -> VerificationResult:
        return self.results[code]


def err(message: str) -> VerificationResult:
    return VerificationResult(
        status=STATUS_ERROR,
        diagnostics=[{"severity": "error", "line": 1, "column": 2, "message": message}],
    )


class TestRelabel(unittest.TestCase):
    def test_labels_from_real_diagnostics(self) -> None:
        data = [
            {"error_id": "A", "category_code": "SYN_01", "code_snippet": "a"},
            {"error_id": "B", "category_code": "TYP_04", "code_snippet": "b"},
            {"error_id": "C", "category_code": "SEM_06", "code_snippet": "c"},
        ]
        stub = StubVerifier(
            {
                "a": err("unexpected token; expected ':'"),
                "b": VerificationResult(status=STATUS_OK),
                "c": VerificationResult(
                    status=STATUS_OK,
                    diagnostics=[{"severity": "warning", "message": "declaration uses `sorry`"}],
                    uses_sorry=True,
                ),
            }
        )
        out = relabel_dataset(data, stub)
        recs = {r["error_id"]: r for r in out["records"]}

        self.assertEqual(recs["A"]["lean_category_code"], "SYN_01")
        self.assertTrue(recs["A"]["label_agrees"])
        self.assertEqual(recs["A"]["lean_log"]["column"], 2)

        self.assertEqual(recs["B"]["lean_category_code"], LABEL_COMPILES)
        self.assertFalse(recs["B"]["label_agrees"])

        self.assertEqual(recs["C"]["lean_category_code"], "SEM_06")
        self.assertEqual(out["summary"]["label_agrees"], 2)
        self.assertEqual(out["summary"]["compiles_without_error"], 1)
        self.assertEqual(out["summary"]["confusion"]["TYP_04->COMPILES"], 1)

    def test_original_label_preserved(self) -> None:
        data = [{"category_code": "SYN_01", "code_snippet": "a", "compiler_log": {"x": 1}}]
        out = relabel_dataset(data, StubVerifier({"a": err("unexpected token")}))
        self.assertEqual(out["records"][0]["compiler_log"], {"x": 1})
        self.assertEqual(out["records"][0]["category_code"], "SYN_01")


if __name__ == "__main__":
    unittest.main()
