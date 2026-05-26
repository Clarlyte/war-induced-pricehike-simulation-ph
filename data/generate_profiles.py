"""Generate the synthetic household population CSV from parameters.yaml.

Run once (or whenever parameters change) to refresh
`data/household_profiles.csv`. The CSV is checked into version control so
runs are reproducible without re-executing this script.

Usage:
    python data/generate_profiles.py
"""

from __future__ import annotations

import csv
import random
from pathlib import Path

import yaml


def main() -> None:
    here = Path(__file__).resolve().parent
    params_path = here / "parameters.yaml"
    out_path = here / "household_profiles.csv"

    with params_path.open("r", encoding="utf-8") as fh:
        params = yaml.safe_load(fh)

    n = params["simulation"]["num_agents"]
    seed = params["simulation"]["seed"]
    rng = random.Random(seed)

    income_classes = params["income_classes"]
    location_mods = params["location_modifiers"]
    employment = params["employment_exposure"]
    vehicles = params["vehicle_exposure"]
    savings = params["savings_buffer"]

    def weighted_choice(options: dict[str, dict]) -> str:
        keys = list(options.keys())
        weights = [options[k]["population_share"] if isinstance(options[k]["population_share"], (int, float))
                   else options[k]["population_share"]["value"]
                   for k in keys]
        return rng.choices(keys, weights=weights, k=1)[0]

    def class_weighted_choice() -> str:
        keys = list(income_classes.keys())
        weights = [income_classes[k]["share_of_population"]["value"] for k in keys]
        return rng.choices(keys, weights=weights, k=1)[0]

    def location_weighted_choice() -> str:
        keys = list(location_mods.keys())
        weights = [location_mods[k]["population_share"]["value"] for k in keys]
        return rng.choices(keys, weights=weights, k=1)[0]

    rows: list[dict] = []
    for i in range(n):
        income_class = class_weighted_choice()
        base_income = income_classes[income_class]["monthly_income_php"]["value"]
        income = int(base_income * rng.uniform(0.85, 1.15))

        location = location_weighted_choice()
        employment_type = weighted_choice(employment)
        vehicle = weighted_choice(vehicles)
        savings_level = weighted_choice(savings)

        if income_class == "low":
            gov_support_eligible = rng.random() < 0.6
        elif income_class == "middle":
            gov_support_eligible = rng.random() < 0.2
        else:
            gov_support_eligible = rng.random() < 0.05

        if income_class == "low":
            household_size = rng.randint(4, 7)
        elif income_class == "middle":
            household_size = rng.randint(3, 5)
        else:
            household_size = rng.randint(2, 4)

        rows.append({
            "agent_id": i,
            "income_class": income_class,
            "monthly_income_php": income,
            "location": location,
            "employment_type": employment_type,
            "vehicle_type": vehicle,
            "savings_buffer": savings_level,
            "household_size": household_size,
            "gov_support_eligible": int(gov_support_eligible),
        })

    fieldnames = list(rows[0].keys())
    with out_path.open("w", encoding="utf-8", newline="") as fh:
        writer = csv.DictWriter(fh, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)

    print(f"Wrote {len(rows)} household profiles to {out_path}")

    counts: dict[str, dict] = {"income_class": {}, "location": {},
                                "employment_type": {}, "vehicle_type": {},
                                "savings_buffer": {}}
    for row in rows:
        for key in counts:
            v = row[key]
            counts[key][v] = counts[key].get(v, 0) + 1
    print("Population summary:")
    for k, c in counts.items():
        shares = {kk: round(vv / n, 3) for kk, vv in c.items()}
        print(f"  {k}: {shares}")


if __name__ == "__main__":
    main()
