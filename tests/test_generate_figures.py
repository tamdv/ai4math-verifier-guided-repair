"""Smoke test for figure generation using SYNTHETIC run records (not real results)."""

import gzip
import json
import random
import tempfile
import unittest
from pathlib import Path

from scripts.generate_figures import fig_quality, fig_scale, load_runs, style


def fake_runs(raw: Path) -> None:
    rng = random.Random(0)
    i = 0

    def write(params: dict, metrics: dict) -> None:
        nonlocal i
        i += 1
        rec = {"run_id": f"exp-{i}", "status": "SUCCESS", "parameters": params, "metrics": metrics}
        (raw / f"run_exp-fake-{i:03d}.json").write_text(json.dumps(rec))

    for data in ["errors_100.jsonl", "errors_1k.jsonl", "errors_10k.jsonl"]:
        for w in [1, 2, 4]:
            for r in [1, 2, 3]:
                tp = 8 * w ** 0.8 * rng.uniform(0.9, 1.1)
                write({"data": f"data/errors/{data}", "workers": w, "tag": "scale",
                       "split": "all", "strategy": "rule_only", "budget": 1, "model": "x",
                       "limit": 0},
                      {"throughput_excl_startup_per_s": tp, "service_p50_ms": 20 + rng.random(),
                       "service_p95_ms": 200 + 10 * rng.random(), "queue_wait_p95_ms": 1000.0,
                       "peak_rss_mb": 3500.0 * w})
    for strat, b, succ in [("none", 0, 0.0), ("rule_only", 3, 0.12), ("blind", 1, 0.18),
                           ("llm_only", 1, 0.31), ("hybrid", 3, 0.42)]:
        for r in [1, 2, 3]:
            write({"data": "data/errors/errors_1k.jsonl", "workers": 4, "tag": "rq",
                   "split": "holdout", "strategy": strat, "budget": b,
                   "model": "gemini-3.5-flash-lite", "limit": 0},
                  {"n_samples": 300, "repair_success_rate": succ + rng.uniform(-0.01, 0.01),
                   "compile_rate": min(1.0, succ * 1.3), "attempts_per_sample": b * 0.6,
                   "service_p95_ms": 900.0, "tokens_per_success": 1200,
                   "cost_usd": 0.0 if strat in ("none", "rule_only") else 0.1 * b,
                   "success_by_category": {"SYN_01": {"rate": succ}, "TAC_07": {"rate": succ / 2}}})


class TestGenerateFigures(unittest.TestCase):
    def test_all_figures_and_tables_written(self) -> None:
        style()
        with tempfile.TemporaryDirectory() as tmp:
            raw, out = Path(tmp) / "raw", Path(tmp) / "fig"
            raw.mkdir()
            out.mkdir()
            fake_runs(raw)
            runs = load_runs(raw)
            made = fig_scale(runs, out) + fig_quality(runs, out)
            names = {p.name for p in made}
            for stem in ["fig_scale_throughput", "fig_scale_speedup", "fig_scale_latency",
                         "fig_ablation", "fig_cost_quality", "fig_category_heatmap"]:
                self.assertIn(f"{stem}.pdf", names)
            table = (out / "table_ablation.md").read_text()
            self.assertIn("hybrid", table)
            self.assertEqual(len((out / "table_scale.csv").read_text().splitlines()), 10)

    def test_service_latency_backfilled_from_log(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            raw = Path(tmp)
            (raw / "logs").mkdir()
            rec = {"run_id": "exp-old", "status": "SUCCESS", "parameters": {},
                   "metrics": {"latency_p95_ms": 1.0}}
            (raw / "run_exp-old.json").write_text(json.dumps(rec))
            with gzip.open(raw / "logs" / "exp-old.jsonl.gz", "wt") as f:
                for ms in range(1, 101):
                    f.write(json.dumps({"wall_ms": float(ms)}) + "\n")
            m = load_runs(raw)[0]["metrics"]
            self.assertEqual((m["service_p50_ms"], m["service_p95_ms"]), (51.0, 96.0))
            self.assertTrue(m["service_backfilled_from_log"])

    def test_no_runs_no_figures(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            self.assertEqual(fig_scale([], Path(tmp)) + fig_quality([], Path(tmp)), [])


if __name__ == "__main__":
    unittest.main()
