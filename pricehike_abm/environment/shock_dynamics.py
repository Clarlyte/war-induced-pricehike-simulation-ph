"""Time-varying shock dynamics.

Manages the ramp from slider target to effective oil shock, maintains
shock history for lagged pass-through, and tracks how long a shock has
been active (for persistence effects on food prices).
"""

from __future__ import annotations

from collections import deque
from dataclasses import dataclass, field
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from pricehike_abm.config import Parameters
    from pricehike_abm.environment.market import MarketEnvironment


@dataclass
class ShockDynamics:
    """Stateful layer between dashboard sliders and agent price reads."""

    target_shock_pct: float = 0.0
    effective_shock_pct: float = 0.0
    shock_history: deque[float] = field(default_factory=lambda: deque(maxlen=10))
    months_shock_active: int = 0

    @classmethod
    def create(cls, target_shock_pct: float = 0.0, max_lag: int = 2) -> "ShockDynamics":
        return cls(
            target_shock_pct=float(target_shock_pct),
            effective_shock_pct=0.0,
            shock_history=deque([0.0], maxlen=max_lag + 2),
            months_shock_active=0,
        )

    def set_target(self, shock_pct: float) -> None:
        self.target_shock_pct = float(shock_pct)

    def advance(self, params: "Parameters") -> None:
        """Ramp effective shock toward target and update history."""
        ramp = params.shock_ramp_pct_per_month
        if self.effective_shock_pct < self.target_shock_pct:
            self.effective_shock_pct = min(
                self.target_shock_pct,
                self.effective_shock_pct + ramp,
            )
        elif self.effective_shock_pct > self.target_shock_pct:
            self.effective_shock_pct = max(
                self.target_shock_pct,
                self.effective_shock_pct - ramp,
            )

        self.shock_history.append(self.effective_shock_pct)

        if self.effective_shock_pct > 0:
            self.months_shock_active += 1
        else:
            self.months_shock_active = 0

    def effective_fuel_multiplier(self, params: "Parameters", market: "MarketEnvironment") -> float:
        return 1.0 + (self.effective_shock_pct / 100.0) * market.fuel_pass_through

    def _lagged_shock_pct(self, lag_months: int) -> float:
        if not self.shock_history:
            return 0.0
        idx = -(lag_months + 1)
        if abs(idx) > len(self.shock_history):
            return self.shock_history[0]
        return float(self.shock_history[idx])

    def category_fuel_delta(
        self,
        category: str,
        params: "Parameters",
        market: "MarketEnvironment",
    ) -> float:
        """Lagged domestic fuel-price delta for a spending category.

        Returns the fractional increase above baseline (e.g. 0.14 means +14%).
        """
        lag = params.pass_through_lag(category)
        lagged_shock = self._lagged_shock_pct(lag)
        delta = (lagged_shock / 100.0) * market.fuel_pass_through

        if (
            category == "food"
            and self.months_shock_active >= params.persistence_shock_months_threshold
        ):
            delta *= params.persistence_food_pass_through_boost

        return delta

    def reset(self, target_shock_pct: float = 0.0, max_lag: int = 2) -> None:
        """Clear state (dashboard Reset)."""
        self.target_shock_pct = float(target_shock_pct)
        self.effective_shock_pct = 0.0
        self.shock_history = deque([0.0], maxlen=max_lag + 2)
        self.months_shock_active = 0
