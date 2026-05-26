"""Colour palette and gradient helpers.

The proposal specifies green / orange / red for high / middle / low
effective income classes. To make class transitions feel continuous in
the dashboard, agents store a `class_progress` value in 0..1 that we
linearly interpolate across this palette.
"""

from __future__ import annotations

CLASS_COLORS: dict[str, str] = {
    "high": "#2ca02c",
    "middle": "#ff9800",
    "low": "#d62728",
}

PATCH_COLORS: dict[str, str] = {
    "urban": "#e6e6e6",
    "rural": "#dff0d8",
}


def _hex_to_rgb(hex_color: str) -> tuple[int, int, int]:
    h = hex_color.lstrip("#")
    return tuple(int(h[i:i + 2], 16) for i in (0, 2, 4))  # type: ignore[return-value]


def _rgb_to_hex(rgb: tuple[float, float, float]) -> str:
    r, g, b = (max(0, min(255, int(round(c)))) for c in rgb)
    return f"#{r:02x}{g:02x}{b:02x}"


def gradient_color(class_progress: float) -> str:
    """Interpolate red -> orange -> green across 0..1.

    0.0 == pure red (low), 0.5 == pure orange (middle), 1.0 == pure
    green (high). Values outside [0, 1] are clamped.
    """
    p = max(0.0, min(1.0, class_progress))
    red = _hex_to_rgb(CLASS_COLORS["low"])
    orange = _hex_to_rgb(CLASS_COLORS["middle"])
    green = _hex_to_rgb(CLASS_COLORS["high"])
    if p < 0.5:
        t = p / 0.5
        rgb = tuple(red[i] + (orange[i] - red[i]) * t for i in range(3))
    else:
        t = (p - 0.5) / 0.5
        rgb = tuple(orange[i] + (green[i] - orange[i]) * t for i in range(3))
    return _rgb_to_hex(rgb)  # type: ignore[arg-type]
