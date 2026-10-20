"""Live / replay demo: broken Lean file -> classify -> repair -> Lean check -> audit.

Live (needs Lean + Mathlib; LLM only if a rule cannot fix it):
    python3 scripts/demo_repair.py --file examples/broken.lean --strategy hybrid --budget 3
    python3 scripts/demo_repair.py --data data/errors/errors_1k.jsonl --error-id E000042

Replay from a run log (no Lean, no API calls, $0) — the fallback for the defense:
    python3 scripts/demo_repair.py --replay results/raw/logs/<run_id>.jsonl.gz --error-id E000042
    python3 scripts/demo_repair.py --replay results/raw/logs/<run_id>.jsonl.gz --pick success
"""

import argparse
import difflib
import gzip
import json
import sys
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.error_parser import LeanErrorParser  # noqa: E402
from src.llm_repair import strip_comments  # noqa: E402
from src.mutations import theorem_statement  # noqa: E402

RULE = "─" * 72
ROOT = Path(__file__).resolve().parent.parent
# Full dataset if downloaded, else the three demo samples shipped in git.
DATA_CANDIDATES = [ROOT / "data" / "errors" / "errors_1k.jsonl", ROOT / "data_sample" / "demo_samples.jsonl"]


def banner(title: str) -> None:
    print(f"\n{RULE}\n {title}\n{RULE}")


def show_code(code: str, max_lines: int = 25) -> None:
    lines = code.rstrip("\n").splitlines()
    for i, line in enumerate(lines[:max_lines], 1):
        print(f"{i:>3}| {line}")
    if len(lines) > max_lines:
        print(f"   … ({len(lines) - max_lines} more lines)")


def show_diagnostics(diags: list[dict[str, Any]], code: str) -> None:
    errors = [d for d in diags if d.get("severity") == "error"] or diags
    for d in errors[:5]:
        rec = LeanErrorParser.parse_diagnostic(d, code)
        msg = d.get("message", "").strip().replace("\n", " ⏎ ")
        print(f"  {d.get('line', 0)}:{d.get('column', 0)}  [{rec.category.value}]  {msg[:110]}")
    primary = LeanErrorParser.primary(diags, code)
    if primary:
        print(f"\n  ⇒ root cause: {primary.category.value}  ⇒ route: {primary.route.value}")


def show_diff(before: str, after: str) -> None:
    diff = difflib.unified_diff(before.splitlines(), after.splitlines(), "broken", "repaired",
                                lineterm="", n=1)
    for line in list(diff)[:40]:
        print("  " + line)


def show_attempts(attempts: list[dict[str, Any]], start_code: str) -> None:
    prev = start_code
    for a in attempts:
        engine = a["engine"] + (f" ({a['rule']})" if a.get("rule") else "")
        tokens = a["input_tokens"] + a["output_tokens"] + a.get("thinking_tokens", 0)
        banner(f"Attempt {a['attempt']}: {engine}")
        print(f"  Lean: {a['status']}  ·  verify {a['verify_latency_ms']:.0f} ms"
              f"  ·  LLM {a.get('llm_latency_ms', 0):.0f} ms  ·  {tokens} tokens")
        verdict = "PASS" if a["audit_passed"] else "FAIL " + ", ".join(a["audit_reasons"])
        print(f"  Semantic audit: {verdict}")
        code = a.get("candidate_code")
        if code:
            show_diff(prev, code)
            prev = code


def summary(out: dict[str, Any]) -> None:
    banner("Result")
    print(f"  success={out['success']}  compiled={out['compiled']}  attempts={out['attempts_used']}"
          f"  stop={out['stop_reason']}  tokens={out['total_tokens']}  wall={out['wall_ms']:.0f} ms")


