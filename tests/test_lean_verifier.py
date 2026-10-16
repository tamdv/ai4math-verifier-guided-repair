"""Unit tests for the Lean 4 verifier wrapper (subprocess is mocked)."""

import subprocess
import tempfile
import unittest

from src.lean_verifier import (
    STATUS_ERROR,
    STATUS_OK,
    STATUS_TIMEOUT,
    LeanVerifier,
    parse_json_diagnostics,
)

ERROR_LINE = (
    '{"severity":"error","pos":{"line":1,"column":23},"endPos":{"line":1,"column":24},'
    '"fileName":"x.lean","data":"unexpected token; expected \':\'"}'
)
SORRY_LINE = (
    '{"severity":"warning","pos":{"line":1,"column":8},"endPos":null,'
    '"fileName":"x.lean","data":"declaration uses \'sorry\'"}'
)


def fake_runner(stdout: str = "", returncode: int = 0, stderr: str = ""):
    calls = []

    def run(cmd, cwd, timeout_s):
        calls.append(cmd)
        return subprocess.CompletedProcess(cmd, returncode, stdout=stdout, stderr=stderr)

    run.calls = calls
    return run


class TestParseDiagnostics(unittest.TestCase):
    def test_parses_position_and_message(self) -> None:
        diags = parse_json_diagnostics(ERROR_LINE + "\n")
        self.assertEqual(len(diags), 1)
        self.assertEqual(diags[0]["severity"], "error")
        self.assertEqual(diags[0]["line"], 1)
        self.assertEqual(diags[0]["column"], 23)
        self.assertIn("expected ':'", diags[0]["message"])

    def test_non_json_line_kept_as_error(self) -> None:
        diags = parse_json_diagnostics("panic: something\n")
        self.assertEqual(diags[0]["severity"], "error")


class TestLeanVerifier(unittest.TestCase):
    def test_clean_compile_is_ok_and_proved(self) -> None:
        v = LeanVerifier(runner=fake_runner(stdout=""))
        res = v.verify("theorem t : 1 = 1 := rfl")
        self.assertEqual(res.status, STATUS_OK)
        self.assertTrue(res.proved)

    def test_error_diagnostic_is_error(self) -> None:
        v = LeanVerifier(runner=fake_runner(stdout=ERROR_LINE, returncode=1))
        res = v.verify("theorem foo (n : Nat) n > 0")
        self.assertEqual(res.status, STATUS_ERROR)
        self.assertFalse(res.compiled)
        self.assertEqual(len(res.errors), 1)

    def test_sorry_compiles_but_not_proved(self) -> None:
        v = LeanVerifier(runner=fake_runner(stdout=SORRY_LINE))
        res = v.verify("theorem t : 1 = 1 := sorry")
        self.assertTrue(res.compiled)
        self.assertTrue(res.uses_sorry)
        self.assertFalse(res.proved)

    def test_nonzero_exit_without_json_is_error(self) -> None:
        v = LeanVerifier(runner=fake_runner(returncode=1, stderr="unknown package 'Mathlib'"))
        res = v.verify("import Mathlib")
        self.assertEqual(res.status, STATUS_ERROR)
        self.assertIn("Mathlib", res.errors[0]["message"])

    def test_timeout(self) -> None:
        def slow(cmd, cwd, timeout_s):
            raise subprocess.TimeoutExpired(cmd, timeout_s)

        res = LeanVerifier(runner=slow, timeout_s=0.1).verify("theorem t : True := by trivial")
        self.assertEqual(res.status, STATUS_TIMEOUT)

    def test_plain_mode_calls_lean_json(self) -> None:
        runner = fake_runner()
        LeanVerifier(runner=runner).verify("example : True := trivial")
        self.assertIn("--json", runner.calls[0])
        self.assertNotIn("env", runner.calls[0])

    def test_project_dir_uses_lake_env(self) -> None:
        runner = fake_runner()
        with tempfile.TemporaryDirectory() as tmp:
            LeanVerifier(project_dir=tmp, runner=runner).verify("example : True := trivial")
        self.assertEqual(runner.calls[0][1:4], ["env", "lean", "--json"])


if __name__ == "__main__":
    unittest.main()
