"""Tests for year partitioning: slice the unified data into per-year folders and
exclude undated rows (closes a T12/F-14 coverage gap). The heavy per-year
sub-builders are mocked — they're tested in their own modules."""

from unittest import mock

import geopandas as gpd
import pandas as pd
from shapely.geometry import Polygon

import gta_urban_analytics.transform.partition_by_year as pby


def test_partition_creates_year_folders_and_excludes_undated(tmp_path, monkeypatch):
    monkeypatch.setattr(pby, "_project_root", str(tmp_path))
    transformed = tmp_path / "data" / "02_transformed"
    transformed.mkdir(parents=True)

    pd.DataFrame(
        {
            "source_identifier": ["a", "b", "c"],
            "region": ["York"] * 3,
            "original_crime_type": ["Assault"] * 3,
            "mapped_crime_category": ["Assault"] * 3,
            "occurrence_date": ["2024-05-01", "2025-06-01", None],  # 'c' has no date
            "lat": [43.6, 43.7, 43.8], "lon": [-79.4, -79.5, -79.6],
            "municipality": ["Markham"] * 3,
        }
    ).to_csv(transformed / "unified_data.csv", index=False)

    gpd.GeoDataFrame(
        {"DAUID": ["1"], "Population": [1000]},
        geometry=[Polygon([(-79.7, 43.5), (-79.3, 43.5), (-79.3, 43.9), (-79.7, 43.9)])],
        crs="EPSG:4326",
    ).to_file(transformed / "gta_census_da.geojson", driver="GeoJSON")

    # Mock the per-year sub-builders (imported locally inside partition_all_years).
    monkeypatch.setattr(
        "gta_urban_analytics.transform.crime.build_shooting_arcs.build_shooting_arcs", mock.Mock()
    )
    enrich = mock.Mock()
    monkeypatch.setattr(
        "gta_urban_analytics.transform.census.enrich_with_crime_rate.enrich_census_with_crime_rate", enrich
    )
    monkeypatch.setattr(
        "gta_urban_analytics.transform.build_standalone_compact.build_standalone_compact", mock.Mock()
    )

    pby.partition_all_years(verbose=False)

    assert list(pd.read_csv(transformed / "2024" / "unified_data.csv")["source_identifier"]) == ["a"]
    assert list(pd.read_csv(transformed / "2025" / "unified_data.csv")["source_identifier"]) == ["b"]
    # The undated row 'c' lands in no year folder.
    for year in range(2020, 2027):
        f = transformed / str(year) / "unified_data.csv"
        if f.exists():
            assert "c" not in set(pd.read_csv(f)["source_identifier"])
    # Per-year census enrichment ran for each populated year (2024, 2025).
    assert enrich.call_count == 2
