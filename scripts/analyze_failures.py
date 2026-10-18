"""Error analysis from replayable run logs (no Lean, no API).

For the first repeat of every 1K hold-out configuration, reads the per-sample log
and writes Markdown/CSV tables to results/figures/:
  table_stop_reasons      why the bounded loop stopped, per strategy
  table_audit_failures    why the last attempt was rejected (audit reasons)
  table_rule_precision    per-rule precision when a rule fired (rule_only + hybrid)
  table_success_by_source synthetic vs natural (version-drift) errors
  table_attempt_of_success at which attempt successes happen (k=3 runs)

Usage:
    python3 scripts/analyze_failures.py --input results/raw/ --output results/figures/
"""

import argparse
import collections
import gzip
import json
import sys
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from scripts.generate_figures import write_table  # noqa: E402


def load_runs(raw: Path) -> list[tuple[str, dict[str, Any], list[dict[str, Any]]]]:
    """(label, run record, log entries) for repeat 1 of each 1K hold-out config."""
    out = []
    for path in sorted(raw.glob("run_exp-*.json")):
        rec = json.loads(path.read_text(encoding="utf-8"))
        p = rec["parameters"]
        if (rec.get("status") != "SUCCESS" or p.get("split") != "holdout" or p.get("limit")
                or Path(p.get("data", "")).name != "errors_1k.jsonl"
                or p.get("tag") in ("scale", "scale-llm", "pilot")
                or p.get("repeat_index", 0) not in (0, 1)):
            continue
        log = raw / "logs" / f"{rec['run_id']}.jsonl.gz"
        if not log.exists():
            continue
        with gzip.open(log, "rt", encoding="utf-8") as f:
            entries = [json.loads(line) for line in f if line.strip()]
        model = p["model"] if p["strategy"] in ("blind", "llm_only", "hybrid") else "-"
        label = f"{p['strategy']} k={p['budget']}" + ("" if model in ("-", "gemini-3.5-flash-lite")
                                                       else f" [{model}]")
        out.append((label, rec, [e for e in entries if "attempts" in e]))
    # keep one run per label (earliest)
    seen, unique = set(), []
    for item in out:
        if item[0] not in seen:
            seen.add(item[0])
            unique.append(item)
    return unique


def pct(a: int, b: int) -> str:
    return f"{100 * a / b:.1f}" if b else "-"


def main() -> None:
    parser = argparse.ArgumentParser(description="Failure analysis from run logs")
    parser.add_argument("--input", default="results/raw/")
    parser.add_argument("--output", default="results/figures/")
    args = parser.parse_args()
    out = Path(args.output)
    out.mkdir(parents=True, exist_ok=True)
    runs = load_runs(Path(args.input))

    stop_rows, audit_rows, source_rows, attempt_rows = [], [], [], []
    rule_stats: dict[str, list[int]] = collections.defaultdict(lambda: [0, 0])
    stop_keys = ["success", "budget_exhausted", "no_rule", "duplicate", "wall_budget", "no_repair"]
    audit_keys = ["does_not_compile", "statement_changed", "uses_sorry", "forbidden_construct",
                  "theorem_missing"]
    for label, rec, entries in runs:
        n = len(entries)
        stops = collections.Counter(e["stop_reason"] for e in entries)
        stop_rows.append({"configuration": label, "n": n,
                          **{f"{k} %": pct(stops.get(k, 0), n) for k in stop_keys}})

        failed_last = [e["attempts"][-1] for e in entries if not e["success"] and e["attempts"]]
        reasons = collections.Counter(r for a in failed_last for r in a["audit_reasons"])
        audit_rows.append({"configuration": label, "failed with attempt": len(failed_last),
                           **{f"{k} %": pct(reasons.get(k, 0), len(failed_last))
                              for k in audit_keys}})

        by_src = collections.defaultdict(lambda: [0, 0])
        for e in entries:
            by_src[e.get("source", "?")][0] += e["success"]
            by_src[e.get("source", "?")][1] += 1
        source_rows.append({"configuration": label,
                            **{f"{s} success %": f"{pct(v[0], v[1])} (n={v[1]})"
                               for s, v in sorted(by_src.items())}})

        if rec["parameters"]["budget"] >= 3:
            at = collections.Counter(len(e["attempts"]) for e in entries if e["success"])
            total = sum(at.values())
            attempt_rows.append({"configuration": label, "successes": total,
                                 **{f"at attempt {i} %": pct(at.get(i, 0), total)
                                    for i in (1, 2, 3)}})

        if rec["parameters"]["strategy"] in ("rule_only", "hybrid"):
            for e in entries:
                for a in e["attempts"]:
                    if a["engine"] == "rule" and a.get("rule"):
                        rule_stats[a["rule"]][0] += a["audit_passed"]
                        rule_stats[a["rule"]][1] += 1

    rule_rows = [{"rule": r, "fired": v[1], "passed audit": v[0], "precision %": pct(v[0], v[1])}
                 for r, v in sorted(rule_stats.items(), key=lambda kv: -kv[1][1])]
    write_table(stop_rows, out, "table_stop_reasons")
    write_table(audit_rows, out, "table_audit_failures")
    write_table(rule_rows, out, "table_rule_precision")
    write_table(source_rows, out, "table_success_by_source")
    write_table(attempt_rows, out, "table_attempt_of_success")
    print(f"[OK] {len(runs)} configurations analysed -> {out}")
    for name in ["table_stop_reasons", "table_audit_failures", "table_rule_precision",
                 "table_success_by_source", "table_attempt_of_success"]:
        print(f"\n## {name}\n" + (out / f"{name}.md").read_text(encoding="utf-8"))


if __name__ == "__main__":
    main()
