"""NetLogo-style live dashboard for the PriceHike ABM.

Run with:
    solara run pricehike_abm/app.py

The page is organised like NetLogo's Interface tab:
    - Top-left   : Controls (sliders, dropdown, speed, play/pause/step/reset)
    - Top-right  : Live monitors (step, COL, class counts, stress)
    - Middle     : World view (rural/urban patches with colour-graded houses)
    - Bottom     : Five live charts updating every tick
"""

from __future__ import annotations

import asyncio
import sys
from pathlib import Path

_PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))

import solara

from pricehike_abm.model import PriceHikeModel
from pricehike_abm.viz.charts import (
    buying_power_chart,
    class_count_chart,
    col_index_chart,
    rural_vs_urban_chart,
    stress_chart,
)
from pricehike_abm.viz.colors import CLASS_COLORS
from pricehike_abm.viz.live_plotly import LiveChartFigure, LiveGridFigure


def _new_model(
    oil_shock_pct: float,
    gov_response_level: int,
    fuel_pass_through: float,
    food_pass_through: float,
    utilities_pass_through: float,
    transport_pass_through: float,
) -> PriceHikeModel:
    return PriceHikeModel(
        oil_shock_pct=oil_shock_pct,
        gov_response_level=gov_response_level,
        fuel_pass_through=fuel_pass_through,
        food_pass_through=food_pass_through,
        utilities_pass_through=utilities_pass_through,
        transport_pass_through=transport_pass_through,
    )


oil_shock = solara.reactive(0.0)
gov_level = solara.reactive(0)
fuel_pt = solara.reactive(0.35)
food_pt = solara.reactive(0.25)
util_pt = solara.reactive(0.35)
trans_pt = solara.reactive(0.70)
speed_ticks_per_sec = solara.reactive(2.0)
playing = solara.reactive(False)
tick_counter = solara.reactive(0)
reset_token = solara.reactive(0)

_model_holder: dict[str, PriceHikeModel] = {
    "model": _new_model(0.0, 0, 0.35, 0.25, 0.35, 0.70)
}


def get_model() -> PriceHikeModel:
    return _model_holder["model"]


def reset_model() -> None:
    _model_holder["model"] = _new_model(
        oil_shock.value,
        gov_level.value,
        fuel_pt.value,
        food_pt.value,
        util_pt.value,
        trans_pt.value,
    )
    tick_counter.value = 0
    reset_token.value += 1


def push_controls() -> None:
    get_model().apply_controls(
        oil_shock_pct=oil_shock.value,
        gov_response_level=gov_level.value,
        fuel_pass_through=fuel_pt.value,
        food_pass_through=food_pt.value,
        utilities_pass_through=util_pt.value,
        transport_pass_through=trans_pt.value,
    )


def step_once() -> None:
    push_controls()
    get_model().step()
    tick_counter.value += 1


@solara.component
def Controls() -> None:
    solara.Markdown("### Controls")
    solara.SliderFloat(
        "Oil shock (%)", value=oil_shock, min=0, max=80, step=5,
        thumb_label="always",
    )
    solara.SliderFloat(
        "Fuel pass-through", value=fuel_pt, min=0.0, max=1.0, step=0.05,
        thumb_label="always",
    )
    solara.SliderFloat(
        "Food pass-through", value=food_pt, min=0.0, max=1.0, step=0.05,
        thumb_label="always",
    )
    solara.SliderFloat(
        "Utilities pass-through", value=util_pt, min=0.0, max=1.0, step=0.05,
        thumb_label="always",
    )
    solara.SliderFloat(
        "Transport pass-through", value=trans_pt, min=0.0, max=1.5, step=0.05,
        thumb_label="always",
    )
    solara.Select(
        "Government response",
        values=[0, 1, 2],
        value=gov_level,
    )
    solara.SliderFloat(
        "Speed (ticks / second)", value=speed_ticks_per_sec, min=0.5, max=10.0, step=0.5,
        thumb_label="always",
    )

    with solara.Row():
        solara.Button(
            "Play" if not playing.value else "Pause",
            color="primary" if not playing.value else "warning",
            on_click=lambda: playing.set(not playing.value),
        )
        solara.Button("Step", on_click=step_once)
        solara.Button("Reset", color="error", on_click=reset_model)


