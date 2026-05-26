"""Smoke test for the headless simulation.

Runs the model for 12 months under two scenarios and prints the key
outcomes. Used to verify Commit 5 before adding the dashboard.

Usage:
    python -m experiments.smoke_run
"""

from __future__ import annotations

from pathlib import Path

import pandas as pd

from pricehike_abm.model import PriceHikeModel


OUTPUT_DIR = Path(__file__).resolve().parent.parent / "output" / "runs"


def run(name: str, **kwargs) -> pd.DataFrame:
    model = PriceHikeModel(**kwargs)
    model.run()
    df = model.datacollector.get_model_vars_dataframe()
    df.insert(0, "scenario", name)
    out_path = OUTPUT_DIR / f"smoke_{name}.csv"
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    df.to_csv(out_path, index=False)
    return df


def main() -> None:
    print("=" * 70)
    print("PriceHike ABM - Smoke Run")
    print("=" * 70)

    baseline = run("baseline", oil_shock_pct=0, gov_response_level=0)
    shocked = run("shock_40pct", oil_shock_pct=40, gov_response_level=0)
    shocked_supported = run("shock_40pct_gov2", oil_shock_pct=40, gov_response_level=2)

    cols = [
        "step",
        "oil_shock_pct",
        "col_index",
        "mean_buying_power",
        "count_low",
        "count_middle",
        "count_high",
        "food_at_risk_share",
        "buying_power_rural",
        "buying_power_urban",
    ]

    for name, df in (("baseline", baseline), ("shock_40pct", shocked),
                     ("shock_40pct_gov2", shocked_supported)):
        print(f"\n>>> Scenario: {name}")
        print(df[cols].tail(3).to_string(index=False, float_format=lambda x: f"{x:,.2f}"))

    print("\n>>> Final-month comparison")
    summary = pd.DataFrame({
        "baseline": baseline.iloc[-1][cols],
        "shock_40pct": shocked.iloc[-1][cols],
        "shock_40pct_gov2": shocked_supported.iloc[-1][cols],
    })
    print(summary.to_string(float_format=lambda x: f"{x:,.2f}"))


if __name__ == "__main__":
    main()
