"""Presentation-ready figure generators.

Each `plot_*` function takes one or more dataframes and returns a
matplotlib Figure. Figures are saved as PNGs in `output/figures/` with
descriptive filenames that map directly to README sections and slide
talking points.
"""

from __future__ import annotations

from pathlib import Path

import matplotlib.pyplot as plt
import pandas as pd

CLASS_COLORS = {
    "high": "#2ca02c",
    "middle": "#ff9800",
    "low": "#d62728",
}

OUTPUT_FIGS = Path(__file__).resolve().parent.parent / "output" / "figures"


def _ensure_dir() -> None:
    OUTPUT_FIGS.mkdir(parents=True, exist_ok=True)


def _save(fig: plt.Figure, name: str) -> Path:
    _ensure_dir()
    path = OUTPUT_FIGS / name
    fig.tight_layout()
    fig.savefig(path, dpi=160, bbox_inches="tight")
    plt.close(fig)
    return path


def plot_class_migration(model_df: pd.DataFrame, scenario: str, out_name: str | None = None) -> Path:
    """Stacked-area chart of effective class counts over time."""
    fig, ax = plt.subplots(figsize=(8, 4))
    months = model_df["step"]
    ax.stackplot(
        months,
        model_df["count_high"], model_df["count_middle"], model_df["count_low"],
        labels=["High", "Middle", "Low"],
        colors=[CLASS_COLORS["high"], CLASS_COLORS["middle"], CLASS_COLORS["low"]],
        alpha=0.85,
    )
    ax.set_title(f"Effective class population over time ({scenario})")
    ax.set_xlabel("Month")
    ax.set_ylabel("Households")
    ax.legend(loc="upper left", framealpha=0.9)
    ax.grid(alpha=0.3)
    return _save(fig, out_name or f"class_migration_{scenario}.png")


def plot_col_by_scenario(summary_df: pd.DataFrame, out_name: str = "col_by_scenario.png") -> Path:
    """Final-month cost-of-living index across scenarios."""
    fig, ax = plt.subplots(figsize=(9, 4.5))
    sorted_df = summary_df.sort_values("oil_shock_pct").reset_index(drop=True)
    colors = ["#1f77b4" if g == 0 else "#9467bd" if g == 1 else "#2ca02c"
              for g in sorted_df["gov_response_level"]]
    ax.bar(sorted_df["scenario"], sorted_df["col_index"], color=colors)
    ax.axhline(100, color="#888", linestyle="--", label="baseline = 100")
    ax.set_title("Cost-of-living index by scenario (final month)")
    ax.set_ylabel("COL index (100 = baseline)")
    ax.set_xticks(range(len(sorted_df)))
    ax.set_xticklabels(sorted_df["scenario"], rotation=30, ha="right")
    ax.legend()
    ax.grid(alpha=0.3, axis="y")
    return _save(fig, out_name)


def plot_buying_power_by_class(summary_df: pd.DataFrame,
                                out_name: str = "buying_power_by_class.png") -> Path:
    """Buying power by income class across scenarios."""
    fig, ax = plt.subplots(figsize=(10, 5))
    x = range(len(summary_df))
    w = 0.27
    ax.bar([i - w for i in x], summary_df["buying_power_low"], width=w,
           label="Low income", color=CLASS_COLORS["low"])
    ax.bar(list(x), summary_df["buying_power_middle"], width=w,
           label="Middle income", color=CLASS_COLORS["middle"])
    ax.bar([i + w for i in x], summary_df["buying_power_high"], width=w,
           label="High income", color=CLASS_COLORS["high"])
    ax.set_title("Mean buying power by income class (final month)")
    ax.set_ylabel("PHP / month")
    ax.set_xticks(list(x))
    ax.set_xticklabels(summary_df["scenario"], rotation=30, ha="right")
    ax.legend()
    ax.grid(alpha=0.3, axis="y")
    return _save(fig, out_name)


def plot_rural_urban_gap(summary_df: pd.DataFrame, out_name: str = "rural_urban_gap.png") -> Path:
    """Rural vs urban buying power side-by-side."""
    fig, ax = plt.subplots(figsize=(9, 4.5))
    x = range(len(summary_df))
    w = 0.4
    ax.bar([i - w / 2 for i in x], summary_df["buying_power_rural"], width=w,
           label="Rural", color="#8c5e2a")
    ax.bar([i + w / 2 for i in x], summary_df["buying_power_urban"], width=w,
           label="Urban", color="#5b9bd5")
    ax.set_title("Rural vs urban mean buying power (final month)")
    ax.set_ylabel("PHP / month")
    ax.set_xticks(list(x))
    ax.set_xticklabels(summary_df["scenario"], rotation=30, ha="right")
    ax.legend()
    ax.grid(alpha=0.3, axis="y")
    return _save(fig, out_name)


def plot_policy_effect(summary_df: pd.DataFrame,
                        shock_pct: float = 40,
                        out_name: str = "policy_effect.png") -> Path:
    """Effect of government response at a fixed shock level."""
    sub = summary_df[summary_df["oil_shock_pct"] == shock_pct].sort_values("gov_response_level")
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(11, 4.5))

    ax1.bar(sub["gov_response_level"].astype(str), sub["count_low"],
            color=CLASS_COLORS["low"])
    ax1.set_title(f"Households dropping to LOW class at +{shock_pct}% shock")
    ax1.set_xlabel("Government response level")
    ax1.set_ylabel("Low-class households")
    ax1.grid(alpha=0.3, axis="y")

    ax2.bar(sub["gov_response_level"].astype(str), sub["mean_buying_power"],
            color="#2ca02c")
    ax2.set_title(f"Mean buying power at +{shock_pct}% shock")
    ax2.set_xlabel("Government response level")
    ax2.set_ylabel("PHP / month")
    ax2.grid(alpha=0.3, axis="y")

    return _save(fig, out_name)


def plot_shock_response_curve(summary_df: pd.DataFrame,
                               out_name: str = "shock_response_curve.png") -> Path:
    """COL index and buying power as a function of shock size (gov=0 only)."""
    sub = summary_df[summary_df["gov_response_level"] == 0].sort_values("oil_shock_pct")
    fig, ax1 = plt.subplots(figsize=(9, 4.5))
    color1 = "#d62728"
    ax1.plot(sub["oil_shock_pct"], sub["col_index"], marker="o",
             color=color1, linewidth=2, label="COL index")
    ax1.set_xlabel("Global oil shock (%)")
    ax1.set_ylabel("Cost-of-living index", color=color1)
    ax1.tick_params(axis="y", labelcolor=color1)
    ax1.axhline(100, color="#888", linestyle="--", alpha=0.6)
    ax1.grid(alpha=0.3)

    ax2 = ax1.twinx()
    color2 = "#1f77b4"
    ax2.plot(sub["oil_shock_pct"], sub["mean_buying_power"], marker="s",
             color=color2, linewidth=2, label="Mean buying power")
    ax2.set_ylabel("Mean buying power (PHP)", color=color2)
    ax2.tick_params(axis="y", labelcolor=color2)

    fig.suptitle("Dose-response curve: how shock size drives household stress (no policy)")
    return _save(fig, out_name)
