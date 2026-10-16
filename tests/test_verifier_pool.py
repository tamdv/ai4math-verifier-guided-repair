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



class TestReplCrashRecovery(unittest.TestCase):
    """A dying REPL must yield a CRASH result and a restart, not an exception."""

    def _attach_fake(self, verifier, script: str) -> None:
        import queue as q
        import subprocess
        import sys

        proc = subprocess.Popen([sys.executable, "-c", script], stdin=subprocess.PIPE,
                                stdout=subprocess.PIPE, text=True)
        verifier._proc = proc
        verifier._lines = q.Queue()
        threading.Thread(target=verifier._pump, args=(proc, verifier._lines), daemon=True).start()
        verifier._mathlib_env, verifier._core_env = 0, 1

    def test_crash_then_recover(self) -> None:
        from src.lean_repl import LeanREPLVerifier
        from src.lean_verifier import STATUS_CRASH

        v = LeanREPLVerifier(preload=False, timeout_s=5)
        dies = "import sys; sys.stdin.readline(); sys.exit(3)"
        healthy = ("import sys, json\n"
                   "while True:\n"
                   "    line = sys.stdin.readline()\n"
                   "    if not line: break\n"
                   "    if line.strip():\n"
                   "        print(json.dumps({'env': 2}) + '\\n', flush=True)\n")
        self._attach_fake(v, dies)
        v.restart = lambda: self._attach_fake(v, healthy)  # type: ignore[method-assign]
        res = v.verify("theorem t : True := trivial")
        self.assertEqual(res.status, STATUS_CRASH)
        self.assertIn("crashed", res.errors[0]["message"])
        self.assertEqual(v.crashes, 1)
        self.assertTrue(v.verify("theorem t : True := trivial").compiled)
        v.close()


if __name__ == "__main__":
    unittest.main()