def replay(args: argparse.Namespace) -> None:
    with gzip.open(args.replay, "rt", encoding="utf-8") as f:
        entries = [json.loads(line) for line in f if line.strip()]
    entries = [e for e in entries if "attempts" in e]
    if args.error_id:
        entry = next((e for e in entries if e["error_id"] == args.error_id), None)
    else:
        want = args.pick == "success"
        entry = next((e for e in entries if e["success"] == want and e["attempts"]), None)
    if entry is None:
        sys.exit("No matching entry in the log")
    sample = None
    data = Path(args.data) if args.data else next((p for p in DATA_CANDIDATES if p.exists()), None)
    if data and data.exists():
        with open(data, encoding="utf-8") as f:
            sample = next((json.loads(x) for x in f if f'"{entry["error_id"]}"' in x), None)
    if sample is None:
        print(f"[!] {entry['error_id']} not found in {data or 'any data file'}: showing the attempts without the original code")
    banner(f"REPLAY {entry['error_id']}  ·  strategy={entry['strategy']}  ·  category={entry.get('category')}")
    start = strip_comments(sample["code"]) if sample else ""
    if sample:
        show_code(start)
        banner("Lean diagnostics (recorded)")
        show_diagnostics(sample["diagnostics"], sample["code"])
    show_attempts(entry["attempts"], start)
    summary(entry)


def live(args: argparse.Namespace) -> None:
    from src.cost_guard import CostGuard, GuardedClient, ResponseCache
    from src.lean_repl import LeanREPLVerifier
    from src.llm_client import make_client
    from src.llm_repair import LLMRepairEngine
    from src.repair_pipeline import RepairPipeline, RepairPolicy

    if args.file:
        code = Path(args.file).read_text(encoding="utf-8")
        sample = {"error_id": Path(args.file).stem, "code": code, "statement": theorem_statement(code)}
    else:
        data = Path(args.data) if args.data else next((p for p in DATA_CANDIDATES if p.exists()), None)
        if data is None or not data.exists():
            sys.exit("No error dataset found: pass --data or run scripts/download_data.sh")
        with open(data, encoding="utf-8") as f:
            sample = next((json.loads(x) for x in f if f'"{args.error_id}"' in x), None)
        if sample is None:
            sys.exit(f"{args.error_id} not found in {data}")

    banner(f"Broken input: {sample['error_id']}")
    show_code(strip_comments(sample["code"]))
    print("\n  Starting Lean REPL (imports Mathlib once) …", flush=True)
    verifier = LeanREPLVerifier(timeout_s=args.timeout)
    print(f"  ready in {verifier.import_latency_ms / 1000:.1f} s")

    res = verifier.verify(sample["code"])
    sample["diagnostics"] = res.diagnostics
    banner(f"Lean says: {res.status}  ({res.latency_ms:.0f} ms)")
    show_diagnostics(res.diagnostics, sample["code"])
    if res.proved:
        print("\n  Already compiles — nothing to repair.")
        verifier.close()
        return

    blind = diag = None
    if args.strategy in ("blind", "llm_only", "hybrid"):
        client = GuardedClient(make_client(args.provider, args.model),
                               CostGuard("demo", run_cap_usd=0.05), ResponseCache())
        blind = LLMRepairEngine(client, "blind")
        diag = LLMRepairEngine(client, "diagnostic")
    pipe = RepairPipeline(verifier, RepairPolicy(args.strategy, args.budget), blind, diag)
    out = pipe.run(sample).to_dict()
    show_attempts(out["attempts"], strip_comments(sample["code"]))
    summary(out)
    verifier.close()


def main() -> None:
    parser = argparse.ArgumentParser(description="Repair demo (live or replay)")
    src = parser.add_mutually_exclusive_group(required=True)
    src.add_argument("--file", help="Broken .lean file")
    src.add_argument("--error-id", help="Sample id from --data (live) or the log (replay)")
    src.add_argument("--pick", choices=["success", "failure"], help="Replay: first such sample")
    parser.add_argument("--data", default=None,
                        help="Error dataset; default: data/errors/errors_1k.jsonl, else data_sample/demo_samples.jsonl")
    parser.add_argument("--replay", help="Run log (.jsonl.gz) to replay instead of running")
    parser.add_argument("--strategy", default="hybrid")
    parser.add_argument("--budget", type=int, default=3)
    parser.add_argument("--provider", default="gemini")
    parser.add_argument("--model", default="gemini-3.5-flash-lite")
    parser.add_argument("--timeout", type=float, default=60.0)
    args = parser.parse_args()
    if args.replay:
        replay(args)
    else:
        if args.pick:
            sys.exit("--pick only works with --replay")
        live(args)


if __name__ == "__main__":
    main()
