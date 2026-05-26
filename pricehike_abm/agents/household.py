"""HouseholdAgent.

One agent = one Filipino household. Implements the monthly budget cycle
from the proposal (Section 4.1) and the buying-power-driven class
migration described in the README.

Each step the agent:
    1. Reads the current domestic fuel multiplier from the model.
    2. Recomputes essential category costs via pass-through rules.
    3. Applies any government policy offsets it qualifies for.
    4. Computes remaining buying power.
    5. Stages cuts when buying power is insufficient.
    6. Updates its effective income class (with hysteresis) and the
       0..1 colour-gradient progress used by the visualization layer.
    7. Records stress flags.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Literal

import mesa

if TYPE_CHECKING:
    from pricehike_abm.model import PriceHikeModel


IncomeClass = Literal["low", "middle", "high"]
Location = Literal["urban", "rural"]
EmploymentType = Literal["transport_worker", "non_transport", "self_employed"]
VehicleType = Literal["none", "motorcycle", "car"]
SavingsLevel = Literal["none", "one_month", "three_plus"]


@dataclass
class BudgetSnapshot:
    """Per-step financial snapshot exported to the data collector."""

    food: float = 0.0
    utilities: float = 0.0
    transport: float = 0.0
    other: float = 0.0
    fuel_private: float = 0.0
    effective_income: float = 0.0
    buying_power: float = 0.0
    buying_power_ratio: float = 0.0
    cost_of_living_index: float = 100.0
    food_at_risk: bool = False
    bill_stress: bool = False
    effective_class: IncomeClass = "middle"
    class_progress: float = 0.5
    savings_remaining_php: float = 0.0


class HouseholdAgent(mesa.Agent):
    """Filipino household agent.

    Attributes that never change after spawn:
        income_class, monthly_income_php, base_shares, location,
        employment_type, vehicle_type, savings_level, household_size,
        gov_support_eligible.

    Dynamic attributes (refreshed each step):
        snapshot (BudgetSnapshot), effective_class, class_progress,
        savings_php, last_buying_power_ratio.
    """

    def __init__(
        self,
        model: "PriceHikeModel",
        income_class: IncomeClass,
        monthly_income_php: float,
        location: Location,
        employment_type: EmploymentType,
        vehicle_type: VehicleType,
        savings_buffer: SavingsLevel,
        household_size: int,
        gov_support_eligible: bool,
    ) -> None:
        super().__init__(model)

        self.income_class: IncomeClass = income_class
        self.monthly_income_php: float = float(monthly_income_php)
        self.location: Location = location
        self.employment_type: EmploymentType = employment_type
        self.vehicle_type: VehicleType = vehicle_type
        self.savings_buffer: SavingsLevel = savings_buffer
        self.household_size: int = int(household_size)
        self.gov_support_eligible: bool = bool(gov_support_eligible)

        params = model.params
        self.base_shares: dict[str, float] = dict(params.expenditure_shares(income_class))

        food_mult = params.location_modifier(location, "food_share_multiplier")
        adjusted_food = self.base_shares["food"] * food_mult
        delta = adjusted_food - self.base_shares["food"]
        self.base_shares["food"] = adjusted_food
        self.base_shares["other"] = max(0.0, self.base_shares["other"] - delta)

        months_covered = params.savings_months(savings_buffer)
        essentials = sum(
            self.monthly_income_php * self.base_shares[k]
            for k in ("food", "utilities", "transport")
        )
        self.savings_php: float = months_covered * essentials
        self.initial_savings_php: float = self.savings_php

        self.effective_class: IncomeClass = income_class
        self.last_buying_power_ratio: float = self._baseline_buying_power_ratio()
        self.class_progress: float = self._compute_class_progress(
            self.last_buying_power_ratio
        )

        essentials_share = sum(self.base_shares[k] for k in ("food", "utilities", "transport"))
        baseline_bp = self.monthly_income_php * (1.0 - essentials_share)
        self.snapshot: BudgetSnapshot = BudgetSnapshot(
            food=self.monthly_income_php * self.base_shares["food"],
            utilities=self.monthly_income_php * self.base_shares["utilities"],
            transport=self.monthly_income_php * self.base_shares["transport"],
            other=self.monthly_income_php * self.base_shares["other"],
            effective_class=self.effective_class,
            class_progress=self.class_progress,
            effective_income=self.monthly_income_php,
            buying_power=baseline_bp,
            buying_power_ratio=self.last_buying_power_ratio,
            cost_of_living_index=100.0,
            savings_remaining_php=self.savings_php,
        )

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------
    def _baseline_buying_power_ratio(self) -> float:
        essentials_share = sum(self.base_shares[k] for k in ("food", "utilities", "transport"))
        return max(0.0, 1.0 - essentials_share)

    def _compute_class_progress(self, ratio: float) -> float:
        """Map buying-power ratio to a 0..1 colour-gradient position.

        0.0 == solid red (low effective class), 0.5 == orange (middle),
        1.0 == solid green (high). Continuous regardless of class label
        so the dashboard can show gradual colour shifts month-to-month.
        """
        params = self.model.params
        anchor = params.class_high_threshold + 0.20
        ratio = max(0.0, min(anchor, ratio))
        return ratio / anchor if anchor > 0 else 0.5

    # ------------------------------------------------------------------
    # Monthly step
    # ------------------------------------------------------------------
    def step(self) -> None:  # noqa: D401 - Mesa hook
        model = self.model
        params = model.params
        env = model.environment
        policy = model.policy

        fuel_delta = env.domestic_fuel_multiplier - 1.0

        loc_transport_mod = params.location_modifier(self.location, "transport_pass_through_multiplier")
        vehicle_mult = params.vehicle_fuel_intensity(self.vehicle_type)

        food_factor = 1.0 + fuel_delta * params.food_pass_through
        utilities_factor = 1.0 + fuel_delta * params.utilities_pass_through
        transport_factor = 1.0 + fuel_delta * params.transport_pass_through * loc_transport_mod * vehicle_mult

        income = self.monthly_income_php
        sensitivity = params.employment_income_sensitivity(self.employment_type)
        effective_income = income * (1.0 + sensitivity * fuel_delta)

        food_need = income * self.base_shares["food"] * food_factor
        utilities_need = income * self.base_shares["utilities"] * utilities_factor
        transport_need = income * self.base_shares["transport"] * transport_factor
        other_need = income * self.base_shares["other"]

        policy_effect = policy.apply(self, env, params)
        effective_income += policy_effect["income_boost"]
        transport_need *= (1.0 - policy_effect["fuel_subsidy_pct"])

        essential_need = food_need + utilities_need + transport_need
        budget_after_essentials = effective_income - essential_need

        food_paid = food_need
        utilities_paid = utilities_need
        transport_paid = transport_need
        other_paid = other_need
        savings_drawn = 0.0
        food_at_risk = False
        bill_stress = False

        if budget_after_essentials < other_need:
            shortfall = other_need - budget_after_essentials
            if self.savings_php > 0:
                drawn = min(self.savings_php, shortfall)
                self.savings_php -= drawn
                savings_drawn = drawn
                shortfall -= drawn
            if shortfall > 0:
                other_cut = min(other_paid, shortfall)
                other_paid -= other_cut
                shortfall -= other_cut
            if shortfall > 0:
                transport_cut = min(transport_paid * 0.30, shortfall)
                transport_paid -= transport_cut
                shortfall -= transport_cut
            if shortfall > 0:
                bill_cut = min(utilities_paid * 0.20, shortfall)
                utilities_paid -= bill_cut
                shortfall -= bill_cut
                bill_stress = bill_cut > 1.0
            if shortfall > 0:
                food_cut = min(food_paid * 0.30, shortfall)
                food_paid -= food_cut
                shortfall -= food_cut
                food_at_risk = food_cut > 1.0
        else:
            surplus = budget_after_essentials - other_need
            self.savings_php += max(0.0, surplus * 0.30)

        if food_paid < food_need * params.food_at_risk_ratio:
            food_at_risk = True
        if utilities_paid < utilities_need * params.bill_stress_ratio:
            bill_stress = True

        actual_essentials = food_paid + utilities_paid + transport_paid
        buying_power = effective_income - actual_essentials
        buying_power_ratio = buying_power / effective_income if effective_income > 0 else 0.0

        baseline_essentials = sum(
            self.monthly_income_php * self.base_shares[k] for k in ("food", "utilities", "transport")
        )
        col_index = 100.0 * (actual_essentials / baseline_essentials) if baseline_essentials > 0 else 100.0

        self._update_effective_class(buying_power_ratio)
        self.last_buying_power_ratio = buying_power_ratio
        self.class_progress = self._compute_class_progress(buying_power_ratio)

        self.snapshot = BudgetSnapshot(
            food=food_paid,
            utilities=utilities_paid,
            transport=transport_paid,
            other=other_paid,
            fuel_private=0.0,
            effective_income=effective_income,
            buying_power=buying_power,
            buying_power_ratio=buying_power_ratio,
            cost_of_living_index=col_index,
            food_at_risk=food_at_risk,
            bill_stress=bill_stress,
            effective_class=self.effective_class,
            class_progress=self.class_progress,
            savings_remaining_php=self.savings_php,
        )

    # ------------------------------------------------------------------
    # Class migration with hysteresis
    # ------------------------------------------------------------------
    def _update_effective_class(self, ratio: float) -> None:
        params = self.model.params
        high = params.class_high_threshold
        mid = params.class_middle_threshold
        hys = params.class_hysteresis

        current = self.effective_class
        if current == "high":
            if ratio < high - hys:
                self.effective_class = "middle"
                if ratio < mid - hys:
                    self.effective_class = "low"
        elif current == "middle":
            if ratio >= high + hys:
                self.effective_class = "high"
            elif ratio < mid - hys:
                self.effective_class = "low"
        else:
            if ratio >= mid + hys:
                self.effective_class = "middle"
                if ratio >= high + hys:
                    self.effective_class = "high"
