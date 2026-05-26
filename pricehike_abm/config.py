"""Parameter loader.

Reads `data/parameters.yaml` into a simple, attribute-style container so
that every module references the same RRL-backed defaults. No magic
numbers are introduced anywhere in the simulation code.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yaml

DEFAULT_PARAMS_PATH = Path(__file__).resolve().parent.parent / "data" / "parameters.yaml"


def _extract_value(node: Any) -> Any:
    """Return the `value` field if the node is a `{value, source, note}` dict,
    otherwise return the node itself. Lets us write either form in YAML.
    """
    if isinstance(node, dict) and "value" in node and ("source" in node or "note" in node):
        return node["value"]
    return node


@dataclass
class Parameters:
    """Container for the entire calibrated parameter set."""

    raw: dict[str, Any]
    path: Path = field(default=DEFAULT_PARAMS_PATH)

    @classmethod
    def load(cls, path: Path | str | None = None) -> "Parameters":
        p = Path(path) if path else DEFAULT_PARAMS_PATH
        with p.open("r", encoding="utf-8") as fh:
            data = yaml.safe_load(fh)
        return cls(raw=data, path=p)

    def get(self, *keys: str) -> Any:
        """Walk nested keys and return the leaf value (unwrapping `value`)."""
        node: Any = self.raw
        for k in keys:
            node = node[k]
        return _extract_value(node)

    @property
    def num_agents(self) -> int:
        return int(self.get("simulation", "num_agents"))

    @property
    def grid_width(self) -> int:
        return int(self.get("simulation", "grid_width"))

    @property
    def grid_height(self) -> int:
        return int(self.get("simulation", "grid_height"))

    @property
    def urban_core_radius(self) -> int:
        return int(self.get("simulation", "urban_core_radius"))

    @property
    def default_months(self) -> int:
        return int(self.get("simulation", "default_months"))

    @property
    def seed(self) -> int:
        return int(self.get("simulation", "seed"))

    def expenditure_shares(self, income_class: str) -> dict[str, float]:
        shares = self.raw["expenditure_shares"][income_class]
        return {
            "food": float(shares["food"]),
            "utilities": float(shares["utilities"]),
            "transport": float(shares["transport"]),
            "other": float(shares["other"]),
        }

    @property
    def fuel_pass_through(self) -> float:
        return float(self.get("pass_through", "fuel_pass_through"))

    @property
    def food_pass_through(self) -> float:
        return float(self.get("pass_through", "food"))

    @property
    def utilities_pass_through(self) -> float:
        return float(self.get("pass_through", "utilities"))

    @property
    def transport_pass_through(self) -> float:
        return float(self.get("pass_through", "transport"))

    def location_modifier(self, location: str, key: str) -> float:
        return float(self.get("location_modifiers", location, key))

    def employment_income_sensitivity(self, employment_type: str) -> float:
        return float(self.get("employment_exposure", employment_type, "income_sensitivity"))

    def vehicle_fuel_intensity(self, vehicle_type: str) -> float:
        return float(self.get("vehicle_exposure", vehicle_type, "fuel_intensity_multiplier"))

    def savings_months(self, level: str) -> int:
        return int(self.get("savings_buffer", level, "months_covered"))

    @property
    def class_high_threshold(self) -> float:
        return float(self.get("class_thresholds", "high_threshold"))

    @property
    def class_middle_threshold(self) -> float:
        return float(self.get("class_thresholds", "middle_threshold"))

    @property
    def class_hysteresis(self) -> float:
        return float(self.get("class_thresholds", "hysteresis"))

    @property
    def food_at_risk_ratio(self) -> float:
        return float(self.get("stress_thresholds", "food_at_risk_ratio"))

    @property
    def bill_stress_ratio(self) -> float:
        return float(self.get("stress_thresholds", "bill_stress_ratio"))

    def government_response(self, level: int) -> dict[str, Any]:
        key = f"level_{level}"
        return dict(self.raw["government_response"][key])

    # --- dynamics (Section 12) ---

    @property
    def shock_ramp_pct_per_month(self) -> float:
        return float(self.get("dynamics", "shock_ramp_pct_per_month"))

    def pass_through_lag(self, category: str) -> int:
        return int(self.raw["dynamics"]["pass_through_lags_months"][category])

    @property
    def max_pass_through_lag(self) -> int:
        lags = self.raw["dynamics"]["pass_through_lags_months"]
        return max(int(lags["transport"]), int(lags["food"]), int(lags["utilities"]))

    @property
    def persistence_shock_months_threshold(self) -> int:
        return int(self.get("dynamics", "persistence_shock_months_threshold"))

    @property
    def persistence_food_pass_through_boost(self) -> float:
        return float(self.get("dynamics", "persistence_food_pass_through_boost"))

    def coping_ladder(self, key: str) -> float:
        return float(self.raw["dynamics"]["coping_ladder"][key])

    @property
    def transport_worker_erosion_monthly(self) -> float:
        return float(self.get("dynamics", "transport_worker_erosion_monthly"))

    @property
    def transport_worker_erosion_floor(self) -> float:
        return float(self.get("dynamics", "transport_worker_erosion_floor"))

    @property
    def transport_worker_recovery_monthly(self) -> float:
        return float(self.get("dynamics", "transport_worker_recovery_monthly"))

    @property
    def policy_activation_lag_months(self) -> int:
        return int(self.get("dynamics", "policy_activation_lag_months"))

    @property
    def policy_stress_boost_multiplier(self) -> float:
        return float(self.get("dynamics", "policy_stress_boost_multiplier"))

    @property
    def class_downgrade_persistence_months(self) -> int:
        return int(self.get("dynamics", "class_downgrade_persistence_months"))

    @property
    def class_upgrade_persistence_months(self) -> int:
        return int(self.get("dynamics", "class_upgrade_persistence_months"))

    def vehicle_substitution(self, key: str) -> float:
        return float(self.raw["dynamics"]["vehicle_substitution"][key])
