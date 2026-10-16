"""Pre-run cost estimate (no API calls, $0): builds the real prompts for a dataset and
multiplies by the experiment plan in configs/exp_plan.yaml.

Token counts are estimated as chars / 3 (conservative for code + Unicode math);
the LLM returns the whole file, so output tokens ~= code tokens. Calibrate both
with a small paid pilot before large runs (the pilot's run record has real counts).

Usage:
    python3 scripts/estimate_cost.py --data data/errors/errors_10k.jsonl
"""

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import yaml  # noqa: E402

from src.cost_guard import CHARS_PER_TOKEN, load_prices, price_usd  # noqa: E402
from src.llm_client import MockClient  # noqa: E402
from src.llm_repair import LLMRepairEngine, strip_comments  # noqa: E402

PLAN_PATH = Path(__file__).resolve().parent.parent / "configs" / "exp_plan.yaml"


def per_call_tokens(samples: list[dict], mode: str, strip: bool) -> tuple[float, float]:
    """Mean (input, output) tokens per LLM call for `mode` over `samples`."""
    engine = LLMRepairEngine(MockClient(), mode=mode)
    system = engine.prompts["system"]
    ins, outs = [], []
    for s in samples:
        code = strip_comments(s["code"]) if strip else s["code"]
        prompt = engine.build_prompt(code, s.get("diagnostics", []))
        ins.append((len(system) + len(prompt)) / CHARS_PER_TOKEN)
        outs.append(len(code) / CHARS_PER_TOKEN + 20)
    return sum(ins) / len(ins), sum(outs) / len(outs)


def main() -> None:
    parser = argparse.ArgumentParser(description="Estimate LLM cost of the experiment plan")
    parser.add_argument("--data", default="data/errors/errors_1k.jsonl")
    parser.add_argument("--plan", default=str(PLAN_PATH))
    parser.add_argument("--vnd-per-usd", type=float, default=26100.0)
    args = parser.parse_args()

    with open(args.data, encoding="utf-8") as f:
        samples = [json.loads(line) for line in f if line.strip()][:500]
    plan = yaml.safe_load(Path(args.plan).read_text())
    prices = load_prices()
    a = plan["assumptions"]
    strip = a.get("strip_comments", False)
    tokens = {m: per_call_tokens(samples, m, strip) for m in ("blind", "diagnostic")}

    print(f"Mean tokens/call  blind: in {tokens['blind'][0]:.0f} out {tokens['blind'][1]:.0f} | "
          f"diagnostic: in {tokens['diagnostic'][0]:.0f} out {tokens['diagnostic'][1]:.0f}")
    print(f"{'experiment':38} {'calls':>8} {'USD':>8} {'VND':>12}")
    total_usd = 0.0
    for exp in plan["experiments"]:
        mode = "blind" if exp["strategy"] == "blind" else "diagnostic"
        attempts = a["mean_attempts"][str(exp["budget"])]
        llm_share = a["hybrid_llm_share"] if exp["strategy"] == "hybrid" else 1.0
        repeats = 1 if a.get("cache_repeats") else exp.get("repeats", 1)
        calls = exp["samples"] * attempts * llm_share * repeats
        tin, tout = tokens[mode]
        usd = calls * price_usd(prices, exp["model"], int(tin), int(tout))
        total_usd += usd
        print(f"{exp['name']:38} {calls:8.0f} {usd:8.2f} {usd * args.vnd_per_usd:12,.0f}")
    margin = total_usd * a["safety_margin"]
    print(f"{'TOTAL (x' + str(a['safety_margin']) + ' safety margin)':38} {'':8} "
          f"{margin:8.2f} {margin * args.vnd_per_usd:12,.0f}")


if __name__ == "__main__":
    main()
