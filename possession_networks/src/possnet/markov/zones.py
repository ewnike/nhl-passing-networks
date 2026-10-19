"""A regular grid over the canonical pitch (meters, center origin, attacking toward +x)."""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np

# Dimensions of the canonical surface (StatsBomb 120 x 80 yards, in meters).
PITCH_LENGTH_M = 120 * 0.9144
PITCH_WIDTH_M = 80 * 0.9144


@dataclass(frozen=True)
class ZoneGrid:
    """``nx`` columns along the attacking axis by ``ny`` rows across it.

    Zone index is ``ix * ny + iy`` with ``ix`` counted from the own goal line toward the
    attacked goal and ``iy`` from the acting team's right touchline to its left.
    """

    nx: int = 12
    ny: int = 8
    length: float = PITCH_LENGTH_M
    width: float = PITCH_WIDTH_M

    @property
    def n_zones(self) -> int:
        return self.nx * self.ny

    def zone_of(self, x, y) -> np.ndarray:
        """Zone index per point, -1 where a coordinate is missing. Points outside clip in."""
        x = np.asarray(x, dtype=float)
        y = np.asarray(y, dtype=float)
        ix = np.clip(np.floor((x + self.length / 2) / self.length * self.nx), 0, self.nx - 1)
        iy = np.clip(np.floor((y + self.width / 2) / self.width * self.ny), 0, self.ny - 1)
        zone = ix * self.ny + iy
        bad = np.isnan(x) | np.isnan(y)
        return np.where(bad, -1, np.nan_to_num(zone)).astype(int)

    def centers(self) -> np.ndarray:
        """(n_zones, 2) array of zone center coordinates in meters."""
        ix, iy = np.divmod(np.arange(self.n_zones), self.ny)
        cx = (ix + 0.5) * self.length / self.nx - self.length / 2
        cy = (iy + 0.5) * self.width / self.ny - self.width / 2
        return np.column_stack([cx, cy])

    def to_matrix(self, values: np.ndarray) -> np.ndarray:
        """Reshape per zone values to (ny, nx) with row 0 at the lowest y, for imshow."""
        return np.asarray(values).reshape(self.nx, self.ny).T
