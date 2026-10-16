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


def calibration(raw_dir: Path) -> dict[str, float]:
    """Mean real USD per LLM call by prompt mode, from `--tag pilot` run records."""
    cost: dict[str, float] = {}
    calls: dict[str, int] = {}
    for path in raw_dir.glob("run_exp-*.json"):
        rec = json.loads(path.read_text(encoding="utf-8"))
        p, m = rec.get("parameters", {}), rec.get("metrics", {})
        if p.get("tag") != "pilot" or not m.get("llm_calls"):
            continue
        mode = "blind" if p.get("strategy") == "blind" else "diagnostic"
        cost[mode] = cost.get(mode, 0.0) + m.get("real_spend_usd", m.get("cost_usd") or 0.0)
        calls[mode] = calls.get(mode, 0) + m["llm_calls"]
    return {k: cost[k] / calls[k] for k in cost if calls[k]}


def main() -> None:
    parser = argparse.ArgumentParser(description="Estimate LLM cost of the experiment plan")
    parser.add_argument("--data", default="data/errors/errors_1k.jsonl")
    parser.add_argument("--plan", default=str(PLAN_PATH))
    parser.add_argument("--vnd-per-usd", type=float, default=26100.0)
    parser.add_argument("--calibrate", default="results/raw",
                        help="Use real cost/call from pilot run records found here")
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
    real = calibration(Path(args.calibrate))
    if real:
        print("Calibrated from pilot (USD/call): " +
              ", ".join(f"{k} {v:.5f}" for k, v in sorted(real.items())))
    print(f"{'experiment':38} {'calls':>8} {'USD':>8} {'VND':>12}")
    total_usd = 0.0
    for exp in plan["experiments"]:
        mode = "blind" if exp["strategy"] == "blind" else "diagnostic"
        attempts = a["mean_attempts"][str(exp["budget"])]
        llm_share = a["hybrid_llm_share"] if exp["strategy"] == "hybrid" else 1.0
        repeats = 1 if a.get("cache_repeats") else exp.get("repeats", 1)
        calls = exp["samples"] * attempts * llm_share * repeats
        tin, tout = tokens[mode]
        per_call = price_usd(prices, exp["model"], int(tin), int(tout))
        pilot_model = "gemini-3.5-flash-lite"
        if real.get(mode):
            # scale the measured per-call cost of the pilot model to this model's prices
            ratio = per_call / price_usd(prices, pilot_model, int(tin), int(tout))
            per_call = real[mode] * ratio
        usd = calls * per_call
        total_usd += usd
        print(f"{exp['name']:38} {calls:8.0f} {usd:8.2f} {usd * args.vnd_per_usd:12,.0f}")
    margin = total_usd * a["safety_margin"]
    print(f"{'TOTAL (x' + str(a['safety_margin']) + ' safety margin)':38} {'':8} "
          f"{margin:8.2f} {margin * args.vnd_per_usd:12,.0f}")


if __name__ == "__main__":
    main()
