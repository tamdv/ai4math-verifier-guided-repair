"""Unit tests for VerifierPool (stub verifiers, no Lean required)."""

import threading
import unittest

from src.lean_repl import split_imports
from src.lean_verifier import STATUS_ERROR, STATUS_OK, VerificationResult
from src.verifier_pool import VerifierPool


class StubVerifier:
    instances = 0
    lock = threading.Lock()

    def __init__(self) -> None:
        with StubVerifier.lock:
            StubVerifier.instances += 1
        self.closed = False

    def verify(self, code: str) -> VerificationResult:
        return VerificationResult(status=STATUS_OK if "ok" in code else STATUS_ERROR)

    def close(self) -> None:
        self.closed = True


class TestVerifierPool(unittest.TestCase):
    def test_all_items_verified_once_with_payload(self) -> None:
        StubVerifier.instances = 0
        items = [(f"ok {i}" if i % 2 else f"bad {i}", {"id": i}) for i in range(50)]
        out = list(VerifierPool(StubVerifier, n_workers=4).imap(items))
        self.assertEqual(len(out), 50)
        self.assertEqual(sorted(r.index for r in out), list(range(50)))
        for r in out:
            self.assertEqual(r.payload["id"], r.index)
            self.assertEqual(r.result.compiled, r.index % 2 == 1)
            self.assertGreaterEqual(r.queue_wait_ms, 0)
        self.assertEqual(StubVerifier.instances, 4)

    def test_task_exception_is_returned_not_fatal(self) -> None:
        def task(worker, item):
            if item == "boom":
                raise ValueError("bad item")
            return worker.verify(item)

        items = [("ok", 0), ("boom", 1), ("ok", 2)]
        out = sorted(VerifierPool(StubVerifier, 2, task=task).imap(items), key=lambda r: r.index)
        self.assertIsInstance(out[1].result, ValueError)
        self.assertTrue(out[0].result.compiled and out[2].result.compiled)

    def test_startup_failure_propagates(self) -> None:
        def broken():
            raise RuntimeError("no lean")

        with self.assertRaises(RuntimeError):
            list(VerifierPool(broken, n_workers=2).imap([("x", None)]))


class TestSplitImports(unittest.TestCase):
    def test_header_split_and_offset(self) -> None:
        code = "import Mathlib\nimport Aesop\n\n-- c\ntheorem t : True := trivial"
        mods, body, offset = split_imports(code)
        self.assertEqual(mods, ["Mathlib", "Aesop"])
        self.assertTrue(body.startswith("theorem"))
        self.assertEqual(offset, 4)

    def test_no_imports(self) -> None:
        mods, body, offset = split_imports("theorem t : True := trivial")
        self.assertEqual((mods, offset), ([], 0))


if __name__ == "__main__":
    unittest.main()
