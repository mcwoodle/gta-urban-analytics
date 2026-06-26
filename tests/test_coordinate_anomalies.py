"""Regression tests for audit finding F-19: the coordinate-anomaly layer flags
placeholder/snapped coordinates (many incidents at one identical point) while
leaving the incident data itself intact, and classifies each flagged coordinate
as near a known high-traffic venue or unexplained."""

import pandas as pd

from gta_urban_analytics.transform.crime.build_coordinate_anomalies import (
    build_coordinate_anomalies,
)

_OUTPUT_COLUMNS = [
    "lat", "lon", "description", "anomaly_type", "nearest_location",
    "location_category", "incident_count", "top_category", "regions",
    "first_date", "last_date",
]


def _rows_at(lat, lon, n, *, region="York", municipality="Markham", category="Theft"):
    return [
        {
            "lat": lat, "lon": lon, "region": region, "municipality": municipality,
            "mapped_crime_category": category, "occurrence_date": f"2025-01-{(i % 28) + 1:02d}",
        }
        for i in range(n)
    ]


def test_flags_high_count_coordinate_in_open_country(tmp_path):
    # A high-count coordinate far from any known venue → unexplained.
    rows = _rows_at(43.8, -79.4, 60)
    rows += _rows_at(43.6, -79.38, 3, region="Toronto", municipality="Toronto", category="Assault")

    out = build_coordinate_anomalies(
        crime_df=pd.DataFrame(rows), output_dir=str(tmp_path), threshold=50, verbose=False
    )

    assert len(out) == 1
    row = out.iloc[0]
    assert (row["lat"], row["lon"]) == (43.8, -79.4)
    assert row["incident_count"] == 60
    assert row["top_category"] == "Theft"
    assert "York" in row["regions"]
    assert row["anomaly_type"] == "unexplained"
    assert row["nearest_location"] == ""
    assert row["location_category"] == ""
    assert row["description"].startswith("Unexplained")


def test_flags_high_count_coordinate_at_known_venue(tmp_path):
    # A high-count coordinate sitting on CF Toronto Eaton Centre → high_traffic_area.
    rows = _rows_at(43.6544, -79.3807, 80, region="Toronto", municipality="Toronto")

    out = build_coordinate_anomalies(
        crime_df=pd.DataFrame(rows), output_dir=str(tmp_path), threshold=50, verbose=False
    )

    assert len(out) == 1
    row = out.iloc[0]
    assert row["anomaly_type"] == "high_traffic_area"
    assert row["nearest_location"] == "CF Toronto Eaton Centre"
    assert row["location_category"] == "mall"
    assert "CF Toronto Eaton Centre" in row["description"]


def test_threshold_is_strictly_greater_than(tmp_path):
    # Exactly threshold incidents must NOT be flagged (the cut is "> threshold").
    out = build_coordinate_anomalies(
        crime_df=pd.DataFrame(_rows_at(43.8, -79.4, 50)),
        output_dir=str(tmp_path), threshold=50, verbose=False,
    )
    assert len(out) == 0


def test_no_anomalies_writes_empty_with_headers(tmp_path):
    df = pd.DataFrame(
        {
            "lat": [43.6, 43.7], "lon": [-79.4, -79.5], "region": ["Toronto", "York"],
            "municipality": ["Toronto", "Markham"], "mapped_crime_category": ["Assault", "Theft"],
            "occurrence_date": ["2025-01-01", "2025-01-02"],
        }
    )
    out = build_coordinate_anomalies(
        crime_df=df, output_dir=str(tmp_path), threshold=50, verbose=False
    )
    assert len(out) == 0
    assert list(out.columns) == _OUTPUT_COLUMNS
