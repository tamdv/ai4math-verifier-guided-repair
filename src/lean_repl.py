"""Persistent Lean 4 verifier backed by the Lean REPL (leanprover-community/repl).

Cold `lake env lean file.lean` re-imports Mathlib on every call (60-100 s on a
16 GB laptop). The REPL imports Mathlib once into environment 0 and then checks
each snippet against that environment in milliseconds.

Import handling (so IMP_02 errors stay observable):
- snippet with `import Mathlib...` lines: the imports are validated against the
  Mathlib build (unknown modules -> error, as cold Lean would report), stripped,
  and the body is checked in the pre-imported Mathlib environment;
- snippet without imports: checked in a pre-built core-only environment (no
  Mathlib), so missing Mathlib names fail exactly as they would in a real file.
"""

import json
import os
import queue
import re
import subprocess
import threading
import time
from pathlib import Path
from typing import Any

from src.lean_verifier import (
    DEFAULT_TIMEOUT_S,
    STATUS_ERROR,
    STATUS_OK,
    STATUS_TIMEOUT,
    VerificationResult,
    _find_executable,
    diagnostic_from_message,
)

DEFAULT_PROJECT = Path(__file__).resolve().parent.parent / "lean_ws"
REPL_REL_PATH = Path(".lake/packages/REPL/.lake/build/bin/repl")
IMPORT_RE = re.compile(r"^\s*import\s+(.+)$")


def split_imports(code: str) -> tuple[list[str], str, int]:
    """Separates leading `import` lines from the body.

    Returns:
        (imported module names, body text, number of header lines removed) so
        diagnostic line numbers can be shifted back to the original file.
    """
    lines = code.splitlines()
    modules: list[str] = []
    idx = 0
    while idx < len(lines):
        stripped = lines[idx].strip()
        match = IMPORT_RE.match(lines[idx])
        if match:
            modules.extend(match.group(1).split())
        elif stripped and not stripped.startswith("--"):
            break
        idx += 1
    return modules, "\n".join(lines[idx:]), idx