@solara.component
def Monitors() -> None:
    _ = tick_counter.value
    model = get_model()
    df = model.datacollector.get_model_vars_dataframe()
    last = df.iloc[-1] if not df.empty else None
    if last is None:
        return
    solara.Markdown("### Monitors")
    with solara.GridFixed(columns=2):
        solara.Markdown(f"**Step**: {int(last['step'])}")
        solara.Markdown(
            f"**Oil shock (target / effective)**: "
            f"{last['oil_shock_pct']:.0f}% / {last.get('effective_oil_shock_pct', last['oil_shock_pct']):.0f}%"
        )
        solara.Markdown(f"**Months under shock**: {int(last.get('months_shock_active', 0))}")
        solara.Markdown(f"**COL index**: {last['col_index']:.2f}")
        solara.Markdown(f"**Mean buying power**: PHP {last['mean_buying_power']:,.0f}")
        solara.Markdown(
            f"**High / Mid / Low**: "
            f"<span style='color:{CLASS_COLORS['high']}'>{int(last['count_high'])}</span> / "
            f"<span style='color:{CLASS_COLORS['middle']}'>{int(last['count_middle'])}</span> / "
            f"<span style='color:{CLASS_COLORS['low']}'>{int(last['count_low'])}</span>"
        )
        solara.Markdown(
            f"**Food at risk**: {last['food_at_risk_share'] * 100:.1f}% | "
            f"**Bill stress**: {last['bill_stress_share'] * 100:.1f}%"
        )
        solara.Markdown(f"**Rural buying power**: PHP {last['buying_power_rural']:,.0f}")
        solara.Markdown(f"**Urban buying power**: PHP {last['buying_power_urban']:,.0f}")
        solara.Markdown(
            f"**Transport erosion (mean)**: {last.get('mean_income_erosion_factor', 1.0):.2f} | "
            f"**Vehicle downgrades**: {int(last.get('vehicle_downgrade_count', 0))}"
        )


@solara.component
def WorldView() -> None:
    tick = tick_counter.value
    model = get_model()
    LiveGridFigure(model, tick, reset_token.value)


@solara.component
def Charts() -> None:
    tick = tick_counter.value
    model = get_model()
    token = reset_token.value
    with solara.GridFixed(columns=2):
        LiveChartFigure(class_count_chart, model, tick, token)
        LiveChartFigure(col_index_chart, model, tick, token)
        LiveChartFigure(buying_power_chart, model, tick, token)
        LiveChartFigure(stress_chart, model, tick, token)
    LiveChartFigure(rural_vs_urban_chart, model, tick, token)


@solara.component
def AutoTicker() -> None:
    async def loop() -> None:
        while True:
            if playing.value:
                step_once()
            interval = 1.0 / max(speed_ticks_per_sec.value, 0.1)
            await asyncio.sleep(interval)

    solara.lab.use_task(loop, dependencies=[])


@solara.component
def Page() -> None:
    solara.Title("PriceHike ABM | Philippines fuel-shock simulation")
    AutoTicker()
    with solara.Sidebar():
        Controls()
        solara.Markdown("---")
        Monitors()
        solara.Markdown(
            "---\n"
            "**Legend**\n"
            f"- <span style='color:{CLASS_COLORS['high']}'>Green</span>: high effective class\n"
            f"- <span style='color:{CLASS_COLORS['middle']}'>Orange</span>: middle\n"
            f"- <span style='color:{CLASS_COLORS['low']}'>Red</span>: low\n"
            "- Light gray patches = urban core; pale green = rural\n"
            "- Effective shock ramps toward slider target (~10%/month)"
        )
    with solara.Column():
        WorldView()
        solara.Markdown("### Live charts")
        Charts()
