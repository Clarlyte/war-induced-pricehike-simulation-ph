"""Live chart components.

Each function returns a Plotly figure with stable trace uids and a fixed
trace count so the dashboard can update figures in place without remounting
widgets or desyncing hover callbacks.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Callable

import pandas as pd
import plotly.graph_objects as go

from pricehike_abm.viz.colors import CLASS_COLORS

if TYPE_CHECKING:
    from pricehike_abm.model import PriceHikeModel

EMPTY_ANNOTATION = dict(
    text="(Step the simulation to populate.)",
    showarrow=False,
    x=0.5,
    y=0.5,
    xref="paper",
    yref="paper",
)


def _model_df(model: "PriceHikeModel") -> pd.DataFrame:
    return model.datacollector.get_model_vars_dataframe()


def _base_layout(title: str, **extra) -> dict:
    layout = dict(
        title=title,
        uirevision="charts",
        height=260,
        margin=dict(l=30, r=10, t=40, b=30),
        hovermode="x unified",
    )
    layout.update(extra)
    return layout


def _empty_annotation() -> list[dict]:
    return [EMPTY_ANNOTATION.copy()]


def _scatter_trace(
    uid: str,
    name: str,
    x: list | pd.Series,
    y: list | pd.Series,
    *,
    color: str,
    visible: bool = True,
    **kwargs,
) -> go.Scatter:
    return go.Scatter(
        uid=uid,
        x=list(x),
        y=list(y),
        name=name,
        visible=visible,
        line=dict(color=color),
        **kwargs,
    )


def class_count_chart(model: "PriceHikeModel") -> go.Figure:
    df = _model_df(model)
    has_data = not df.empty
    months = df["step"] if has_data else []
    fig = go.Figure(
        data=[
            _scatter_trace(
                "class_high", "High", months,
                df["count_high"] if has_data else [],
                color=CLASS_COLORS["high"],
                visible=has_data,
                stackgroup="one",
            ),
            _scatter_trace(
                "class_middle", "Middle", months,
                df["count_middle"] if has_data else [],
                color=CLASS_COLORS["middle"],
                visible=has_data,
                stackgroup="one",
            ),
            _scatter_trace(
                "class_low", "Low", months,
                df["count_low"] if has_data else [],
                color=CLASS_COLORS["low"],
                visible=has_data,
                stackgroup="one",
            ),
        ]
    )
    fig.update_layout(
        **_base_layout(
            "Effective class population (stacked)",
            xaxis_title="Month",
            yaxis_title="Households",
            legend=dict(orientation="h", y=-0.25),
            annotations=_empty_annotation() if not has_data else [],
        )
    )
    return fig


def col_index_chart(model: "PriceHikeModel") -> go.Figure:
    df = _model_df(model)
    has_data = not df.empty
    months = df["step"] if has_data else []
    baseline_x = list(months) if has_data else []
    baseline_y = [100.0] * len(baseline_x) if has_data else []
    fig = go.Figure(
        data=[
            go.Scatter(
                uid="col_index",
                x=list(months),
                y=list(df["col_index"]) if has_data else [],
                mode="lines+markers",
                name="COL index",
                visible=has_data,
                line=dict(color="#1f77b4", width=3),
            ),
            go.Scatter(
                uid="baseline_100",
                x=baseline_x,
                y=baseline_y,
                mode="lines",
                name="baseline=100",
                visible=has_data,
                line=dict(color="#888", width=1, dash="dash"),
                hoverinfo="skip",
            ),
        ]
    )
    fig.update_layout(
        **_base_layout(
            "Cost-of-living index over time",
            xaxis_title="Month",
            yaxis_title="Index (100 = baseline)",
            annotations=_empty_annotation() if not has_data else [],
        )
    )
    return fig


def buying_power_chart(model: "PriceHikeModel") -> go.Figure:
    df = _model_df(model)
    has_data = not df.empty
    months = df["step"] if has_data else []
    fig = go.Figure(
        data=[
            _scatter_trace(
                "bp_high", "High income", months,
                df["buying_power_high"] if has_data else [],
                color=CLASS_COLORS["high"],
                visible=has_data,
            ),
            _scatter_trace(
                "bp_middle", "Middle income", months,
                df["buying_power_middle"] if has_data else [],
                color=CLASS_COLORS["middle"],
                visible=has_data,
            ),
            _scatter_trace(
                "bp_low", "Low income", months,
                df["buying_power_low"] if has_data else [],
                color=CLASS_COLORS["low"],
                visible=has_data,
            ),
        ]
    )
    fig.update_layout(
        **_base_layout(
            "Mean buying power by income class (PHP)",
            xaxis_title="Month",
            yaxis_title="PHP / month",
            legend=dict(orientation="h", y=-0.25),
            annotations=_empty_annotation() if not has_data else [],
        )
    )
    return fig


def stress_chart(model: "PriceHikeModel") -> go.Figure:
    df = _model_df(model)
    has_data = not df.empty
    months = df["step"] if has_data else []
    fig = go.Figure(
        data=[
            _scatter_trace(
                "stress_food", "Food at risk %", months,
                (df["food_at_risk_share"] * 100) if has_data else [],
                color="#d62728",
                visible=has_data,
            ),
            _scatter_trace(
                "stress_bill", "Bill stress %", months,
                (df["bill_stress_share"] * 100) if has_data else [],
                color="#9467bd",
                visible=has_data,
            ),
        ]
    )
    fig.update_layout(
        **_base_layout(
            "Household stress indicators",
            xaxis_title="Month",
            yaxis_title="Share of households (%)",
            legend=dict(orientation="h", y=-0.25),
            annotations=_empty_annotation() if not has_data else [],
        )
    )
    return fig


def rural_vs_urban_chart(model: "PriceHikeModel") -> go.Figure:
    df = _model_df(model)
    has_data = not df.empty
    months = df["step"] if has_data else []
    fig = go.Figure(
        data=[
            _scatter_trace(
                "bp_rural", "Rural", months,
                df["buying_power_rural"] if has_data else [],
                color="#8c5e2a",
                visible=has_data,
            ),
            _scatter_trace(
                "bp_urban", "Urban", months,
                df["buying_power_urban"] if has_data else [],
                color="#5b9bd5",
                visible=has_data,
            ),
        ]
    )
    fig.update_layout(
        **_base_layout(
            "Rural vs urban mean buying power",
            xaxis_title="Month",
            yaxis_title="PHP / month",
            legend=dict(orientation="h", y=-0.25),
            annotations=_empty_annotation() if not has_data else [],
        )
    )
    return fig


ChartBuilder = Callable[["PriceHikeModel"], go.Figure]

CHART_BUILDERS: dict[str, ChartBuilder] = {
    "class_count": class_count_chart,
    "col_index": col_index_chart,
    "buying_power": buying_power_chart,
    "stress": stress_chart,
    "rural_vs_urban": rural_vs_urban_chart,
}
