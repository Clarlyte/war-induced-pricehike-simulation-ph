"""Rural / urban patch grid.

A `PatchGrid` wraps a Mesa MultiGrid and labels every cell as either
`urban` or `rural`. Households are placed on cells matching their
declared location attribute, so the visualisation can show two distinct
zones in a single map.

Layout rule
    - Cells within `urban_core_radius` of the grid centre are urban.
    - All other cells are rural.
    This produces a compact urban core surrounded by rural periphery
    that reads naturally in the dashboard.
"""

from __future__ import annotations

from dataclasses import dataclass, field

import mesa


@dataclass
class PatchGrid:
    """Spatial layer of the model."""

    width: int
    height: int
    urban_core_radius: int
    grid: mesa.space.MultiGrid = field(init=False)
    patch_types: dict[tuple[int, int], str] = field(init=False)

    def __post_init__(self) -> None:
        self.grid = mesa.space.MultiGrid(self.width, self.height, torus=False)
        cx, cy = self.width // 2, self.height // 2
        self.patch_types = {}
        for x in range(self.width):
            for y in range(self.height):
                if abs(x - cx) <= self.urban_core_radius and abs(y - cy) <= self.urban_core_radius:
                    self.patch_types[(x, y)] = "urban"
                else:
                    self.patch_types[(x, y)] = "rural"

    def cells_of_type(self, patch_type: str) -> list[tuple[int, int]]:
        return [pos for pos, t in self.patch_types.items() if t == patch_type]

    def patch_type(self, pos: tuple[int, int]) -> str:
        return self.patch_types[pos]
