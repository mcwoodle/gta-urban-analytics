"""Tests for the monthly municipality builder: one polygon per municipality
(dissolved DAs, geometry stable across months) carrying per-month
``count_YYYY_MM`` / ``rate_YYYY_MM_per_1k`` columns for 2025 + 2026."""

import geopandas as gpd
import pandas as pd
from shapely.geometry import Polygon

from gta_urban_analytics.transform.census.build_municipality_monthly import (
    build_municipality_monthly,
)


def _census():
    # Two side-by-side DAs; dissolve into the municipalities their points name.
    a = Polygon([(-79.6, 43.7), (-79.5, 43.7), (-79.5, 43.8), (-79.6, 43.8)])
    b = Polygon([(-79.5, 43.7), (-79.4, 43.7), (-79.4, 43.8), (-79.5, 43.8)])
    return gpd.GeoDataFrame(
        {"DAUID": ["1", "2"], "Population": [1000, 2000]},
        geometry=[a, b],
        crs="EPSG:4326",
    )


def _crime():
    # Aurora (DA 1, west) and Newmarket (DA 2, east) across two months/years.
    return pd.DataFrame(
        {
            "lat": [43.75, 43.75, 43.75, 43.75, 43.75, 43.75],
            "lon": [-79.55, -79.55, -79.55, -79.45, -79.45, -79.45],
            "municipality": ["Aurora"] * 3 + ["Newmarket"] * 3,
            # Aurora: 2 in 2025-01, 1 in 2026-01.
            # Newmarket: 1 in 2025-01, 2 in 2026-01.
            "occurrence_date": [
                "2025-01-10", "2025-01-20", "2026-01-15",
                "2025-01-05", "2026-01-08", "2026-01-22",
            ],
        }
    )


def test_builds_one_polygon_per_municipality(tmp_path):
    out = build_municipality_monthly(
        crime_df=_crime(), census_gdf=_census(), output_dir=str(tmp_path), verbose=False
    )
    assert set(out["municipality"]) == {"Aurora", "Newmarket"}
    aurora = out[out["municipality"] == "Aurora"].iloc[0]
    newmarket = out[out["municipality"] == "Newmarket"].iloc[0]
    assert aurora["Population"] == 1000
    assert newmarket["Population"] == 2000


def test_per_month_counts_and_rates(tmp_path):
    out = build_municipality_monthly(
        crime_df=_crime(), census_gdf=_census(), output_dir=str(tmp_path), verbose=False
    )
    aurora = out[out["municipality"] == "Aurora"].iloc[0]
    newmarket = out[out["municipality"] == "Newmarket"].iloc[0]

    # Counts per month.
    assert aurora["count_2025_01"] == 2
    assert aurora["count_2026_01"] == 1
    assert newmarket["count_2025_01"] == 1
    assert newmarket["count_2026_01"] == 2

    # Rates: count / population * 1000.
    assert aurora["rate_2025_01_per_1k"] == 2.0  # 2 / 1000 * 1000
    assert newmarket["rate_2026_01_per_1k"] == 1.0  # 2 / 2000 * 1000


def test_only_2025_2026_months_emitted(tmp_path):
    crime = _crime()
    # A 2024 incident must be ignored entirely (outside the monthly window).
    crime = pd.concat(
        [
            crime,
            pd.DataFrame(
                {
                    "lat": [43.75],
                    "lon": [-79.55],
                    "municipality": ["Aurora"],
                    "occurrence_date": ["2024-06-01"],
                }
            ),
        ],
        ignore_index=True,
    )
    out = build_municipality_monthly(
        crime_df=crime, census_gdf=_census(), output_dir=str(tmp_path), verbose=False
    )
    month_cols = [c for c in out.columns if c.startswith("count_")]
    assert "count_2024_06" not in month_cols
    assert {"count_2025_01", "count_2026_01"} <= set(month_cols)


def test_writes_geojson_to_standalone_dir(tmp_path):
    build_municipality_monthly(
        crime_df=_crime(), census_gdf=_census(), output_dir=str(tmp_path), verbose=False
    )
    written = gpd.read_file(tmp_path / "standalone" / "gta_municipalities_monthly.geojson")
    assert "rate_2025_01_per_1k" in written.columns
    assert len(written) == 2
