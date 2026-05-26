"""Solara components for in-place Plotly figure updates.

Holds persistent FigureWidget instances and patches trace data on each tick
instead of remounting new go.Figure objects, which eliminates dashboard flicker
and Plotly hover trace-index desync errors.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Callable

import plotly.graph_objects as go
import solara

from pricehike_abm.viz.charts import ChartBuilder
from pricehike_abm.viz.grid import (
    create_grid_figure_widget,
    update_grid_figure_widget,
)

if TYPE_CHECKING:
    from pricehike_abm.model import PriceHikeModel

FIGURE_CONFIG: dict = {"displayModeBar": False}


def _apply_figure_config(fig: go.FigureWidget) -> go.FigureWidget:
    """Hide the Plotly mode bar (Solara FigurePlotly has no config kwarg)."""
    fig._config = FIGURE_CONFIG  # noqa: SLF001 — plotly widget display config
    return fig


def _sync_traces_by_uid(widget: go.FigureWidget, source: go.Figure) -> None:
    """Copy trace arrays from source into widget traces matched by uid."""
    source_by_uid = {trace.uid: trace for trace in source.data if trace.uid}
    for trace in widget.data:
        src = source_by_uid.get(trace.uid)
        if src is None:
            continue
        trace.update(
            x=src.x,
            y=src.y,
            visible=src.visible,
            mode=getattr(src, "mode", trace.mode),
            text=getattr(src, "text", None),
            hoverinfo=getattr(src, "hoverinfo", None),
        )
        if hasattr(src, "marker") and src.marker:
            marker_update = {}
            if src.marker.color is not None:
                marker_update["color"] = src.marker.color
            if src.marker.size is not None:
                marker_update["size"] = src.marker.size
            if marker_update:
                trace.marker.update(marker_update)
        if hasattr(src, "line") and src.line:
            line_update = {}
            if src.line.color is not None:
                line_update["color"] = src.line.color
            if src.line.width is not None:
                line_update["width"] = src.line.width
            if src.line.dash is not None:
                line_update["dash"] = src.line.dash
            if line_update:
                trace.line.update(line_update)

    widget.layout.annotations = source.layout.annotations


def _make_chart_widget(build_fn: ChartBuilder, model: "PriceHikeModel") -> go.FigureWidget:
    source = build_fn(model)
    return _apply_figure_config(go.FigureWidget(data=source.data, layout=source.layout))


def _update_chart_widget(
    widget: go.FigureWidget,
    build_fn: ChartBuilder,
    model: "PriceHikeModel",
) -> None:
    source = build_fn(model)
    _sync_traces_by_uid(widget, source)


@solara.component
def LiveGridFigure(
    model: "PriceHikeModel",
    tick: int,
    reset_token: int,
) -> None:
    del tick  # dependency only; model state read on each render
    fig_ref = solara.use_ref(None)
    token_ref = solara.use_ref(-1)

    if token_ref.current != reset_token or fig_ref.current is None:
        fig_ref.current = _apply_figure_config(create_grid_figure_widget(model))
        token_ref.current = reset_token
    else:
        update_grid_figure_widget(fig_ref.current, model)

    solara.FigurePlotly(fig_ref.current)


@solara.component
def LiveChartFigure(
    build_fn: ChartBuilder,
    model: "PriceHikeModel",
    tick: int,
    reset_token: int,
) -> None:
    del tick
    fig_ref = solara.use_ref(None)
    token_ref = solara.use_ref(-1)

    if token_ref.current != reset_token or fig_ref.current is None:
        fig_ref.current = _make_chart_widget(build_fn, model)
        token_ref.current = reset_token
    else:
        _update_chart_widget(fig_ref.current, build_fn, model)

    solara.FigurePlotly(fig_ref.current)
