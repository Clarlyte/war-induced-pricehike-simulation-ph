"""Market environment.

Holds the system-level price drivers that every household reads each
month: the war-induced global oil shock, the pass-through to domestic
fuel, and category-level pass-through coefficients.

The values can be mutated at runtime (e.g., by Solara sliders) so the
dashboard can demonstrate policy/shock scenarios live.
"""

from __future__ import annotations

from dataclasses import dataclass

from pricehike_abm.config import Parameters


@dataclass
class MarketEnvironment:
    """Mutable container for the system-level economic environment.

    Attributes:
        oil_shock_pct: Global oil price change in percent (e.g. 40 -> +40%).
        fuel_pass_through: Fraction of global shock reaching domestic pumps.
        food_pass_through: Coefficient applied to domestic fuel multiplier
            when computing food price inflation.
        utilities_pass_through: Same for utilities.
        transport_pass_through: Same for transport fares.
    """

    oil_shock_pct: float = 0.0
    fuel_pass_through: float = 0.35
    food_pass_through: float = 0.25
    utilities_pass_through: float = 0.35
    transport_pass_through: float = 0.70

    @classmethod
    def from_params(cls, params: Parameters) -> "MarketEnvironment":
        return cls(
            oil_shock_pct=0.0,
            fuel_pass_through=params.fuel_pass_through,
            food_pass_through=params.food_pass_through,
            utilities_pass_through=params.utilities_pass_through,
            transport_pass_through=params.transport_pass_through,
        )

    @property
    def domestic_fuel_multiplier(self) -> float:
        """Multiplier applied to baseline domestic fuel price.

        domestic = 1 + oil_shock_pct/100 * fuel_pass_through
        """
        return 1.0 + (self.oil_shock_pct / 100.0) * self.fuel_pass_through

    def update(
        self,
        oil_shock_pct: float | None = None,
        fuel_pass_through: float | None = None,
        food_pass_through: float | None = None,
        utilities_pass_through: float | None = None,
        transport_pass_through: float | None = None,
    ) -> None:
        """Mutate slider-controlled fields in place (any provided values)."""
        if oil_shock_pct is not None:
            self.oil_shock_pct = float(oil_shock_pct)
        if fuel_pass_through is not None:
            self.fuel_pass_through = float(fuel_pass_through)
        if food_pass_through is not None:
            self.food_pass_through = float(food_pass_through)
        if utilities_pass_through is not None:
            self.utilities_pass_through = float(utilities_pass_through)
        if transport_pass_through is not None:
            self.transport_pass_through = float(transport_pass_through)
