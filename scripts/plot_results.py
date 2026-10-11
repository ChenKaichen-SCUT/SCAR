"""Plot measured results only; use after analyze.py. No simulated data."""
import argparse
from collections import defaultdict
import json
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np


METHODS = ["ShortTermMemoryAgent", "VanillaRAGAgent", "LongContextAgent", "SimpleFailureRecovery", "SCARAgent"]
LABELS = ["STM", "RAG", "Long context", "Simple recovery", "SCAR"]
COLORS = ["#888888", "#0072B2", "#009E73", "#E69F00", "#D55E00"]


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--results", default="results")
    parser.add_argument("--output", default="reports/figures")
    args = parser.parse_args()
    rows = json.loads((Path(args.results) / "all_summaries.json").read_text())
    out = Path(args.output)
    out.mkdir(parents=True, exist_ok=True)
    plt.rcParams.update({"font.size": 9, "axes.spines.top": False, "axes.spines.right": False,
                         "svg.fonttype": "none", "savefig.dpi": 300})
    fig, (ax, bx) = plt.subplots(1, 2, figsize=(11.2, 4.0), gridspec_kw={"width_ratios": [1.35, 1]})
    games = ["remnant", "mark", "metropolis"]
    width = .14
    for j, (method, label, color) in enumerate(zip(METHODS, LABELS, COLORS)):
        for i, game in enumerate(games):
            values = [r["main_quest_reward"] for r in rows if r.get("stage") == "long" and
                      r["algorithm"] == method and r["game"] == game and r["status"] == "completed"]
            if not values:
                continue
            x = i + (j - 2) * width
            ax.bar(x, np.mean(values), width=width * .90, color=color, label=label if i == 0 else None, alpha=.8)
            ax.scatter(x + np.linspace(-.025, .025, len(values)), values, s=16, facecolors="white", edgecolors="black", linewidths=.5, zorder=5)
    ax.set_xticks(range(3), games)
    ax.set_ylabel("Main-quest reward (engine units)")
    ax.set_title("200-step games: means and individual seeds", loc="left", fontsize=10)
    max_reward = max((r["main_quest_reward"] for r in rows if r.get("stage") == "long"), default=1)
    ax.set_ylim(0, max_reward * 1.23)
    ax.legend(frameon=False, fontsize=8, ncol=3, loc="upper left")
    selected = [m for m in METHODS if m != "LongContextAgent"]
    for i, method in enumerate(selected):
        values = [r for r in rows if r.get("diagnostic") and r.get("protocol_cohort") == "formal_hash0"
                  and r["algorithm"] == method and r["status"] == "completed"]
        if not values:
            continue
        groups = defaultdict(list)
        for row in values:
            groups[row["family"]].append(float(row["recovery_at_20"]))
        family_values = np.asarray([np.mean(v) for v in groups.values()])
        mean = family_values.mean()
        rng = np.random.default_rng(314159)
        samples = rng.choice(family_values, size=(10000, len(family_values)), replace=True).mean(axis=1)
        low, high = np.quantile(samples, [.025, .975])
        j = METHODS.index(method)
        bx.bar(i, mean * 100, color=COLORS[j], alpha=.8, width=.65)
        bx.errorbar(i, mean * 100, yerr=np.array([[mean - low], [high - mean]]) * 100, fmt="none", color="black", capsize=4)
        bx.text(i, high * 100 + 2, f"{mean:.1%}", ha="center", fontsize=8)
    bx.set_xticks(range(len(selected)), [LABELS[METHODS.index(m)].replace(" ", "\n") for m in selected])
    bx.set_ylim(0, 115)
    bx.set_ylabel("Recovery@20 (%)")
    bx.set_title("Frozen recovery cases; 95% family bootstrap CI", loc="left", fontsize=10)
    for axis in (ax, bx):
        axis.grid(axis="y", alpha=.15)
        axis.set_axisbelow(True)
    fig.tight_layout()
    fig.savefig(out / "main_results.svg", bbox_inches="tight")
    fig.savefig(out / "main_results.png", bbox_inches="tight")
    plt.close(fig)
    ratios_path = Path(args.results) / "fbr_ratio_uncertainty.json"
    if ratios_path.exists():
        ratios = json.loads(ratios_path.read_text())
        fig, ax = plt.subplots(figsize=(6.7, 3.5))
        stages = ["diagnostic", "long", "cost"]
        for j, method in enumerate(["SimpleFailureRecovery", "SCARAgent"]):
            for i, stage in enumerate(stages):
                row = next(v for v in ratios if v["stage"] == stage and v["algorithm"] == method)
                x = i + (j - .5) * .30
                value = row["pooled_fbr"] * 100
                ax.bar(x, value, width=.27, color=COLORS[METHODS.index(method)], alpha=.8,
                       label=LABELS[METHODS.index(method)] if i == 0 else None)
                ax.errorbar(x, value, yerr=[[value-row["ci95_low"]*100], [row["ci95_high"]*100-value]],
                            fmt="none", color="black", capsize=3)
                ax.text(x, 3, f"{row['false_blocks']}/{row['interceptions']}", ha="center", fontsize=8)
        ax.set_xticks(range(3), ["Recovery cases", "200-step games", "$0.15 cap games"])
        ax.set_ylabel("Valid candidates among overridden actions (%)")
        ax.set_ylim(0, 103)
        ax.set_title("False blocking remains substantial", loc="left", fontsize=10)
        ax.legend(frameon=False, loc="upper right", ncol=2, fontsize=8)
        ax.grid(axis="y", alpha=.15)
        ax.set_axisbelow(True)
        fig.tight_layout()
        fig.savefig(out / "false_blocking.svg", bbox_inches="tight")
        fig.savefig(out / "false_blocking.png", bbox_inches="tight")
        plt.close(fig)
    (out / "plot_environment.json").write_text(json.dumps({"matplotlib": matplotlib.__version__, "numpy": np.__version__}, indent=2))


if __name__ == "__main__":
    main()
