"""Spatial binning — the n=7 problem and the privacy rule, in one place.

Two constraints meet here and happen to have the same solution.

*Modelling.* Cainta has seven barangays. Seven observations cannot support
supervised learning at the barangay level (plan §1), so spatial features are
computed on H3 resolution-9 cells (~0.1 km², roughly 430 over Cainta) rather
than on barangays. Barangay codes remain useful for labelling and joining to
LGU records; they are not a modelling unit.

*Privacy.* RA 10173 and Cainta Ordinance 2023-005 make a geotag personal data,
and a scan taken at home is a home address. Plan §7.5 is therefore absolute:
store the cell ID, never the raw coordinate. ``bin_point`` is the only function
that should ever see a precise latitude and longitude, and it does not return
one.

The ``h3`` package is optional. Without it, a documented equal-angle fallback
grid is used so the pipeline runs and the privacy guarantee still holds; the
cell IDs are prefixed ``sq9-`` so fallback bins can never be mistaken for real
H3 indexes in stored data.
"""

from __future__ import annotations

import math
from dataclasses import dataclass

try:  # pragma: no cover - exercised by whichever branch is installed
    import h3

    HAS_H3 = True
except ImportError:  # pragma: no cover
    h3 = None
    HAS_H3 = False

#: Plan §4.2 specifies H3 r9 for the spatial feature table.
DEFAULT_RESOLUTION = 9

#: Approximate Cainta envelope (S, W, N, E), matching scrapers/osm_overpass.py.
CAINTA_BBOX = (14.545, 121.085, 14.620, 121.145)

#: Fallback grid step in degrees, chosen so a cell is roughly the area of an
#: H3 r9 hex (~0.1 km²) at Cainta's latitude: ~0.003 deg ~= 330 m.
FALLBACK_STEP_DEG = 0.003


class CoordinateOutOfRange(ValueError):
    """Raised for a latitude/longitude that is not a real coordinate."""


@dataclass(frozen=True)
class Cell:
    """A spatial bin. Carries no precise coordinate, by construction."""

    cell_id: str
    resolution: int
    scheme: str

    @property
    def is_h3(self) -> bool:
        return self.scheme == "h3"


def bin_point(lat: float, lon: float, resolution: int = DEFAULT_RESOLUTION) -> Cell:
    """Reduce a precise coordinate to a spatial cell.

    This is the privacy boundary. Call it as early as possible -- ideally in
    the request handler that receives the scan -- and let nothing downstream
    keep the arguments.
    """
    if not -90.0 <= lat <= 90.0:
        raise CoordinateOutOfRange(f"latitude {lat} out of range")
    if not -180.0 <= lon <= 180.0:
        raise CoordinateOutOfRange(f"longitude {lon} out of range")

    if HAS_H3:
        return Cell(
            cell_id=h3.latlng_to_cell(lat, lon, resolution),
            resolution=resolution,
            scheme="h3",
        )

    row = math.floor(lat / FALLBACK_STEP_DEG)
    col = math.floor(lon / FALLBACK_STEP_DEG)
    return Cell(cell_id=f"sq{resolution}-{row}-{col}", resolution=resolution, scheme="square")


def in_cainta_bbox(lat: float, lon: float) -> bool:
    """Cheap envelope test.

    A bounding box is not a municipality: this envelope also covers parts of
    Pasig and Taytay. Use it to discard obviously irrelevant points, then
    point-in-polygon against the PSA boundary before telling a user that
    anything is "in Cainta".
    """
    south, west, north, east = CAINTA_BBOX
    return south <= lat <= north and west <= lon <= east


def haversine_m(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Great-circle distance in metres.

    Used for `distance_to_nearest_junkshop_m` and friends. Straight-line, not
    walking distance -- a creek or the Manggahan Floodway between a user and a
    junkshop can make 400 m impassable, so treat this as a ranking key rather
    than as a travel estimate shown to users.
    """
    radius = 6_371_000.0
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlambda = math.radians(lon2 - lon1)
    a = (
        math.sin(dphi / 2) ** 2
        + math.cos(phi1) * math.cos(phi2) * math.sin(dlambda / 2) ** 2
    )
    return 2 * radius * math.asin(math.sqrt(a))


def estimated_cell_count(
    bbox: tuple[float, float, float, float] = CAINTA_BBOX,
    resolution: int = DEFAULT_RESOLUTION,
) -> int:
    """Rough count of cells covering a bounding box.

    Sanity check for the n=7 argument: this should land in the hundreds, which
    is the whole reason the spatial unit is a cell and not a barangay.
    """
    south, west, north, east = bbox
    if HAS_H3:
        area_km2 = h3.average_hexagon_area(resolution, unit="km^2")
    else:
        area_km2 = (FALLBACK_STEP_DEG * 111.32) ** 2

    mean_lat = math.radians((south + north) / 2)
    height_km = (north - south) * 111.32
    width_km = (east - west) * 111.32 * math.cos(mean_lat)
    return max(1, round(height_km * width_km / area_km2))
