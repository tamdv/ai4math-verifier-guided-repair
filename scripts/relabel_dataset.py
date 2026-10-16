"""Re-derive error labels from a real Lean 4 compile instead of hand-written logs.

For every sample, compiles `code_snippet` with `LeanVerifier`, stores the real
first diagnostic as `lean_log`, re-classifies it with `LeanErrorParser`, and
flags samples whose original label disagrees with Lean. The original
`compiler_log` / `category_code` are kept untouched for traceability.

Usage:
    python3 scripts/relabel_dataset.py --data data_sample/error_dataset_50.json \
        --out data_sample/error_dataset_50_lean.json [--lean-project lean_ws]
"""

import argparse
import datetime
import json
import sys
from collections import Counter
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.error_parser import LeanErrorParser  # noqa: E402
from src.lean_verifier import STATUS_TIMEOUT, LeanVerifier  # noqa: E402

LABEL_COMPILES = "COMPILES"  # no error: not a valid error sample
LABEL_SORRY = "SEM_06"  # compiles only thanks to sorry


def relabel_sample(item: dict[str, Any], verifier: LeanVerifier) -> dict[str, Any]:
    """Compiles one sample and attaches the Lean-derived label.

    Args:
        item: Dataset record with at least `code_snippet` and `category_code`.
        verifier: Configured Lean verifier.

    Returns:
        A copy of `item` with `lean_status`, `lean_log`, `lean_category_code`
        and `label_agrees` added.
    """
    res = verifier.verify(item.get("code_snippet", ""))
    out = dict(item)
    out["lean_status"] = res.status
    out["lean_latency_ms"] = res.latency_ms

    if res.status == STATUS_TIMEOUT:
        out["lean_log"] = {"severity": "error", "line": 0, "column": 0, "message": "timeout"}
        out["lean_category_code"] = "TMO_05"
    elif res.errors:
        first = res.errors[0]
        out["lean_log"] = {k: first.get(k) for k in ("severity", "line", "column", "message")}
        category, _ = LeanErrorParser.classify_message(first["message"])
        out["lean_category_code"] = category.value
    elif res.uses_sorry:
        out["lean_log"] = next(d for d in res.diagnostics if "sorry" in d["message"])
        out["lean_category_code"] = LABEL_SORRY
    else:
        out["lean_log"] = None
        out["lean_category_code"] = LABEL_COMPILES

    out["label_agrees"] = out["lean_category_code"] == item.get("category_code")
    return out


def relabel_dataset(data: list[dict[str, Any]], verifier: LeanVerifier) -> dict[str, Any]:
    """Relabels all samples and returns records plus an agreement summary."""
    records = [relabel_sample(item, verifier) for item in data]
    confusion = Counter((r.get("category_code"), r["lean_category_code"]) for r in records)
    summary = {
        "total": len(records),
        "label_agrees": sum(r["label_agrees"] for r in records),
        "compiles_without_error": sum(
            r["lean_category_code"] == LABEL_COMPILES for r in records
        ),
        "lean_category_counts": dict(Counter(r["lean_category_code"] for r in records)),
        "confusion": {f"{a}->{b}": n for (a, b), n in sorted(confusion.items())},
    }
    return {"records": records, "summary": summary}


def main() -> None:
    parser = argparse.ArgumentParser(description="Relabel error dataset with real Lean output")
    parser.add_argument("--data", default="data_sample/error_dataset_50.json")
    parser.add_argument("--out", default="data_sample/error_dataset_50_lean.json")
    parser.add_argument("--lean-project", default=None, help="Lake project dir (Mathlib)")
    parser.add_argument("--timeout", type=float, default=60.0)
    args = parser.parse_args()

    verifier = LeanVerifier(project_dir=args.lean_project, timeout_s=args.timeout)
    if not verifier.available:
        sys.exit("Lean toolchain not found (run scripts/install_lean4.sh)")

    with open(args.data, "r", encoding="utf-8") as f:
        data = json.load(f)

    result = relabel_dataset(data, verifier)
    summary = result["summary"]
    summary.update(
        {
            "source": args.data,
            "lean_project": args.lean_project,
            "timestamp": datetime.datetime.now(datetime.timezone.utc).isoformat(),
        }
    )

    with open(args.out, "w", encoding="utf-8") as f:
        json.dump(result["records"], f, indent=2, ensure_ascii=False)
    summary_path = Path(args.out).with_suffix(".summary.json")
    with open(summary_path, "w", encoding="utf-8") as f:
        json.dump(summary, f, indent=2, ensure_ascii=False)

    print(f"[OK] Relabeled {summary['total']} samples -> {args.out}")
    print(f"     Label agrees with Lean: {summary['label_agrees']}/{summary['total']}")
    print(f"     Compiles without error: {summary['compiles_without_error']}")
    print(f"     Lean categories: {summary['lean_category_counts']}")
    print(f"     Summary: {summary_path}")


if __name__ == "__main__":
    main()
