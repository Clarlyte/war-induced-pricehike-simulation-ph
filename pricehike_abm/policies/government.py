"""Government policy module.

Three response levels from the proposal (Section 4.2), with temporal
dynamics: activation lag after shock onset and extra support for
households that showed food or bill stress in the prior month.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, Any

from pricehike_abm.config import Parameters
from pricehike_abm.environment.market import MarketEnvironment

if TYPE_CHECKING:
    from pricehike_abm.agents.household import HouseholdAgent
    from pricehike_abm.environment.shock_dynamics import ShockDynamics


@dataclass
class GovernmentPolicy:
    """Holds the active policy level and resolves targeting per agent."""

    level: int = 0

    def set_level(self, level: int) -> None:
        if level not in (0, 1, 2):
            raise ValueError(f"Unsupported government response level: {level}")
        self.level = int(level)

    def apply(
        self,
        agent: "HouseholdAgent",
        env: MarketEnvironment,
        params: Parameters,
        shock_dynamics: "ShockDynamics",
    ) -> dict[str, float]:
        """Resolve per-agent income boost and fuel subsidy for this month."""
        no_effect = {"income_boost": 0.0, "fuel_subsidy_pct": 0.0}
        if self.level == 0 or shock_dynamics.effective_shock_pct <= 0:
            return no_effect
        if shock_dynamics.months_shock_active < params.policy_activation_lag_months:
            return no_effect

        cfg: dict[str, Any] = params.government_response(self.level)
        target_groups: list[str] = list(cfg.get("target_groups", []))
        if not self._agent_in_target_groups(agent, target_groups):
            return no_effect
        if self.level == 1 and not agent.gov_support_eligible:
            return no_effect

        scale = self._targeting_scale(agent)
        income_boost = agent.monthly_income_php * float(cfg["targeted_income_boost"]) * scale
        fuel_subsidy_pct = float(cfg["fuel_subsidy_pct"]) * scale

        if agent.last_food_at_risk or agent.last_bill_stress:
            income_boost *= params.policy_stress_boost_multiplier

        return {
            "income_boost": income_boost,
            "fuel_subsidy_pct": fuel_subsidy_pct,
        }

    @staticmethod
    def _agent_in_target_groups(agent: "HouseholdAgent", target_groups: list[str]) -> bool:
        for tag in target_groups:
            if tag in {"low", "middle", "high"} and agent.income_class == tag:
                return True
            if tag == "transport_worker" and agent.employment_type == "transport_worker":
                return True
        return False

    @staticmethod
    def _targeting_scale(agent: "HouseholdAgent") -> float:
        if agent.income_class == "low" or agent.employment_type == "transport_worker":
            return 1.0
        if agent.income_class == "middle":
            return 0.5
        return 0.0
