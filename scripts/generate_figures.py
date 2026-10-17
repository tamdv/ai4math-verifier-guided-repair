"""Generates report figures and tables strictly from immutable run records.

Reads every `results/raw/run_exp-*.json`, groups repeats of the same configuration,
and reports the **median with min-max range** across repeats (assignment rule).

Figures (PDF for LaTeX + PNG preview) in results/figures/:
  fig_scale_throughput   steady-state throughput vs data tier, one line per worker count
  fig_scale_speedup      speedup vs workers per tier, with the ideal linear line
  fig_scale_latency      service latency P50 | P95 vs data tier (small multiples)
  fig_ablation           repair success vs compile rate per strategy / budget
  fig_cost_quality       cost per 1K samples vs repair success, Pareto frontier
  fig_category_heatmap   success rate by error category x strategy
Tables: table_scale.{csv,md}, table_ablation.{csv,md}

Usage:
    python3 scripts/generate_figures.py --input results/raw/ --output results/figures/
"""

import argparse
import collections
import csv
import gzip
import json
import statistics
from pathlib import Path
from typing import Any

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402

# Reference categorical palette, light mode, slots 1-3 (validated all-pairs for <= 3
# series); text/axes use ink tokens, never series colors.
SERIES = ["#2a78d6", "#eb6834", "#1baf7a"]
MARKERS = ["o", "s", "^"]
LINESTYLES = ["-", "--", ":"]
INK = "#0b0b0b"
INK_2 = "#52514e"
GRID = "#e4e3df"
SURFACE = "#ffffff"
SEQ_BLUE = ["#cde2fb", "#9ec5f4", "#6da7ec", "#3987e5", "#256abf", "#184f95", "#0d366b"]
TIER_ORDER = {"errors_100.jsonl": 100, "errors_1k.jsonl": 1000, "errors_10k.jsonl": 10000}
STRATEGY_LABEL = {
    "none": "No repair",
    "rule_only": "Rule-only",
    "blind": "Blind retry\n(baseline)",
    "llm_only": "LLM +\ndiagnostics",
    "hybrid": "Hybrid\nrouter",
}


def style() -> None:
    plt.rcParams.update({
        "figure.facecolor": SURFACE, "axes.facecolor": SURFACE, "savefig.facecolor": SURFACE,
        "font.size": 9, "axes.titlesize": 10, "axes.labelsize": 9,
        "axes.edgecolor": INK_2, "axes.labelcolor": INK, "xtick.color": INK_2,
        "ytick.color": INK_2, "text.color": INK, "axes.spines.top": False,
        "axes.spines.right": False, "axes.grid": True, "grid.color": GRID,
        "grid.linewidth": 0.6, "axes.axisbelow": True, "lines.linewidth": 2,
        "lines.markersize": 6, "legend.frameon": False, "pdf.fonttype": 42,
    })


def backfill_service_latency(rec: dict[str, Any], raw_dir: Path) -> None:
    """Recomputes service P50/P95 from the per-sample log for records written before
    run_experiment.py reported them (the log keeps each sample's `wall_ms`)."""
    m = rec["metrics"]
    if "service_p95_ms" in m:
        return
    log = raw_dir / "logs" / f"{rec['run_id']}.jsonl.gz"
    if not log.exists():
        return
    with gzip.open(log, "rt", encoding="utf-8") as f:
        walls = sorted(e["wall_ms"] for e in map(json.loads, f) if "wall_ms" in e)
    if walls:
        m["service_p50_ms"] = walls[min(int(len(walls) * 0.5), len(walls) - 1)]
        m["service_p95_ms"] = walls[min(int(len(walls) * 0.95), len(walls) - 1)]
        m["service_backfilled_from_log"] = True


def load_runs(raw_dir: Path) -> list[dict[str, Any]]:
    runs = []
    for path in sorted(raw_dir.glob("run_exp-*.json")):
        rec = json.loads(path.read_text(encoding="utf-8"))
        if rec.get("status") in ("SUCCESS", "PARTIAL"):
            backfill_service_latency(rec, raw_dir)
            runs.append(rec)
    return runs


def agg(values: list[float]) -> tuple[float, float, float]:
    """(median, min, max) of repeats."""
    return statistics.median(values), min(values), max(values)


def save(fig: plt.Figure, out: Path, name: str) -> list[Path]:
    paths = [out / f"{name}.pdf", out / f"{name}.png"]
    for p in paths:
        fig.savefig(p, dpi=300, bbox_inches="tight")
    plt.close(fig)
    return paths


