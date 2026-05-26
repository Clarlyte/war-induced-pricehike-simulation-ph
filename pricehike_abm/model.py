"""PriceHikeModel.

The Mesa Model that ties everything together:
    - loads RRL-backed parameters,
    - spawns household agents from the synthetic profile CSV,
    - places them on the rural/urban patch grid,
    - exposes a mutable MarketEnvironment and GovernmentPolicy for the
      dashboard sliders,
    - collects per-step metrics for live charts and offline analysis.

One step == one simulated month. The default activation is simultaneous
(`AgentSet.do("step")`), so every household reacts to the same monthly
prices in lock-step, which is standard for monthly economic ABMs.
"""

from __future__ import annotations

import csv
from pathlib import Path
from typing import Iterable

import mesa
from mesa.datacollection import DataCollector

from pricehike_abm.agents.household import HouseholdAgent
from pricehike_abm.config import Parameters
from pricehike_abm.environment.market import MarketEnvironment
from pricehike_abm.environment.patches import PatchGrid
from pricehike_abm.metrics import AGENT_REPORTERS, MODEL_REPORTERS
from pricehike_abm.policies.government import GovernmentPolicy


DEFAULT_PROFILES_PATH = Path(__file__).resolve().parent.parent / "data" / "household_profiles.csv"


class PriceHikeModel(mesa.Model):
    """Top-level ABM driving the war-induced fuel shock simulation."""

    def __init__(
        self,
        oil_shock_pct: float = 0.0,
        gov_response_level: int = 0,
        fuel_pass_through: float | None = None,
        food_pass_through: float | None = None,
        utilities_pass_through: float | None = None,
        transport_pass_through: float | None = None,
        params: Parameters | None = None,
        profiles_path: Path | str | None = None,
        seed: int | None = None,
    ) -> None:
        self.params: Parameters = params or Parameters.load()
        super().__init__(rng=seed if seed is not None else self.params.seed)

        self.environment: MarketEnvironment = MarketEnvironment.from_params(self.params)
        self.environment.update(
            oil_shock_pct=oil_shock_pct,
            fuel_pass_through=fuel_pass_through,
            food_pass_through=food_pass_through,
            utilities_pass_through=utilities_pass_through,
            transport_pass_through=transport_pass_through,
        )

        self.policy: GovernmentPolicy = GovernmentPolicy(level=gov_response_level)

        self.patches: PatchGrid = PatchGrid(
            width=self.params.grid_width,
            height=self.params.grid_height,
            urban_core_radius=self.params.urban_core_radius,
        )

        profiles = self._load_profiles(profiles_path or DEFAULT_PROFILES_PATH)
        self._spawn_agents(profiles)

        self.datacollector: DataCollector = DataCollector(
            model_reporters=MODEL_REPORTERS,
            agent_reporters=AGENT_REPORTERS,
        )

        self._stress_history: list[float] = []
        self.datacollector.collect(self)

    # ------------------------------------------------------------------
    # Setup
    # ------------------------------------------------------------------
    def _load_profiles(self, path: Path | str) -> list[dict]:
        p = Path(path)
        with p.open("r", encoding="utf-8") as fh:
            reader = csv.DictReader(fh)
            return list(reader)

    def _spawn_agents(self, profiles: Iterable[dict]) -> None:
        urban_cells = list(self.patches.cells_of_type("urban"))
        rural_cells = list(self.patches.cells_of_type("rural"))
        self.random.shuffle(urban_cells)
        self.random.shuffle(rural_cells)
        u_idx = r_idx = 0

        for row in profiles:
            agent = HouseholdAgent(
                model=self,
                income_class=row["income_class"],
                monthly_income_php=float(row["monthly_income_php"]),
                location=row["location"],
                employment_type=row["employment_type"],
                vehicle_type=row["vehicle_type"],
                savings_buffer=row["savings_buffer"],
                household_size=int(row["household_size"]),
                gov_support_eligible=bool(int(row["gov_support_eligible"])),
            )
            if row["location"] == "urban":
                if u_idx >= len(urban_cells):
                    self.random.shuffle(urban_cells)
                    u_idx = 0
                pos = urban_cells[u_idx]
                u_idx += 1
            else:
                if r_idx >= len(rural_cells):
                    self.random.shuffle(rural_cells)
                    r_idx = 0
                pos = rural_cells[r_idx]
                r_idx += 1
            self.patches.grid.place_agent(agent, pos)

    # ------------------------------------------------------------------
    # Step
    # ------------------------------------------------------------------
    def step(self) -> None:  # noqa: D401 - Mesa hook
        self.agents.do("step")
        self.datacollector.collect(self)

    # ------------------------------------------------------------------
    # Dashboard / experiment helpers
    # ------------------------------------------------------------------
    def apply_controls(
        self,
        oil_shock_pct: float | None = None,
        gov_response_level: int | None = None,
        fuel_pass_through: float | None = None,
        food_pass_through: float | None = None,
        utilities_pass_through: float | None = None,
        transport_pass_through: float | None = None,
    ) -> None:
        """Update sliders/dropdowns from the dashboard without restarting."""
        self.environment.update(
            oil_shock_pct=oil_shock_pct,
            fuel_pass_through=fuel_pass_through,
            food_pass_through=food_pass_through,
            utilities_pass_through=utilities_pass_through,
            transport_pass_through=transport_pass_through,
        )
        if gov_response_level is not None:
            self.policy.set_level(int(gov_response_level))

    def run(self, months: int | None = None) -> None:
        steps = months if months is not None else self.params.default_months
        for _ in range(steps):
            self.step()
