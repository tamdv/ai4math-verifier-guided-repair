"""Unit tests for run_experiment helpers (no Lean, no API)."""

import unittest

from scripts.run_experiment import list_or_raise


class TestListOrRaise(unittest.TestCase):
    def test_startup_failure_surfaces_immediately(self) -> None:
        def broken():
            raise RuntimeError("GEMINI_API_KEY is not set")
            yield  # pragma: no cover

        with self.assertRaises(RuntimeError):
            list_or_raise(broken())

    def test_stream_is_preserved(self) -> None:
        self.assertEqual(list(list_or_raise(iter([1, 2, 3]))), [1, 2, 3])
        self.assertEqual(list(list_or_raise(iter([]))), [])


if __name__ == "__main__":
    unittest.main()
