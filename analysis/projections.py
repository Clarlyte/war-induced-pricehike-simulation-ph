"""Forward projections from scenario results.

Generates illustrative trend extrapolations and inequality metrics that
go into the analysis report. Projections are simple linear / multiplier
extrapolations of the model's monthly outputs and are clearly labelled
as illustrative rather than predictive.
"""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
RUNS_DIR = ROOT / "output" / "runs"
PROJ_DIR = ROOT / "output" / "projections"


def load_model_run(scenario: str) -> pd.DataFrame:
    path = RUNS_DIR / f"{scenario}_model.csv"
    return pd.read_csv(path)


def project_class_counts(scenario: str, extra_months: int = 12) -> pd.DataFrame:
    """Extend class counts by linearly extrapolating month-over-month trend.

    This is illustrative: in steady-state the model converges, so the
    extrapolation is informative mainly for the transition months.
    """
    df = load_model_run(scenario)
    last = df.tail(3)
    trends = {col: float((last[col].iloc[-1] - last[col].iloc[0]) / max(len(last) - 1, 1))
              for col in ("count_high", "count_middle", "count_low")}
    last_step = int(df["step"].iloc[-1])
    rows: list[dict] = []
    base = df.iloc[-1]
    for k in range(1, extra_months + 1):
        rows.append({
            "scenario": scenario,
            "step": last_step + k,
            "projected": True,
            "count_high": max(0.0, base["count_high"] + trends["count_high"] * k),
            "count_middle": max(0.0, base["count_middle"] + trends["count_middle"] * k),
            "count_low": max(0.0, base["count_low"] + trends["count_low"] * k),
            "col_index": float(base["col_index"]),
            "mean_buying_power": float(base["mean_buying_power"]),
        })
    projected = pd.DataFrame(rows)
    historical = df.assign(projected=False)
    return pd.concat([historical, projected], ignore_index=True)


def inequality_metrics(scenario: str) -> dict[str, float]:
    """Compute simple inequality metrics from the final-month agent CSV."""
    agents_path = RUNS_DIR / f"{scenario}_agents.csv"
    agents = pd.read_csv(agents_path)
    bp = agents["buying_power"].to_numpy(dtype=float)
    metrics: dict[str, float] = {
        "scenario": scenario,
        "mean_buying_power": float(np.mean(bp)),
        "median_buying_power": float(np.median(bp)),
        "p10": float(np.percentile(bp, 10)),
        "p90": float(np.percentile(bp, 90)),
        "p90_p10_ratio": float(np.percentile(bp, 90) / max(np.percentile(bp, 10), 1.0)),
        "gini": _gini(bp),
        "low_class_count": int((agents["effective_class"] == "low").sum()),
        "share_rural": float((agents["location"] == "rural").mean()),
    }
    return metrics


def _gini(values: np.ndarray) -> float:
    x = np.array(values, dtype=float)
    if np.amin(x) < 0:
        x = x - np.amin(x)
    x = x + 1e-9
    x = np.sort(x)
    n = x.size
    cumulative = np.cumsum(x)
    return float((n + 1 - 2 * np.sum(cumulative) / cumulative[-1]) / n)


def scenario_comparison_table(summary_df: pd.DataFrame) -> pd.DataFrame:
    """Compute deltas relative to the baseline scenario."""
    baseline = summary_df[summary_df["scenario"] == "S0_baseline"].iloc[0]
    rows: list[dict] = []
    for _, row in summary_df.iterrows():
        rows.append({
            "scenario": row["scenario"],
            "oil_shock_pct": row["oil_shock_pct"],
            "gov_response_level": row["gov_response_level"],
            "col_index": row["col_index"],
            "col_delta_vs_baseline": row["col_index"] - baseline["col_index"],
            "mean_buying_power": row["mean_buying_power"],
            "buying_power_delta_pct": (row["mean_buying_power"] - baseline["mean_buying_power"])
                                       / baseline["mean_buying_power"] * 100,
            "low_class_delta": int(row["count_low"] - baseline["count_low"]),
            "rural_vs_urban_gap": row["buying_power_rural"] - row["buying_power_urban"],
        })
    return pd.DataFrame(rows)


def export_projections() -> None:
    PROJ_DIR.mkdir(parents=True, exist_ok=True)
    summary = pd.read_csv(RUNS_DIR / "summary.csv")
    comp = scenario_comparison_table(summary)
    comp.to_csv(PROJ_DIR / "scenario_deltas.csv", index=False)

    ineq_rows = [inequality_metrics(s) for s in summary["scenario"]]
    ineq_df = pd.DataFrame(ineq_rows)
    ineq_df.to_csv(PROJ_DIR / "inequality_metrics.csv", index=False)

    for s in summary["scenario"]:
        proj = project_class_counts(s, extra_months=12)
        proj.to_csv(PROJ_DIR / f"{s}_projection.csv", index=False)

    print(f"Wrote projection CSVs to {PROJ_DIR}")


if __name__ == "__main__":
    export_projections()
