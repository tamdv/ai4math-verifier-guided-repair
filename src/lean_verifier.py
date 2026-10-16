"""Lean 4 Verifier wrapper: compiles a Lean snippet and returns structured diagnostics.

Runs `lean --json` (or `lake env lean --json` inside a Lake project such as a
Mathlib workspace) on a temporary file with a hard timeout. This is the ground
truth used to decide whether a repair actually compiles.
"""

import json
import os
import shutil
import subprocess
import tempfile
import time
from collections.abc import Callable
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

DEFAULT_TIMEOUT_S = 15.0
ELAN_BIN = Path.home() / ".elan" / "bin"

STATUS_OK = "OK"
STATUS_ERROR = "ERROR"
STATUS_TIMEOUT = "TIMEOUT"
STATUS_TOOL_MISSING = "TOOL_MISSING"

Runner = Callable[[list[str], str | None, float], subprocess.CompletedProcess]


@dataclass
class VerificationResult:
    """Outcome of compiling one Lean snippet."""

    status: str
    diagnostics: list[dict[str, Any]] = field(default_factory=list)
    latency_ms: float = 0.0
    uses_sorry: bool = False
    stderr: str = ""

    @property
    def compiled(self) -> bool:
        """True if Lean accepted the file with no error-level diagnostics."""
        return self.status == STATUS_OK

    @property
    def proved(self) -> bool:
        """True if the file compiled and no declaration relies on `sorry`."""
        return self.compiled and not self.uses_sorry

    @property
    def errors(self) -> list[dict[str, Any]]:
        """Error-level diagnostics only."""
        return [d for d in self.diagnostics if d.get("severity") == "error"]

    def to_dict(self) -> dict[str, Any]:
        """Serializable form for raw result logs."""
        return {
            "status": self.status,
            "compiled": self.compiled,
            "proved": self.proved,
            "uses_sorry": self.uses_sorry,
            "latency_ms": self.latency_ms,
            "diagnostics": self.diagnostics,
        }


def _default_runner(
    cmd: list[str], cwd: str | None, timeout_s: float
) -> subprocess.CompletedProcess:
    return subprocess.run(
        cmd, cwd=cwd, capture_output=True, text=True, timeout=timeout_s, check=False
    )


def _find_executable(name: str) -> str | None:
    found = shutil.which(name)
    if found:
        return found
    candidate = ELAN_BIN / name
    return str(candidate) if candidate.exists() else None


def parse_json_diagnostics(stdout: str) -> list[dict[str, Any]]:
    """Parses `lean --json` output (one JSON object per line) into flat diagnostics.

    Args:
        stdout: Raw stdout of `lean --json`.

    Returns:
        A list of dicts with severity, line, column, end_line, end_column, message.
        Non-JSON lines are kept as error diagnostics so nothing is silently dropped.
    """
    diagnostics = []
    for raw in stdout.splitlines():
        raw = raw.strip()
        if not raw:
            continue
        try:
            msg = json.loads(raw)
        except json.JSONDecodeError:
            diagnostics.append(
                {"severity": "error", "line": 0, "column": 0, "message": raw}
            )
            continue
        diagnostics.append(diagnostic_from_message(msg))
    return diagnostics


def diagnostic_from_message(msg: dict[str, Any]) -> dict[str, Any]:
    """Flattens one Lean message (`lean --json` or REPL format) into a diagnostic."""
    pos = msg.get("pos") or {}
    end = msg.get("endPos") or {}
    return {
        "severity": msg.get("severity", "error"),
        "line": pos.get("line", 0),
        "column": pos.get("column", 0),
        "end_line": end.get("line"),
        "end_column": end.get("column"),
        "message": msg.get("data", ""),
    }


class LeanVerifier:
    """Compiles Lean 4 code via the local toolchain.

    Args:
        project_dir: Optional Lake project (e.g. with Mathlib). If set, runs
            `lake env lean --json` inside it so `import Mathlib` resolves.
        timeout_s: Wall-clock limit per file; exceeded runs return TIMEOUT.
        runner: Injectable subprocess runner (used by unit tests).
    """

    def __init__(
        self,
        project_dir: str | Path | None = None,
        timeout_s: float = DEFAULT_TIMEOUT_S,
        runner: Runner | None = None,
    ) -> None:
        self.project_dir = str(project_dir) if project_dir else None
        self.timeout_s = timeout_s
        self._runner = runner or _default_runner
        self._lean = _find_executable("lean")
        self._lake = _find_executable("lake")

    @property
    def available(self) -> bool:
        """Whether the required toolchain binaries were found."""
        if self.project_dir:
            return self._lake is not None
        return self._lean is not None

    def _command(self, file_path: str) -> list[str]:
        if self.project_dir:
            return [self._lake or "lake", "env", "lean", "--json", file_path]
        return [self._lean or "lean", "--json", file_path]

    def verify(self, code: str) -> VerificationResult:
        """Compiles `code` and classifies the outcome.

        Args:
            code: Full Lean 4 source text.

        Returns:
            VerificationResult with status OK / ERROR / TIMEOUT / TOOL_MISSING.
        """
        if not self.available and self._runner is _default_runner:
            return VerificationResult(status=STATUS_TOOL_MISSING)

        fd, path = tempfile.mkstemp(suffix=".lean", dir=self.project_dir)
        start = time.perf_counter()
        try:
            with os.fdopen(fd, "w", encoding="utf-8") as f:
                f.write(code if code.endswith("\n") else code + "\n")
            try:
                proc = self._runner(self._command(path), self.project_dir, self.timeout_s)
            except subprocess.TimeoutExpired:
                return VerificationResult(
                    status=STATUS_TIMEOUT,
                    latency_ms=round((time.perf_counter() - start) * 1000, 3),
                )
        finally:
            if os.path.exists(path):
                os.remove(path)

        latency_ms = round((time.perf_counter() - start) * 1000, 3)
        diagnostics = parse_json_diagnostics(proc.stdout)
        has_error = any(d["severity"] == "error" for d in diagnostics)
        if proc.returncode != 0 and not has_error:
            # Non-zero exit without a parsed error (e.g. crash): surface stderr.
            diagnostics.append(
                {"severity": "error", "line": 0, "column": 0, "message": proc.stderr.strip()}
            )
            has_error = True
        uses_sorry = any("sorry" in d["message"] for d in diagnostics)

        return VerificationResult(
            status=STATUS_ERROR if has_error else STATUS_OK,
            diagnostics=diagnostics,
            latency_ms=latency_ms,
            uses_sorry=uses_sorry,
            stderr=proc.stderr,
        )
