"""Tests for spatial binning — the n=7 workaround and the privacy boundary."""

from __future__ import annotations

import pytest

from daloy.spatial import (
    CAINTA_BBOX,
    CoordinateOutOfRange,
    bin_point,
    estimated_cell_count,
    haversine_m,
    in_cainta_bbox,
)

# Somewhere in Cainta; precise enough to test binning, not a real address.
CAINTA_LAT, CAINTA_LON = 14.5786, 121.1222


def test_binning_is_deterministic() -> None:
    assert bin_point(CAINTA_LAT, CAINTA_LON) == bin_point(CAINTA_LAT, CAINTA_LON)


def test_cell_id_does_not_leak_the_coordinate() -> None:
    """The privacy guarantee in plan §7.5, as an assertion.

    A stored cell ID must not contain the raw decimal degrees it came from.
    """
    cell = bin_point(CAINTA_LAT, CAINTA_LON)
    assert "14.5786" not in cell.cell_id
    assert "121.1222" not in cell.cell_id


def test_nearby_points_collapse_into_one_cell() -> None:
    """~20 m apart should not be distinguishable after binning."""
    a = bin_point(CAINTA_LAT, CAINTA_LON)
    b = bin_point(CAINTA_LAT + 0.0001, CAINTA_LON + 0.0001)
    assert a.cell_id == b.cell_id


def test_distant_points_land_in_different_cells() -> None:
    a = bin_point(CAINTA_LAT, CAINTA_LON)
    b = bin_point(CAINTA_LAT + 0.02, CAINTA_LON + 0.02)
    assert a.cell_id != b.cell_id


def test_fallback_cells_are_labelled_so_they_cannot_pass_as_h3() -> None:
    cell = bin_point(CAINTA_LAT, CAINTA_LON)
    assert cell.scheme in ("h3", "square")
    if not cell.is_h3:
        assert cell.cell_id.startswith("sq")


def test_bad_coordinates_rejected() -> None:
    with pytest.raises(CoordinateOutOfRange):
        bin_point(95.0, 121.0)
    with pytest.raises(CoordinateOutOfRange):
        bin_point(14.5, 200.0)


def test_bbox_membership() -> None:
    assert in_cainta_bbox(CAINTA_LAT, CAINTA_LON)
    assert not in_cainta_bbox(14.5995, 120.9842)  # Manila
    south, west, north, east = CAINTA_BBOX
    assert in_cainta_bbox(south, west)
    assert in_cainta_bbox(north, east)


def test_haversine_against_a_known_separation() -> None:
    """0.001 deg of latitude is ~111 m anywhere on Earth."""
    assert haversine_m(14.5, 121.0, 14.501, 121.0) == pytest.approx(111.0, abs=2.0)
    assert haversine_m(14.5, 121.0, 14.5, 121.0) == 0.0


def test_cell_count_defeats_the_n_equals_7_problem() -> None:
    """Plan §1: hundreds of cells where there are only seven barangays."""
    count = estimated_cell_count()
    assert count > 100, f"expected hundreds of cells, got {count}"
    assert count > 7 * 10
