"""Model and agent reporters wired into Mesa's DataCollector.

Centralising reporters here keeps `model.py` short and means the same
metrics drive both the live dashboard charts and the offline analysis
scripts.
"""

from __future__ import annotations

from statistics import mean
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from pricehike_abm.agents.household import HouseholdAgent
    from pricehike_abm.model import PriceHikeModel


def _agent_snapshots(model: "PriceHikeModel") -> list:
    return [a.snapshot for a in model.agents]


def _mean_or_zero(values: list[float]) -> float:
    return float(mean(values)) if values else 0.0


def col_index(model: "PriceHikeModel") -> float:
    snaps = _agent_snapshots(model)
    return _mean_or_zero([s.cost_of_living_index for s in snaps])


def mean_buying_power(model: "PriceHikeModel") -> float:
    snaps = _agent_snapshots(model)
    return _mean_or_zero([s.buying_power for s in snaps])


def class_count(model: "PriceHikeModel", cls: str) -> int:
    return sum(1 for s in _agent_snapshots(model) if s.effective_class == cls)


def count_high(model: "PriceHikeModel") -> int:
    return class_count(model, "high")


def count_middle(model: "PriceHikeModel") -> int:
    return class_count(model, "middle")


def count_low(model: "PriceHikeModel") -> int:
    return class_count(model, "low")


def food_at_risk_share(model: "PriceHikeModel") -> float:
    snaps = _agent_snapshots(model)
    if not snaps:
        return 0.0
    return sum(1 for s in snaps if s.food_at_risk) / len(snaps)


def bill_stress_share(model: "PriceHikeModel") -> float:
    snaps = _agent_snapshots(model)
    if not snaps:
        return 0.0
    return sum(1 for s in snaps if s.bill_stress) / len(snaps)


def mean_food_spend(model: "PriceHikeModel") -> float:
    return _mean_or_zero([s.food for s in _agent_snapshots(model)])


def mean_utilities_spend(model: "PriceHikeModel") -> float:
    return _mean_or_zero([s.utilities for s in _agent_snapshots(model)])


def mean_transport_spend(model: "PriceHikeModel") -> float:
    return _mean_or_zero([s.transport for s in _agent_snapshots(model)])


def buying_power_by_class(model: "PriceHikeModel", income_class: str) -> float:
    values = [a.snapshot.buying_power for a in model.agents if a.income_class == income_class]
    return _mean_or_zero(values)


def buying_power_low(model: "PriceHikeModel") -> float:
    return buying_power_by_class(model, "low")


def buying_power_middle(model: "PriceHikeModel") -> float:
    return buying_power_by_class(model, "middle")


def buying_power_high(model: "PriceHikeModel") -> float:
    return buying_power_by_class(model, "high")


def buying_power_rural(model: "PriceHikeModel") -> float:
    values = [a.snapshot.buying_power for a in model.agents if a.location == "rural"]
    return _mean_or_zero(values)


def buying_power_urban(model: "PriceHikeModel") -> float:
    values = [a.snapshot.buying_power for a in model.agents if a.location == "urban"]
    return _mean_or_zero(values)


def oil_shock_pct(model: "PriceHikeModel") -> float:
    return float(model.environment.oil_shock_pct)


def fuel_multiplier(model: "PriceHikeModel") -> float:
    return float(model.environment.domestic_fuel_multiplier)


def gov_response_level(model: "PriceHikeModel") -> int:
    return int(model.policy.level)


MODEL_REPORTERS: dict = {
    "step": lambda m: m.steps,
    "oil_shock_pct": oil_shock_pct,
    "fuel_multiplier": fuel_multiplier,
    "gov_response_level": gov_response_level,
    "col_index": col_index,
    "mean_buying_power": mean_buying_power,
    "count_high": count_high,
    "count_middle": count_middle,
    "count_low": count_low,
    "food_at_risk_share": food_at_risk_share,
    "bill_stress_share": bill_stress_share,
    "mean_food_spend": mean_food_spend,
    "mean_utilities_spend": mean_utilities_spend,
    "mean_transport_spend": mean_transport_spend,
    "buying_power_low": buying_power_low,
    "buying_power_middle": buying_power_middle,
    "buying_power_high": buying_power_high,
    "buying_power_rural": buying_power_rural,
    "buying_power_urban": buying_power_urban,
}


AGENT_REPORTERS: dict = {
    "income_class": lambda a: a.income_class,
    "effective_class": lambda a: a.effective_class,
    "location": lambda a: a.location,
    "employment_type": lambda a: a.employment_type,
    "buying_power": lambda a: a.snapshot.buying_power,
    "buying_power_ratio": lambda a: a.snapshot.buying_power_ratio,
    "food": lambda a: a.snapshot.food,
    "utilities": lambda a: a.snapshot.utilities,
    "transport": lambda a: a.snapshot.transport,
    "food_at_risk": lambda a: a.snapshot.food_at_risk,
    "bill_stress": lambda a: a.snapshot.bill_stress,
    "class_progress": lambda a: a.snapshot.class_progress,
}
