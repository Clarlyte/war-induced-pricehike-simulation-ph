"""HouseholdAgent.

One agent = one Filipino household. Implements the monthly budget cycle
from the proposal (Section 4.1), buying-power-driven class migration,
and RRL-backed temporal dynamics (coping ladder, erosion, substitution).
"""

from __future__ import annotations

from dataclasses import dataclass
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
    months_under_stress: int = 0
    income_erosion_factor: float = 1.0
    effective_vehicle_type: str = "none"


class HouseholdAgent(mesa.Agent):
    """Filipino household agent with conditional monthly coping moves."""

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
        self.had_savings_at_start: bool = self.savings_php > 0

        self.effective_class: IncomeClass = income_class
        self.effective_vehicle_type: VehicleType = vehicle_type
        self.income_erosion_factor: float = 1.0
        self.months_under_stress: int = 0
        self.months_post_buffer: int = 0
        self.months_low_ratio: int = 0
        self.months_below_high_ratio: int = 0
        self.months_high_ratio: int = 0
        self.months_mid_ratio: int = 0
        self.months_vehicle_stress: int = 0
        self.last_food_at_risk: bool = False
        self.last_bill_stress: bool = False

        self.last_buying_power_ratio: float = self._baseline_buying_power_ratio()
        init_ratio = self.last_buying_power_ratio
        high_t = params.class_high_threshold
        mid_t = params.class_middle_threshold
        if init_ratio >= high_t:
            self.effective_class = "high"
        elif init_ratio >= mid_t:
            self.effective_class = "middle"
        else:
            self.effective_class = "low"
        self.class_progress: float = self._compute_class_progress(self.last_buying_power_ratio)

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
            effective_vehicle_type=self.effective_vehicle_type,
        )

    def _baseline_buying_power_ratio(self) -> float:
        essentials_share = sum(self.base_shares[k] for k in ("food", "utilities", "transport"))
        return max(0.0, 1.0 - essentials_share)

    def _compute_class_progress(self, ratio: float) -> float:
        params = self.model.params
        anchor = params.class_high_threshold + 0.20
        ratio = max(0.0, min(anchor, ratio))
        return ratio / anchor if anchor > 0 else 0.5

    def _update_vehicle_substitution(self, buying_power_ratio: float) -> None:
        params = self.model.params
        threshold = params.vehicle_substitution("ratio_threshold")
        persist = int(params.vehicle_substitution("persistence_months"))

        if buying_power_ratio < threshold:
            self.months_vehicle_stress += 1
        else:
            self.months_vehicle_stress = 0

        if (
            self.vehicle_type == "car"
            and self.effective_vehicle_type == "car"
            and self.months_vehicle_stress >= persist
        ):
            self.effective_vehicle_type = "motorcycle"

    def _update_income_erosion(self, transport_delta: float) -> None:
        params = self.model.params
        if self.employment_type != "transport_worker":
            return
        if transport_delta > 0.10:
            self.income_erosion_factor = max(
                params.transport_worker_erosion_floor,
                self.income_erosion_factor * (1.0 - params.transport_worker_erosion_monthly),
            )
        elif transport_delta < 0.05:
            self.income_erosion_factor = min(
                1.0,
                self.income_erosion_factor + params.transport_worker_recovery_monthly,
            )

    def _apply_coping_ladder(
        self,
        params,
        effective_income: float,
        food_paid: float,
        utilities_paid: float,
        transport_paid: float,
        other_paid: float,
        food_need: float,
        utilities_need: float,
        transport_need: float,
    ) -> tuple[float, float, float, float, bool, bool]:
        """Staged cuts when total spending exceeds effective income."""
        food_at_risk = False
        bill_stress = False

        total_paid = food_paid + utilities_paid + transport_paid + other_paid
        if total_paid <= effective_income:
            surplus = effective_income - total_paid
            self.savings_php += max(0.0, surplus * 0.30)
        else:
            shortfall = total_paid - effective_income
            if self.savings_php > 0:
                drawn = min(self.savings_php, shortfall)
                self.savings_php -= drawn
                shortfall -= drawn

            if self.savings_php <= 0 and self.had_savings_at_start:
                self.months_post_buffer += 1

            if shortfall > 0:
                projected_ratio = (
                    (effective_income - food_paid - utilities_paid - transport_paid) / effective_income
                    if effective_income > 0
                    else 0.0
                )
                cut_other = params.coping_ladder("ratio_cut_other")
                cut_transport = params.coping_ladder("ratio_cut_transport")
                cut_utilities = params.coping_ladder("ratio_cut_utilities")

                if projected_ratio >= cut_other:
                    c = min(other_paid, shortfall)
                    other_paid -= c
                    shortfall -= c
                elif projected_ratio >= cut_transport:
                    c = min(transport_paid * params.coping_ladder("transport_cut_max"), shortfall)
                    transport_paid -= c
                    shortfall -= c
                elif projected_ratio >= cut_utilities:
                    c = min(utilities_paid * params.coping_ladder("utility_cut_max"), shortfall)
                    utilities_paid -= c
                    shortfall -= c
                    bill_stress = c > 1.0
                else:
                    food_max = params.coping_ladder("food_cut_max")
                    if self.months_post_buffer >= params.coping_ladder("post_buffer_months"):
                        food_max = params.coping_ladder("post_buffer_food_cut_max")
                    c = min(food_paid * food_max, shortfall)
                    food_paid -= c
                    shortfall -= c
                    food_at_risk = c > 1.0

                if shortfall > 0:
                    c = min(other_paid, shortfall)
                    other_paid -= c
                    shortfall -= c
                if shortfall > 0:
                    c = min(transport_paid * params.coping_ladder("transport_cut_max"), shortfall)
                    transport_paid -= c
                    shortfall -= c
                if shortfall > 0:
                    c = min(utilities_paid * params.coping_ladder("utility_cut_max"), shortfall)
                    utilities_paid -= c
                    shortfall -= c
                    bill_stress = bill_stress or c > 1.0
                if shortfall > 0:
                    food_max = (
                        params.coping_ladder("post_buffer_food_cut_max")
                        if self.months_post_buffer >= params.coping_ladder("post_buffer_months")
                        else params.coping_ladder("food_cut_max")
                    )
                    c = min(food_paid * food_max, shortfall)
                    food_paid -= c
                    shortfall -= c
                    food_at_risk = food_at_risk or c > 1.0

        if food_paid < food_need * params.food_at_risk_ratio:
            food_at_risk = True
        if utilities_paid < utilities_need * params.bill_stress_ratio:
            bill_stress = True

        return food_paid, utilities_paid, transport_paid, other_paid, food_at_risk, bill_stress

    def step(self) -> None:  # noqa: D401 - Mesa hook
        model = self.model
        params = model.params
        env = model.environment
        policy = model.policy
        sd = model.shock_dynamics

        transport_delta = sd.category_fuel_delta("transport", params, env)
        food_delta = sd.category_fuel_delta("food", params, env)
        utilities_delta = sd.category_fuel_delta("utilities", params, env)

        loc_transport_mod = params.location_modifier(self.location, "transport_pass_through_multiplier")
        vehicle_mult = params.vehicle_fuel_intensity(self.effective_vehicle_type)

        transport_factor = 1.0 + transport_delta * params.transport_pass_through * loc_transport_mod * vehicle_mult
        food_factor = 1.0 + food_delta * params.food_pass_through
        utilities_factor = 1.0 + utilities_delta * params.utilities_pass_through

        income = self.monthly_income_php
        sensitivity = params.employment_income_sensitivity(self.employment_type)
        base_effective = income * (1.0 + sensitivity * transport_delta)

        self._update_income_erosion(transport_delta)
        effective_income = base_effective * self.income_erosion_factor

        food_need = income * self.base_shares["food"] * food_factor
        utilities_need = income * self.base_shares["utilities"] * utilities_factor
        transport_need = income * self.base_shares["transport"] * transport_factor
        other_need = income * self.base_shares["other"]

        policy_effect = policy.apply(self, env, params, sd)
        effective_income += policy_effect["income_boost"]
        transport_need *= (1.0 - policy_effect["fuel_subsidy_pct"])

        food_paid = food_need
        utilities_paid = utilities_need
        transport_paid = transport_need
        other_paid = other_need

        food_paid, utilities_paid, transport_paid, other_paid, food_at_risk, bill_stress = (
            self._apply_coping_ladder(
                params,
                effective_income,
                food_paid,
                utilities_paid,
                transport_paid,
                other_paid,
                food_need,
                utilities_need,
                transport_need,
            )
        )

        actual_essentials = food_paid + utilities_paid + transport_paid
        buying_power = effective_income - actual_essentials
        buying_power_ratio = buying_power / effective_income if effective_income > 0 else 0.0

        self._update_vehicle_substitution(buying_power_ratio)

        baseline_essentials = sum(
            self.monthly_income_php * self.base_shares[k] for k in ("food", "utilities", "transport")
        )
        col_index = 100.0 * (actual_essentials / baseline_essentials) if baseline_essentials > 0 else 100.0

        mid = params.class_middle_threshold
        if buying_power_ratio < mid:
            self.months_under_stress += 1
        else:
            self.months_under_stress = 0

        self._update_effective_class(buying_power_ratio)
        self.last_buying_power_ratio = buying_power_ratio
        self.class_progress = self._compute_class_progress(buying_power_ratio)

        self.last_food_at_risk = food_at_risk
        self.last_bill_stress = bill_stress

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
            months_under_stress=self.months_under_stress,
            income_erosion_factor=self.income_erosion_factor,
            effective_vehicle_type=self.effective_vehicle_type,
        )

    def _update_effective_class(self, ratio: float) -> None:
        params = self.model.params
        high = params.class_high_threshold
        mid = params.class_middle_threshold
        hys = params.class_hysteresis
        down_persist = params.class_downgrade_persistence_months
        up_persist = params.class_upgrade_persistence_months

        if ratio < mid - hys:
            self.months_low_ratio += 1
        else:
            self.months_low_ratio = 0

        if ratio < high - hys:
            self.months_below_high_ratio += 1
        else:
            self.months_below_high_ratio = 0

        if ratio >= high + hys:
            self.months_high_ratio += 1
            self.months_mid_ratio = 0
        elif ratio >= mid + hys:
            self.months_mid_ratio += 1
            self.months_high_ratio = 0
        else:
            self.months_high_ratio = 0
            self.months_mid_ratio = 0

        current = self.effective_class
        if current == "high":
            if ratio < mid - hys and self.months_low_ratio >= down_persist:
                self.effective_class = "low"
            elif ratio < high - hys and self.months_below_high_ratio >= down_persist:
                self.effective_class = "middle"
        elif current == "middle":
            if ratio < mid - hys and self.months_low_ratio >= down_persist:
                self.effective_class = "low"
            elif ratio >= high + hys and self.months_high_ratio >= up_persist:
                self.effective_class = "high"
        elif ratio >= high + hys and self.months_high_ratio >= up_persist:
            self.effective_class = "high"
        elif ratio >= mid + hys and self.months_mid_ratio >= up_persist:
            self.effective_class = "middle"