def write_table(rows: list[dict[str, Any]], out: Path, name: str) -> None:
    if not rows:
        return
    with open(out / f"{name}.csv", "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0]))
        w.writeheader()
        w.writerows(rows)
    header = "| " + " | ".join(rows[0]) + " |\n|" + "---|" * len(rows[0]) + "\n"
    body = "".join("| " + " | ".join(str(v) for v in r.values()) + " |\n" for r in rows)
    (out / f"{name}.md").write_text(header + body, encoding="utf-8")


# ---------------------------------------------------------------- scalability
def scale_groups(runs: list[dict[str, Any]]) -> dict[tuple[int, int], list[dict[str, Any]]]:
    groups: dict[tuple[int, int], list[dict[str, Any]]] = collections.defaultdict(list)
    for r in runs:
        p = r["parameters"]
        tier = TIER_ORDER.get(Path(p["data"]).name)
        if p.get("tag") == "scale" and tier:
            groups[(tier, p["workers"])].append(r["metrics"])
    return groups


def fig_scale(runs: list[dict[str, Any]], out: Path) -> list[Path]:
    groups = scale_groups(runs)
    if not groups:
        return []
    tiers = sorted({t for t, _ in groups})
    workers = sorted({w for _, w in groups})
    made: list[Path] = []

    def series(metric: str, w: int) -> tuple[list[int], list[float], list[list[float]]]:
        xs, med, err = [], [], [[], []]
        for t in tiers:
            vals = [m[metric] for m in groups.get((t, w), []) if m.get(metric) is not None]
            if vals:
                m, lo, hi = agg(vals)
                xs.append(t)
                med.append(m)
                err[0].append(m - lo)
                err[1].append(hi - m)
        return xs, med, err

    # Throughput vs tier
    fig, ax = plt.subplots(figsize=(4.2, 3.0))
    for i, w in enumerate(workers):
        xs, med, err = series("throughput_excl_startup_per_s", w)
        ax.errorbar(xs, med, yerr=err, color=SERIES[i], marker=MARKERS[i], ls=LINESTYLES[i],
                    capsize=3, label=f"{w} worker{'s' if w > 1 else ''}")
    ax.set_xscale("log")
    ax.set_xticks(tiers, [f"{t:,}" for t in tiers])
    ax.set_xlabel("Error candidates (data tier)")
    ax.set_ylabel("Throughput (samples/s)")
    ax.set_title("Steady-state throughput (median, min–max of 3 runs)", loc="left")
    ax.legend()
    made += save(fig, out, "fig_scale_throughput")

    # Speedup vs workers
    fig, ax = plt.subplots(figsize=(4.2, 3.0))
    ax.plot(workers, workers, color=INK_2, ls=(0, (2, 3)), lw=1, label="Ideal (linear)")
    for i, t in enumerate(tiers):
        base = [m["throughput_excl_startup_per_s"] for m in groups.get((t, workers[0]), [])]
        if not base:
            continue
        b = statistics.median(base)
        ys = [statistics.median([m["throughput_excl_startup_per_s"] for m in groups[(t, w)]]) / b
              for w in workers if groups.get((t, w))]
        ax.plot(workers[: len(ys)], ys, color=SERIES[i], marker=MARKERS[i], ls=LINESTYLES[i],
                label=f"{t:,} candidates")
    ax.set_xticks(workers)
    ax.set_xlabel("Lean REPL workers")
    ax.set_ylabel(f"Speedup vs {workers[0]} worker")
    ax.set_title("Worker scaling", loc="left")
    ax.legend()
    made += save(fig, out, "fig_scale_speedup")

    # Service latency P50 | P95 (small multiples, shared y)
    # P50 and P95 differ by an order of magnitude: independent y-scales, both from 0.
    fig, axes = plt.subplots(1, 2, figsize=(6.4, 2.8))
    for ax, metric, title in zip(axes, ["service_p50_ms", "service_p95_ms"], ["P50", "P95"]):
        for i, w in enumerate(workers):
            xs, med, err = series(metric, w)
            ax.errorbar(xs, med, yerr=err, color=SERIES[i], marker=MARKERS[i],
                        ls=LINESTYLES[i], capsize=3, label=f"{w} worker{'s' if w > 1 else ''}")
        ax.set_xscale("log")
        ax.set_xticks(tiers, [f"{t:,}" for t in tiers])
        ax.set_title(f"Service latency {title}", loc="left")
        ax.set_xlabel("Error candidates")
        ax.set_ylim(bottom=0)
    axes[0].set_ylabel("ms per sample")
    axes[1].legend()
    made += save(fig, out, "fig_scale_latency")

    rows = []
    for (t, w), ms in sorted(groups.items()):
        def cell(key: str) -> str:
            vals = [m[key] for m in ms if m.get(key) is not None]
            if not vals:
                return "-"
            md, lo, hi = agg(vals)
            return f"{md:.1f} [{lo:.1f}-{hi:.1f}]"
        rows.append({"tier": t, "workers": w, "runs": len(ms),
                     "throughput/s": cell("throughput_excl_startup_per_s"),
                     "service P50 ms": cell("service_p50_ms"),
                     "service P95 ms": cell("service_p95_ms"),
                     "queue wait P95 ms": cell("queue_wait_p95_ms"),
                     "peak RSS MB": cell("peak_rss_mb")})
    write_table(rows, out, "table_scale")
    return made


# ---------------------------------------------------------------- quality / cost
def quality_groups(runs: list[dict[str, Any]]) -> dict[tuple[str, int, str], list[dict[str, Any]]]:
    """Hold-out runs of the 1K tier, keyed by (strategy, budget, model)."""
    groups: dict[tuple[str, int, str], list[dict[str, Any]]] = collections.defaultdict(list)
    for r in runs:
        p = r["parameters"]
        if (p.get("split") != "holdout" or p.get("limit")
                or Path(p.get("data", "")).name != "errors_1k.jsonl"
                or p.get("tag") in ("scale", "scale-llm", "pilot")):
            continue
        model = p["model"] if p["strategy"] in ("blind", "llm_only", "hybrid") else "-"
        groups[(p["strategy"], p["budget"], model)].append(r["metrics"])
    return groups


def label(strategy: str, budget: int, model: str) -> str:
    base = STRATEGY_LABEL.get(strategy, strategy)
    suffix = f" k={budget}" if strategy not in ("none",) else ""
    if model not in ("-", "gemini-3.5-flash-lite"):
        suffix += f"\n[{model}]"
    return base + suffix


def fig_quality(runs: list[dict[str, Any]], out: Path) -> list[Path]:
    groups = quality_groups(runs)
    if not groups:
        return []
    order = ["none", "rule_only", "blind", "llm_only", "hybrid"]
    keys = sorted(groups, key=lambda k: (order.index(k[0]) if k[0] in order else 9, k[1], k[2]))
    made: list[Path] = []

    # Ablation: compile rate vs audited repair success
    fig, ax = plt.subplots(figsize=(max(4.5, 1.0 * len(keys) + 1.5), 3.2))
    width = 0.38
    for j, (metric, name) in enumerate([("compile_rate", "Compiles"),
                                        ("repair_success_rate", "Repair success (audited)")]):
        xs, med, err = [], [], [[], []]
        for i, k in enumerate(keys):
            m, lo, hi = agg([g[metric] * 100 for g in groups[k]])
            xs.append(i + (j - 0.5) * (width + 0.02))
            med.append(m)
            err[0].append(m - lo)
            err[1].append(hi - m)
        bars = ax.bar(xs, med, width, color=SERIES[j], label=name, yerr=err, capsize=2,
                      error_kw={"elinewidth": 1, "ecolor": INK_2})
        if j == 1:
            for b, v in zip(bars, med):
                ax.annotate(f"{v:.0f}%", (b.get_x() + b.get_width() / 2, b.get_height()),
                            xytext=(0, 3), textcoords="offset points", ha="center",
                            fontsize=7, color=INK)
    ax.set_xticks(range(len(keys)), [label(*k) for k in keys], fontsize=7)
    ax.set_ylabel("% of hold-out samples")
    ax.set_ylim(0, 100)
    ax.grid(axis="x", visible=False)
    ax.set_title("Ablation on 1K hold-out (median, min–max of repeats)", loc="left")
    ax.legend(loc="upper left")
    made += save(fig, out, "fig_ablation")

    # Cost vs quality with Pareto frontier
    pts = []
    for k in keys:
        n = statistics.median(g["n_samples"] for g in groups[k])
        cost = statistics.median((g.get("cost_usd") or 0.0) for g in groups[k])
        succ = statistics.median(g["repair_success_rate"] for g in groups[k]) * 100
        pts.append((cost / n * 1000 if n else 0.0, succ, k))
    fig, ax = plt.subplots(figsize=(4.6, 3.2))
    frontier, best = [], -1.0
    for c, s, k in sorted(pts, key=lambda p: (p[0], -p[1])):
        if s > best:
            frontier.append((c, s))
            best = s
    ax.plot(*zip(*frontier), color=INK_2, lw=1, ls=(0, (2, 3)), label="Pareto frontier")
    ax.scatter([p[0] for p in pts], [p[1] for p in pts], s=40, color=SERIES[0],
               edgecolor=SURFACE, linewidth=2, zorder=3)
    xr = (max(p[0] for p in pts) - min(p[0] for p in pts)) or 1.0
    yr = (max(p[1] for p in pts) - min(p[1] for p in pts)) or 1.0
    placed: list[tuple[float, float]] = []
    for c, s, k in sorted(pts, key=lambda p: -p[1]):
        # put the label above the point if another labelled point sits just below it
        crowded = any(abs(c - pc) / xr < 0.25 and 0 <= (s - ps) / yr < 0.12 for pc, ps in placed)
        crowded = crowded or any(abs(c - pc) / xr < 0.25 and 0 < (s - ps) / yr < 0.12
                                 for pc, ps, _ in pts if (pc, ps) != (c, s))
        placed.append((c, s))
        ax.annotate(label(*k).replace("\n", " "), (c, s), xytext=(6, 5 if crowded else -10),
                    textcoords="offset points", fontsize=7, color=INK_2, zorder=4,
                    bbox={"boxstyle": "square,pad=0.15", "fc": SURFACE, "ec": "none"})
    ax.set_ylim(bottom=-6)  # room for labels of points at 0 %
    ax.set_xlabel("LLM cost per 1,000 samples (USD)")
    ax.set_ylabel("Repair success (%)")
    ax.set_title("Cost–quality trade-off", loc="left")
    ax.legend(loc="lower right")
    made += save(fig, out, "fig_cost_quality")

    # Success by category heatmap (sequential blue, values annotated)
    cats = sorted({c for k in keys for g in groups[k] for c in g.get("success_by_category", {})})
    if cats:
        grid = []
        for c in cats:
            row = []
            for k in keys:
                rates = [g["success_by_category"][c]["rate"] * 100 for g in groups[k]
                         if c in g.get("success_by_category", {})]
                row.append(statistics.median(rates) if rates else float("nan"))
            grid.append(row)
        cmap = matplotlib.colors.LinearSegmentedColormap.from_list("seq_blue", SEQ_BLUE)
        fig, ax = plt.subplots(figsize=(max(4.5, 0.9 * len(keys) + 1.5), 0.42 * len(cats) + 1.2))
        im = ax.imshow(grid, cmap=cmap, vmin=0, vmax=100, aspect="auto")
        for i, row in enumerate(grid):
            for j, v in enumerate(row):
                if v == v:  # not NaN
                    ax.text(j, i, f"{v:.0f}", ha="center", va="center", fontsize=7,
                            color=SURFACE if v > 55 else INK)
        ax.set_xticks(range(len(keys)), [label(*k) for k in keys], fontsize=7)
        ax.set_yticks(range(len(cats)), cats)
        ax.grid(False)
        ax.set_title("Repair success (%) by error category", loc="left")
        fig.colorbar(im, ax=ax, fraction=0.03, pad=0.02)
        made += save(fig, out, "fig_category_heatmap")

    rows = []
    for k in keys:
        def cell(key: str, scale: float = 1.0, fmt: str = "{:.1f}") -> str:
            vals = [g[key] * scale for g in groups[k] if g.get(key) is not None]
            if not vals:
                return "-"
            md, lo, hi = agg(vals)
            return fmt.format(md) + (f" [{fmt.format(lo)}-{fmt.format(hi)}]" if len(vals) > 1 else "")
        rows.append({"strategy": k[0], "budget": k[1], "model": k[2], "runs": len(groups[k]),
                     "success %": cell("repair_success_rate", 100),
                     "compile %": cell("compile_rate", 100),
                     "attempts/sample": cell("attempts_per_sample", fmt="{:.2f}"),
                     "service P95 ms": cell("service_p95_ms"),
                     "tokens/success": cell("tokens_per_success", fmt="{:.0f}"),
                     "cost USD": cell("cost_usd", fmt="{:.4f}")})
    write_table(rows, out, "table_ablation")
    return made


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate report figures from raw results")
    parser.add_argument("--input", default="results/raw/")
    parser.add_argument("--output", default="results/figures/")
    args = parser.parse_args()

    style()
    out = Path(args.output)
    out.mkdir(parents=True, exist_ok=True)
    runs = load_runs(Path(args.input))
    made = fig_scale(runs, out) + fig_quality(runs, out)
    print(f"[OK] {len(runs)} run records -> {len(made)} figure files in {out}")
    for p in made:
        if p.suffix == ".pdf":
            print("   ", p.name)


if __name__ == "__main__":
    main()
