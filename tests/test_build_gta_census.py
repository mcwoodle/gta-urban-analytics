"""Tests for the census builder: boundaries ⋈ demographics, drop zero-population
DAs, and compute centroids (closes a T12/F-14 coverage gap). Uses synthetic inputs
so no StatCan shapefile / 8 GB CSV is read."""

import geopandas as gpd
import pandas as pd
from shapely.geometry import Polygon

import gta_urban_analytics.transform.census.build_gta_census as bc


def test_build_gta_census_merges_filters_and_centroids(tmp_path, monkeypatch):
    monkeypatch.setattr(bc, "_project_root", str(tmp_path))

    boundaries = gpd.GeoDataFrame(
        {"DAUID": ["35200001", "35200002"]},
        geometry=[
            Polygon([(-79.5, 43.7), (-79.4, 43.7), (-79.4, 43.8), (-79.5, 43.8)]),
            Polygon([(-79.3, 43.6), (-79.2, 43.6), (-79.2, 43.7), (-79.3, 43.7)]),
        ],
        crs="EPSG:4326",
    )
    demographics = pd.DataFrame(
        {
            "ALT_GEO_CODE": ["35200001", "35200002"],
            "Population": [1000, 0],          # the 0-population DA must be dropped
            "Median_Income": [50000, 60000],
        }
    )

    out = bc.build_gta_census_geojson(boundaries=boundaries, demographics=demographics, verbose=False)

    # Zero-population DA dropped; surviving DA merged correctly.
    assert list(out["DAUID"]) == ["35200001"]
    assert int(out.iloc[0]["Population"]) == 1000
    assert int(out.iloc[0]["Median_Income"]) == 50000
    # Centroid lands inside the first polygon's bounds.
    assert -79.5 < out.iloc[0]["centroid_lon"] < -79.4
    assert 43.7 < out.iloc[0]["centroid_lat"] < 43.8
    # GeoJSON written under the patched project root.
    assert (tmp_path / "data" / "02_transformed" / "gta_census_da.geojson").exists()
