"""Tests for the municipality-level crime-rate choropleth: DAs are dissolved into
municipalities (assigned via the crime feed's municipality labels), population is
summed, and total + per-bucket per-capita rates are computed over a shared
denominator so the bucket counts sum to the total."""

import geopandas as gpd
import pandas as pd
from shapely.geometry import Polygon

from gta_urban_analytics.transform.census.build_municipality_choropleth import (
    build_municipality_choropleth,
)


def _census():
    # Two side-by-side DAs; together they will dissolve into the municipalities
    # that the crime points within them name.
    a = Polygon([(-79.6, 43.7), (-79.5, 43.7), (-79.5, 43.8), (-79.6, 43.8)])
    b = Polygon([(-79.5, 43.7), (-79.4, 43.7), (-79.4, 43.8), (-79.5, 43.8)])
    return gpd.GeoDataFrame(
        {"DAUID": ["1", "2"], "Population": [1000, 2000]},
        geometry=[a, b],
        crs="EPSG:4326",
    )


def _crime():
    # DA "1" (west) gets Aurora points; DA "2" (east) gets Newmarket points.
    return pd.DataFrame(
        {
            "lat": [43.75, 43.75, 43.75, 43.75, 43.75],
            "lon": [-79.55, -79.55, -79.45, -79.45, -79.45],
            "municipality": ["Aurora", "Aurora", "Newmarket", "Newmarket", "Newmarket"],
            "crime_group": ["Violent", "Property", "Violent", "Violent", "Nuisance"],
        }
    )


def test_builds_one_polygon_per_municipality(tmp_path):
    out = build_municipality_choropleth(
        crime_df=_crime(), census_gdf=_census(), output_dir=str(tmp_path), verbose=False
    )
    assert set(out["municipality"]) == {"Aurora", "Newmarket"}
    # Population summed from the DA assigned to each municipality.
    aurora = out[out["municipality"] == "Aurora"].iloc[0]
    newmarket = out[out["municipality"] == "Newmarket"].iloc[0]
    assert aurora["Population"] == 1000
    assert newmarket["Population"] == 2000


def test_rates_and_bucket_sums(tmp_path):
    out = build_municipality_choropleth(
        crime_df=_crime(), census_gdf=_census(), output_dir=str(tmp_path), verbose=False
    )
    aurora = out[out["municipality"] == "Aurora"].iloc[0]
    # 2 incidents / 1000 people * 1000 = 2.0
    assert aurora["crime_count"] == 2
    assert aurora["crime_rate_per_1k"] == 2.0

    newmarket = out[out["municipality"] == "Newmarket"].iloc[0]
    # 3 incidents / 2000 * 1000 = 1.5
    assert newmarket["crime_count"] == 3
    assert newmarket["crime_rate_per_1k"] == 1.5
    # Buckets sum to the total for every municipality.
    bucket_cols = [
        "crime_count_violent", "crime_count_property",
        "crime_count_nuisance", "crime_count_other",
    ]
    for _, row in out.iterrows():
        assert sum(int(row[c]) for c in bucket_cols) == int(row["crime_count"])


def test_selected_fields_default_to_total(tmp_path):
    out = build_municipality_choropleth(
        crime_df=_crime(), census_gdf=_census(), output_dir=str(tmp_path), verbose=False
    )
    assert (out["selected_count"] == out["crime_count"]).all()
    assert (out["selected_rate"] == out["crime_rate_per_1k"]).all()


def test_drops_non_municipality_labels(tmp_path):
    crime = pd.DataFrame(
        {
            "lat": [43.75, 43.75, 43.75],
            "lon": [-79.55, -79.45, -79.45],
            "municipality": ["Aurora", "Outside Region", "Outside Region"],
            "crime_group": ["Violent", "Property", "Property"],
        }
    )
    out = build_municipality_choropleth(
        crime_df=crime, census_gdf=_census(), output_dir=str(tmp_path), verbose=False
    )
    assert "Outside Region" not in set(out["municipality"])


def test_excludes_near_anomaly_crimes(tmp_path):
    # Two incidents on top of the CF Toronto Eaton Centre (a known venue), one
    # away from any venue — all inside DA "1" (geometry covers Toronto-ish here).
    eaton = Polygon([(-79.40, 43.64), (-79.36, 43.64), (-79.36, 43.67), (-79.40, 43.67)])
    census = gpd.GeoDataFrame(
        {"DAUID": ["1"], "Population": [1000]}, geometry=[eaton], crs="EPSG:4326"
    )
    crime = pd.DataFrame(
        {
            "lat": [43.6544, 43.6544, 43.655],
            "lon": [-79.3807, -79.3807, -79.37],  # first two = Eaton Centre
            "municipality": ["Toronto", "Toronto", "Toronto"],
            "crime_group": ["Property", "Property", "Violent"],
        }
    )
    out = build_municipality_choropleth(
        crime_df=crime, census_gdf=census, output_dir=str(tmp_path), verbose=False
    )
    row = out.iloc[0]
    assert int(row["crime_count"]) == 3
    # The two venue-snapped incidents are excluded; one remains.
    assert int(row["crime_count_excl_anomaly"]) == 1
    # Excluded count never exceeds the full count.
    assert int(row["crime_count_excl_anomaly"]) <= int(row["crime_count"])
    assert int(row["crime_count_property_excl_anomaly"]) == 0
    assert int(row["crime_count_violent_excl_anomaly"]) == 1


def test_writes_geojson(tmp_path):
    build_municipality_choropleth(
        crime_df=_crime(), census_gdf=_census(), output_dir=str(tmp_path), verbose=False
    )
    written = gpd.read_file(tmp_path / "gta_municipalities.geojson")
    assert "selected_rate" in written.columns
    assert len(written) == 2