class LeanREPLVerifier:
    """Long-lived REPL process with Mathlib pre-imported.

    Args:
        project_dir: Lake workspace containing Mathlib and the REPL package.
        timeout_s: Wall-clock limit per snippet. On expiry the process is
            killed and restarted (expensive), so Lean's own heartbeat limit
            should catch most runaway tactics first.
        max_commands: Restart after this many commands to bound memory growth.
        preload: Import Mathlib at construction time.
    """

    def __init__(
        self,
        project_dir: str | Path = DEFAULT_PROJECT,
        timeout_s: float = DEFAULT_TIMEOUT_S,
        max_commands: int = 2000,
        preload: bool = True,
    ) -> None:
        self.project_dir = str(project_dir)
        self.timeout_s = timeout_s
        self.max_commands = max_commands
        self._lake = _find_executable("lake")
        self._proc: subprocess.Popen[str] | None = None
        self._lines: queue.Queue[str | None] = queue.Queue()
        self._mathlib_env: int | None = None
        self._core_env: int | None = None
        self._commands = 0
        self.import_latency_ms = 0.0
        self.restarts = 0
        if preload and self.available:
            self._start()

    @property
    def available(self) -> bool:
        """Whether lake and the REPL binary exist."""
        return self._lake is not None and (Path(self.project_dir) / REPL_REL_PATH).exists()

    # ---- process management -------------------------------------------------
    def _start(self) -> None:
        env = dict(os.environ)
        if self._lake:
            env["PATH"] = f"{Path(self._lake).parent}:{env.get('PATH', '')}"
        self._proc = subprocess.Popen(
            [self._lake or "lake", "env", str(REPL_REL_PATH)],
            cwd=self.project_dir,
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL,
            text=True,
            env=env,
        )
        self._lines = queue.Queue()
        threading.Thread(target=self._pump, args=(self._proc, self._lines), daemon=True).start()
        self._commands = 0
        start = time.perf_counter()
        # Importing Mathlib can take minutes on a cold page cache.
        resp = self._send({"cmd": "import Mathlib"}, timeout_s=max(self.timeout_s, 900.0))
        self.import_latency_ms = round((time.perf_counter() - start) * 1000, 3)
        if resp is None or "env" not in resp:
            raise RuntimeError(f"REPL failed to import Mathlib: {resp}")
        self._mathlib_env = resp["env"]
        core = self._send({"cmd": ""}, timeout_s=60.0)
        self._core_env = core["env"] if core and "env" in core else None

    @staticmethod
    def _pump(proc: subprocess.Popen[str], out: "queue.Queue[str | None]") -> None:
        assert proc.stdout is not None
        for line in proc.stdout:
            out.put(line)
        out.put(None)

    def close(self) -> None:
        """Terminates the REPL process."""
        if self._proc and self._proc.poll() is None:
            self._proc.kill()
            self._proc.wait()
        self._proc = None

    def restart(self) -> None:
        """Kills and relaunches the REPL (re-imports Mathlib)."""
        self.close()
        self.restarts += 1
        self._start()

    def __enter__(self) -> "LeanREPLVerifier":
        return self

    def __exit__(self, *exc: object) -> None:
        self.close()

    # ---- protocol -----------------------------------------------------------
    def _send(self, obj: dict[str, Any], timeout_s: float) -> dict[str, Any] | None:
        """Sends one JSON command; returns the parsed reply or None on timeout/EOF."""
        assert self._proc is not None and self._proc.stdin is not None
        self._proc.stdin.write(json.dumps(obj, ensure_ascii=False) + "\n\n")
        self._proc.stdin.flush()
        deadline = time.monotonic() + timeout_s
        buf: list[str] = []
        while True:
            remaining = deadline - time.monotonic()
            if remaining <= 0:
                return None
            try:
                line = self._lines.get(timeout=remaining)
            except queue.Empty:
                return None
            if line is None:
                return None
            if line.strip() == "" and buf:
                break
            buf.append(line)
        return json.loads("".join(buf))

    def _module_exists(self, module: str) -> bool:
        """True if `module` is built in any package of the workspace (Mathlib deps)."""
        rel = Path(*module.split(".")).with_suffix(".olean")
        packages = Path(self.project_dir) / ".lake" / "packages"
        return any(
            (pkg / ".lake" / "build" / "lib" / "lean" / rel).exists()
            for pkg in packages.iterdir()
            if pkg.is_dir()
        )

    def verify(self, code: str) -> VerificationResult:
        """Checks `code` and returns the same result type as `LeanVerifier`."""
        if self._proc is None or self._proc.poll() is not None:
            self._start()
        elif self._commands >= self.max_commands:
            self.restart()

        modules, body, offset = split_imports(code)
        missing = [m for m in modules if not self._module_exists(m)]
        if missing:
            return VerificationResult(
                status=STATUS_ERROR,
                diagnostics=[
                    {
                        "severity": "error",
                        "line": 1,
                        "column": 0,
                        "message": f"unknown module prefix or module does not exist: {m}",
                    }
                    for m in missing
                ],
            )

        cmd: dict[str, Any] = {"cmd": body}
        env_id = self._mathlib_env if modules else self._core_env
        if env_id is not None:
            cmd["env"] = env_id
        start = time.perf_counter()
        resp = self._send(cmd, timeout_s=self.timeout_s)
        latency_ms = round((time.perf_counter() - start) * 1000, 3)
        self._commands += 1

        if resp is None:
            self.restart()
            return VerificationResult(status=STATUS_TIMEOUT, latency_ms=latency_ms)

        if "message" in resp and "messages" not in resp and "env" not in resp:
            # REPL-level error (e.g. malformed command).
            diags = [{"severity": "error", "line": 0, "column": 0, "message": resp["message"]}]
        else:
            diags = [diagnostic_from_message(m) for m in resp.get("messages", [])]
        for d in diags:
            if d.get("line"):
                d["line"] += offset
            if d.get("end_line"):
                d["end_line"] += offset

        has_error = any(d["severity"] == "error" for d in diags)
        uses_sorry = bool(resp.get("sorries")) or any("sorry" in d["message"] for d in diags)
        return VerificationResult(
            status=STATUS_ERROR if has_error else STATUS_OK,
            diagnostics=diags,
            latency_ms=latency_ms,
            uses_sorry=uses_sorry,
        )
