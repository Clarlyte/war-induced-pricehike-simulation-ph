"""Philippine fuel-shock agent-based model.

Top-level package. Submodules are added in subsequent commits:
    agents.household     - HouseholdAgent
    environment.market   - Pass-through engine and cost-of-living index
    environment.patches  - Rural/urban grid
    policies.government  - Government response levels
    model                - PriceHikeModel
    metrics              - DataCollector reporters
    viz.grid             - Patch and house rendering
    viz.charts           - Live chart components
    app                  - Solara dashboard entry point
"""

__version__ = "0.1.0"
