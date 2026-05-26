"""Batch runner for the scenario matrix.

Loads `experiments/scenarios.yaml`, runs each scenario for the configured
number of months, and writes:
    - output/runs/{scenario}_model.csv  (per-month model metrics)
    - output/runs/{scenario}_agents.csv (per-agent end-of-run snapshot)
    - output/runs/summary.csv           (one row per scenario, final month)

Usage:
    python -m experiments.run_scenarios
"""

from __future__ import annotations

from pathlib import Path

import pandas as pd
import yaml

from pricehike_abm.model import PriceHikeModel

ROOT = Path(__file__).resolve().parent.parent
SCENARIOS_PATH = ROOT / "experiments" / "scenarios.yaml"
RUNS_DIR = ROOT / "output" / "runs"


SUMMARY_COLUMNS = [
    "scenario",
    "description",
    "oil_shock_pct",
    "fuel_pass_through",
    "gov_response_level",
    "col_index",
    "mean_buying_power",
    "count_low",
    "count_middle",
    "count_high",
    "food_at_risk_share",
    "bill_stress_share",
    "buying_power_low",
    "buying_power_middle",
    "buying_power_high",
    "buying_power_rural",
    "buying_power_urban",
]


def run_scenario(name: str, params: dict, months: int) -> tuple[pd.DataFrame, pd.DataFrame]:
    model = PriceHikeModel(
        oil_shock_pct=params.get("oil_shock_pct", 0),
        gov_response_level=params.get("gov_response_level", 0),
        fuel_pass_through=params.get("fuel_pass_through"),
        food_pass_through=params.get("food_pass_through"),
        utilities_pass_through=params.get("utilities_pass_through"),
        transport_pass_through=params.get("transport_pass_through"),
    )
    model.run(months=months)

    model_df = model.datacollector.get_model_vars_dataframe().reset_index(drop=True)
    model_df.insert(0, "scenario", name)

    agent_df = model.datacollector.get_agent_vars_dataframe().reset_index()
    final_step = agent_df["Step"].max()
    agent_df = agent_df[agent_df["Step"] == final_step].copy()
    agent_df.insert(0, "scenario", name)

    return model_df, agent_df


def main() -> None:
    with SCENARIOS_PATH.open("r", encoding="utf-8") as fh:
        config = yaml.safe_load(fh)

    months = int(config.get("defaults", {}).get("months", 12))
    scenarios = config["scenarios"]
    RUNS_DIR.mkdir(parents=True, exist_ok=True)

    print(f"Running {len(scenarios)} scenarios for {months} months each...")
    summary_rows: list[dict] = []

    for scenario in scenarios:
        name: str = scenario["name"]
        desc: str = scenario.get("description", "")
        print(f"  -> {name} | {desc}")

        model_df, agent_df = run_scenario(name, scenario, months)
        model_df.to_csv(RUNS_DIR / f"{name}_model.csv", index=False)
        agent_df.to_csv(RUNS_DIR / f"{name}_agents.csv", index=False)

        final = model_df.iloc[-1]
        summary_rows.append({
            "scenario": name,
            "description": desc,
            "oil_shock_pct": scenario.get("oil_shock_pct", 0),
            "fuel_pass_through": scenario.get("fuel_pass_through", 0.35),
            "gov_response_level": scenario.get("gov_response_level", 0),
            "col_index": float(final["col_index"]),
            "mean_buying_power": float(final["mean_buying_power"]),
            "count_low": int(final["count_low"]),
            "count_middle": int(final["count_middle"]),
            "count_high": int(final["count_high"]),
            "food_at_risk_share": float(final["food_at_risk_share"]),
            "bill_stress_share": float(final["bill_stress_share"]),
            "buying_power_low": float(final["buying_power_low"]),
            "buying_power_middle": float(final["buying_power_middle"]),
            "buying_power_high": float(final["buying_power_high"]),
            "buying_power_rural": float(final["buying_power_rural"]),
            "buying_power_urban": float(final["buying_power_urban"]),
        })

    summary_df = pd.DataFrame(summary_rows, columns=SUMMARY_COLUMNS)
    summary_df.to_csv(RUNS_DIR / "summary.csv", index=False)

    print("\n=== Scenario summary (final month) ===")
    cols_to_show = [
        "scenario", "oil_shock_pct", "gov_response_level",
        "col_index", "mean_buying_power",
        "count_low", "count_middle", "count_high",
        "food_at_risk_share",
    ]
    print(summary_df[cols_to_show].to_string(
        index=False, float_format=lambda x: f"{x:,.2f}"
    ))
    print(f"\nWrote per-scenario CSVs and summary to {RUNS_DIR}")


if __name__ == "__main__":
    main()
