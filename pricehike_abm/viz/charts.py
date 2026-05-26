"""Live chart components.

Each function returns a Plotly figure built from the model's
DataCollector history. Charts are intentionally lightweight and stateless
so the dashboard can rebuild them on every tick.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

import pandas as pd
import plotly.graph_objects as go

from pricehike_abm.viz.colors import CLASS_COLORS

if TYPE_CHECKING:
    from pricehike_abm.model import PriceHikeModel


def _model_df(model: "PriceHikeModel") -> pd.DataFrame:
    return model.datacollector.get_model_vars_dataframe()


def class_count_chart(model: "PriceHikeModel") -> go.Figure:
    df = _model_df(model)
    fig = go.Figure()
    if df.empty:
        return _empty("Effective class population over time")
    months = df["step"]
    fig.add_trace(go.Scatter(x=months, y=df["count_high"], name="High",
                             stackgroup="one", line=dict(color=CLASS_COLORS["high"])))
    fig.add_trace(go.Scatter(x=months, y=df["count_middle"], name="Middle",
                             stackgroup="one", line=dict(color=CLASS_COLORS["middle"])))
    fig.add_trace(go.Scatter(x=months, y=df["count_low"], name="Low",
                             stackgroup="one", line=dict(color=CLASS_COLORS["low"])))
    fig.update_layout(
        title="Effective class population (stacked)",
        xaxis_title="Month",
        yaxis_title="Households",
        height=260,
        margin=dict(l=30, r=10, t=40, b=30),
        legend=dict(orientation="h", y=-0.25),
    )
    return fig


def col_index_chart(model: "PriceHikeModel") -> go.Figure:
    df = _model_df(model)
    fig = go.Figure()
    if df.empty:
        return _empty("Cost-of-living index")
    fig.add_trace(go.Scatter(
        x=df["step"], y=df["col_index"],
        mode="lines+markers", name="COL index",
        line=dict(color="#1f77b4", width=3),
    ))
    fig.add_hline(y=100, line_dash="dash", line_color="#888",
                  annotation_text="baseline=100")
    fig.update_layout(
        title="Cost-of-living index over time",
        xaxis_title="Month",
        yaxis_title="Index (100 = baseline)",
        height=260,
        margin=dict(l=30, r=10, t=40, b=30),
    )
    return fig


def buying_power_chart(model: "PriceHikeModel") -> go.Figure:
    df = _model_df(model)
    fig = go.Figure()
    if df.empty:
        return _empty("Mean buying power by income class")
    fig.add_trace(go.Scatter(x=df["step"], y=df["buying_power_high"],
                             name="High income", line=dict(color=CLASS_COLORS["high"])))
    fig.add_trace(go.Scatter(x=df["step"], y=df["buying_power_middle"],
                             name="Middle income", line=dict(color=CLASS_COLORS["middle"])))
    fig.add_trace(go.Scatter(x=df["step"], y=df["buying_power_low"],
                             name="Low income", line=dict(color=CLASS_COLORS["low"])))
    fig.update_layout(
        title="Mean buying power by income class (PHP)",
        xaxis_title="Month",
        yaxis_title="PHP / month",
        height=260,
        margin=dict(l=30, r=10, t=40, b=30),
        legend=dict(orientation="h", y=-0.25),
    )
    return fig


def stress_chart(model: "PriceHikeModel") -> go.Figure:
    df = _model_df(model)
    fig = go.Figure()
    if df.empty:
        return _empty("Stress indicators")
    fig.add_trace(go.Scatter(x=df["step"], y=df["food_at_risk_share"] * 100,
                             name="Food at risk %", line=dict(color="#d62728")))
    fig.add_trace(go.Scatter(x=df["step"], y=df["bill_stress_share"] * 100,
                             name="Bill stress %", line=dict(color="#9467bd")))
    fig.update_layout(
        title="Household stress indicators",
        xaxis_title="Month",
        yaxis_title="Share of households (%)",
        height=260,
        margin=dict(l=30, r=10, t=40, b=30),
        legend=dict(orientation="h", y=-0.25),
    )
    return fig


def rural_vs_urban_chart(model: "PriceHikeModel") -> go.Figure:
    df = _model_df(model)
    fig = go.Figure()
    if df.empty:
        return _empty("Rural vs urban buying power")
    fig.add_trace(go.Scatter(x=df["step"], y=df["buying_power_rural"],
                             name="Rural", line=dict(color="#8c5e2a")))
    fig.add_trace(go.Scatter(x=df["step"], y=df["buying_power_urban"],
                             name="Urban", line=dict(color="#5b9bd5")))
    fig.update_layout(
        title="Rural vs urban mean buying power",
        xaxis_title="Month",
        yaxis_title="PHP / month",
        height=260,
        margin=dict(l=30, r=10, t=40, b=30),
        legend=dict(orientation="h", y=-0.25),
    )
    return fig


def _empty(title: str) -> go.Figure:
    fig = go.Figure()
    fig.update_layout(
        title=title,
        height=260,
        margin=dict(l=30, r=10, t=40, b=30),
        annotations=[dict(text="(Step the simulation to populate.)",
                          showarrow=False, x=0.5, y=0.5, xref="paper", yref="paper")],
    )
    return fig
