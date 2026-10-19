"""Experiment provenance helpers (CLAUDE.md Rule 3).

Every run record written to `results/raw/run_<run_id>.json` gets the same
machine / software / git metadata from here.
"""

import datetime
import json
import os
import platform
import subprocess
import uuid
from pathlib import Path
from typing import Any

from src.lean_verifier import _find_executable

ROOT = Path(__file__).resolve().parent.parent
RAW_DIR = ROOT / "results" / "raw"


def _run(cmd: list[str]) -> str:
    try:
        return subprocess.run(cmd, capture_output=True, text=True, check=True, cwd=ROOT).stdout.strip()
    except (OSError, subprocess.CalledProcessError):
        return "unknown"


def git_commit() -> str:
    """Current HEAD hash, suffixed with `-dirty` if the tree has local changes."""
    head = _run(["git", "rev-parse", "HEAD"])
    # The cost ledger is appended during LLM runs; it is data, not code.
    dirty = _run(["git", "status", "--porcelain", "--untracked-files=no", "--", ".",
                  ":(exclude)results/cost_ledger.jsonl"])
    return f"{head}-dirty" if dirty and dirty != "unknown" else head


def gpu_info() -> str:
    """GPU names from nvidia-smi, or "none" (every reported run is CPU-only)."""
    out = _run(["nvidia-smi", "--query-gpu=name", "--format=csv,noheader"])
    return "none" if out in ("", "unknown") else "; ".join(out.splitlines())


def machine_info() -> dict[str, Any]:
    """CPU / RAM / GPU / OS of the current host."""
    info: dict[str, Any] = {
        "os": platform.platform(),
        "cpu": platform.processor() or platform.machine(),
        "cpu_count": os.cpu_count(),
        "gpu": gpu_info(),
    }
    try:
        import psutil

        info["ram_gb"] = round(psutil.virtual_memory().total / 2**30, 1)
    except ImportError:
        pass
    return info


def software_info() -> dict[str, Any]:
    """Python, key package and Lean toolchain versions."""
    from importlib import metadata

    lean = _find_executable("lean")
    packages = {}
    for name in ("google-genai", "pyyaml", "psutil", "pyarrow", "matplotlib"):
        try:
            packages[name] = metadata.version(name)
        except metadata.PackageNotFoundError:
            packages[name] = None
    return {
        "python": platform.python_version(),
        "lean": _run([lean, "--version"]) if lean else "missing",
        "packages": packages,
    }


def new_run_id(prefix: str) -> str:
    """`<prefix>-<UTC timestamp>-<6 hex>`."""
    stamp = datetime.datetime.now(datetime.timezone.utc).strftime("%Y%m%d%H%M%S")
    return f"{prefix}-{stamp}-{uuid.uuid4().hex[:6]}"


def write_run_record(
    prefix: str,
    parameters: dict[str, Any],
    metrics: dict[str, Any],
    data_version: str,
    seed: int,
    timeout: float,
    status: str = "SUCCESS",
    extra: dict[str, Any] | None = None,
    run_id: str | None = None,
) -> Path:
    """Writes an immutable run record and returns its path."""
    run_id = run_id or new_run_id(prefix)
    record = {
        "run_id": run_id,
        "timestamp": datetime.datetime.now(datetime.timezone.utc).isoformat(),
        "git_commit": git_commit(),
        "data_version": data_version,
        "machine": machine_info(),
        "software": software_info(),
        "parameters": parameters,
        "seed": seed,
        "timeout": timeout,
        "metrics": metrics,
        "status": status,
    }
    if extra:
        record.update(extra)
    RAW_DIR.mkdir(parents=True, exist_ok=True)
    path = RAW_DIR / f"run_{run_id}.json"
    path.write_text(json.dumps(record, indent=2, ensure_ascii=False), encoding="utf-8")
    return path


def percentile(values: list[float], q: float) -> float:
    """Nearest-rank percentile (q in [0, 1]); 0.0 for empty input."""
    if not values:
        return 0.0
    ordered = sorted(values)
    return float(ordered[min(int(len(ordered) * q), len(ordered) - 1)])
