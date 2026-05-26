"""Government policy module.

Three response levels from the proposal (Section 4.2):
    0 - No response (baseline / counterfactual)
    1 - Moderate: targeted income transfer + partial fuel subsidy for
        low-income and transport workers
    2 - Strong: broader targeted transfer + larger fuel subsidy that
        still concentrates on vulnerable groups (PIDS 2026 warns that
        blanket subsidies disproportionately benefit higher-income
        households).

Returns a per-agent effect dict so the HouseholdAgent can apply it
inside its step() without needing to know any policy internals.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, Any

from pricehike_abm.config import Parameters
from pricehike_abm.environment.market import MarketEnvironment

if TYPE_CHECKING:
    from pricehike_abm.agents.household import HouseholdAgent


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
    ) -> dict[str, float]:
        """Resolve the per-agent income boost and fuel subsidy in PHP.

        Returns:
            {
                "income_boost": PHP added to effective income this step,
                "fuel_subsidy_pct": fraction (0..1) deducted from transport
                                    + private fuel spending.
            }
        """
        no_effect = {"income_boost": 0.0, "fuel_subsidy_pct": 0.0}
        if self.level == 0 or env.oil_shock_pct <= 0:
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
        """Per-agent support intensity.

        Low-income and transport workers receive full support, middle-income
        receives partial. This mirrors PIDS 2026's warning that blanket
        subsidies disproportionately benefit higher-income households.
        """
        if agent.income_class == "low" or agent.employment_type == "transport_worker":
            return 1.0
        if agent.income_class == "middle":
            return 0.5
        return 0.0
