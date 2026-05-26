"""Patch grid renderer using Plotly.

Renders the rural/urban backdrop and the agent houses as a single
heatmap-plus-scatter Plotly figure suitable for embedding in a Solara
component and refreshing every simulation tick.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

import plotly.graph_objects as go

from pricehike_abm.viz.colors import PATCH_COLORS, gradient_color

if TYPE_CHECKING:
    from pricehike_abm.model import PriceHikeModel


def build_grid_figure(model: "PriceHikeModel") -> go.Figure:
    """Build a Plotly figure showing patches and agent houses."""
    width = model.patches.width
    height = model.patches.height

    patch_matrix = [[0] * width for _ in range(height)]
    for (x, y), t in model.patches.patch_types.items():
        patch_matrix[y][x] = 0 if t == "urban" else 1

    xs: list[float] = []
    ys: list[float] = []
    colors: list[str] = []
    hovers: list[str] = []
    for agent in model.agents:
        pos = getattr(agent, "pos", None)
        if pos is None:
            continue
        x, y = pos
        xs.append(x)
        ys.append(y)
        colors.append(gradient_color(agent.snapshot.class_progress))
        hovers.append(
            f"#{agent.unique_id} | {agent.income_class}/{agent.location}<br>"
            f"effective: {agent.snapshot.effective_class}<br>"
            f"buying power: PHP {agent.snapshot.buying_power:,.0f}<br>"
            f"ratio: {agent.snapshot.buying_power_ratio:.2f}<br>"
            f"vehicle: {agent.snapshot.effective_vehicle_type} | "
            f"stress months: {agent.snapshot.months_under_stress}"
        )

    patch_layer = go.Heatmap(
        z=patch_matrix,
        x=list(range(width)),
        y=list(range(height)),
        colorscale=[[0.0, PATCH_COLORS["urban"]], [1.0, PATCH_COLORS["rural"]]],
        showscale=False,
        hoverinfo="skip",
        zmin=0,
        zmax=1,
    )

    house_layer = go.Scatter(
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

    fig = go.Figure(data=[patch_layer, house_layer])
    fig.update_layout(
        title=(
            f"Step {model.steps} | target shock={model.environment.oil_shock_pct:.0f}% | "
            f"effective={model.shock_dynamics.effective_shock_pct:.0f}% | gov={model.policy.level}"
        ),
        xaxis=dict(visible=False, range=[-1, width]),
        yaxis=dict(visible=False, range=[-1, height], scaleanchor="x", scaleratio=1),
        margin=dict(l=10, r=10, t=40, b=10),
        height=520,
        plot_bgcolor="white",
    )
    return fig
