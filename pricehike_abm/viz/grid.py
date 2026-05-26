"""Patch grid renderer using Plotly.

Renders the rural/urban backdrop as static layout shapes and agent houses
as a single scatter trace. The patch layer is cached so live dashboard
updates only mutate household marker colors and hover text.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

import plotly.graph_objects as go

from pricehike_abm.viz.colors import PATCH_COLORS, gradient_color

if TYPE_CHECKING:
    from pricehike_abm.model import PriceHikeModel

_PATCH_SHAPE_CACHE: dict[tuple[int, int, int], list[dict]] = {}


def build_patch_shapes(
    width: int,
    height: int,
    patch_types: dict[tuple[int, int], str],
) -> list[dict]:
    """Return Plotly layout shape dicts for each rural/urban cell."""
    shapes: list[dict] = []
    for x in range(width):
        for y in range(height):
            patch_type = patch_types.get((x, y), "rural")
            shapes.append(
                dict(
                    type="rect",
                    x0=x - 0.5,
                    x1=x + 0.5,
                    y0=y - 0.5,
                    y1=y + 0.5,
                    fillcolor=PATCH_COLORS[patch_type],
                    line=dict(width=0),
                    layer="below",
                )
            )
    return shapes


def get_cached_patch_shapes(model: "PriceHikeModel") -> list[dict]:
    """Return cached patch shapes for the model grid dimensions."""
    key = (
        model.patches.width,
        model.patches.height,
        model.params.urban_core_radius,
    )
    if key not in _PATCH_SHAPE_CACHE:
        _PATCH_SHAPE_CACHE[key] = build_patch_shapes(
            model.patches.width,
            model.patches.height,
            model.patches.patch_types,
        )
    return _PATCH_SHAPE_CACHE[key]


def extract_household_trace_data(
    model: "PriceHikeModel",
) -> tuple[list[float], list[float], list[str], list[str]]:
    """Extract scatter coordinates, colors, and hover text for all agents."""
    xs: list[float] = []
    ys: list[float] = []
    colors: list[str] = []
    hovers: list[str] = []
    for agent in model.agents:
        pos = getattr(agent, "pos", None)
        if pos is None:
            continue
        x, y = pos
        xs.append(float(x))
        ys.append(float(y))
        colors.append(gradient_color(agent.snapshot.class_progress))
        hovers.append(
            f"#{agent.unique_id} | {agent.income_class}/{agent.location}<br>"
            f"effective: {agent.snapshot.effective_class}<br>"
            f"buying power: PHP {agent.snapshot.buying_power:,.0f}<br>"
            f"ratio: {agent.snapshot.buying_power_ratio:.2f}<br>"
            f"vehicle: {agent.snapshot.effective_vehicle_type} | "
            f"stress months: {agent.snapshot.months_under_stress}"
        )
    return xs, ys, colors, hovers


def grid_layout(model: "PriceHikeModel") -> dict:
    """Shared layout dict for grid figures (live and static export)."""
    width = model.patches.width
    height = model.patches.height
    return dict(
        title="Household map",
        uirevision="grid",
        shapes=get_cached_patch_shapes(model),
        xaxis=dict(visible=False, range=[-1, width], fixedrange=True),
        yaxis=dict(
            visible=False,
            range=[-1, height],
            scaleanchor="x",
            scaleratio=1,
            fixedrange=True,
        ),
        margin=dict(l=10, r=10, t=40, b=10),
        height=520,
        plot_bgcolor="white",
        hovermode="closest",
    )


def build_household_scatter(
    xs: list[float],
    ys: list[float],
    colors: list[str],
    hovers: list[str],
) -> go.Scatter:
    """Build the household scatter trace with a stable uid."""
    return go.Scatter(
        uid="households",
        x=xs,
        y=ys,
        mode="markers",
        marker=dict(
            size=14,
            color=colors,
            symbol="square",
            line=dict(width=1, color="#222"),
        ),
        text=hovers,
        hoverinfo="text",
        name="Households",
    )


def create_grid_figure_widget(model: "PriceHikeModel") -> go.FigureWidget:
    """Create a FigureWidget for the live dashboard grid."""
    xs, ys, colors, hovers = extract_household_trace_data(model)
    fig = go.FigureWidget(
        data=[build_household_scatter(xs, ys, colors, hovers)],
        layout=grid_layout(model),
    )
    return fig


def update_grid_figure_widget(fig: go.FigureWidget, model: "PriceHikeModel") -> None:
    """Update household colors and hover text in place."""
    _, _, colors, hovers = extract_household_trace_data(model)
    fig.data[0].marker.color = colors
    fig.data[0].text = hovers


def build_grid_figure(model: "PriceHikeModel") -> go.Figure:
    """Build a static Plotly figure showing patches and agent houses."""
    xs, ys, colors, hovers = extract_household_trace_data(model)
    fig = go.Figure(data=[build_household_scatter(xs, ys, colors, hovers)])
    fig.update_layout(**grid_layout(model))
    return fig
