"""Regression tests for audit finding F-19: the coordinate-anomaly layer flags
placeholder/snapped coordinates (many incidents at one identical point) while
leaving the incident data itself intact."""

import pandas as pd

from gta_urban_analytics.transform.crime.build_coordinate_anomalies import (
    build_coordinate_anomalies,
)


def test_flags_high_count_coordinate(tmp_path):
    rows = []
    for i in range(60):  # one placeholder coordinate with 60 distinct incidents
        rows.append(
            {
                "lat": 43.8, "lon": -79.4, "region": "York", "municipality": "Markham",
                "mapped_crime_category": "Theft", "occurrence_date": f"2025-01-{(i % 28) + 1:02d}",
            }
        )
    for _ in range(3):  # an organic coordinate with only 3 incidents
        rows.append(
            {
                "lat": 43.6, "lon": -79.38, "region": "Toronto", "municipality": "Toronto",
                "mapped_crime_category": "Assault", "occurrence_date": "2025-02-01",
            }
        )

    out = build_coordinate_anomalies(
        crime_df=pd.DataFrame(rows), output_dir=str(tmp_path), threshold=50, verbose=False
    )

    assert len(out) == 1
    row = out.iloc[0]
    assert (row["lat"], row["lon"]) == (43.8, -79.4)
    assert row["incident_count"] == 60
    assert row["top_category"] == "Theft"
    assert "York" in row["regions"]


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
    assert list(out.columns) == [
        "lat", "lon", "incident_count", "regions", "top_category", "first_date", "last_date",
    ]
