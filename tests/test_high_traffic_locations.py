"""Tests for the high-traffic GTA location reference + classifier used to
distinguish organic anomaly hotspots (malls/hospitals) from unexplained
placeholder coordinates (F-19 follow-up)."""

import math

from gta_urban_analytics.transform.crime.high_traffic_locations import (
    HIGH_TRAFFIC_LOCATIONS,
    _haversine_m,
    classify_coordinate,
)


def test_exact_venue_match_returns_zero_distance():
    match = classify_coordinate(43.6544, -79.3807)  # CF Toronto Eaton Centre
    assert match is not None
    loc, dist = match
    assert loc.name == "CF Toronto Eaton Centre"
    assert loc.category == "mall"
    assert dist < 5.0  # essentially on the venue


def test_nearby_within_radius_matches():
    # ~220 m north of Canada's Wonderland (an isolated venue) → still a hit.
    match = classify_coordinate(43.8430 + 0.0020, -79.5390)
    assert match is not None
    loc, dist = match
    assert loc.name == "Canada's Wonderland"
    assert 100 < dist < 500


def test_open_country_returns_none():
    assert classify_coordinate(43.8, -79.4) is None


def test_missing_coordinate_returns_none():
    assert classify_coordinate(None, -79.4) is None
    assert classify_coordinate(float("nan"), -79.4) is None


def test_nearest_of_two_candidates_wins():
    # Mount Sinai (43.6575, -79.3905) and Toronto General (43.6587, -79.3884)
    # sit close together; a point next to Toronto General should pick it.
    match = classify_coordinate(43.6587, -79.3884)
    assert match is not None
    loc, _ = match
    assert loc.name == "Toronto General Hospital"


def test_haversine_known_distance():
    # ~1 degree of latitude ≈ 111 km.
    d = _haversine_m(43.0, -79.0, 44.0, -79.0)
    assert math.isclose(d, 111_000, rel_tol=0.02)


def test_all_locations_are_within_the_gta_bbox():
    # Sanity-guard the curated coordinates against transcription slips.
    for loc in HIGH_TRAFFIC_LOCATIONS:
        assert 43.0 <= loc.lat <= 44.6, f"{loc.name} lat out of GTA bbox"
        assert -80.6 <= loc.lon <= -78.2, f"{loc.name} lon out of GTA bbox"
        assert loc.category in {"mall", "hospital", "attraction", "transit"}
