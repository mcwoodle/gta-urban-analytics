"""Tests for the per-bucket (Violent/Property/Nuisance/Other) crime counts and
per-1,000 rates added to the census enrichment. Per-bucket counts must sum to
the total, inherit the reference-year window, and respect small-pop nulling —
without disturbing the existing total or bivariate columns."""

import geopandas as gpd
import pandas as pd
from shapely.geometry import Polygon

from gta_urban_analytics.transform.census.enrich_with_crime_rate import (
    enrich_census_with_crime_rate,
    _BUCKET_COUNT_COLUMNS,
    _BUCKET_RATE_COLUMNS,
)


def _census(population=1000):
    poly = Polygon([(-79.5, 43.7), (-79.3, 43.7), (-79.3, 43.9), (-79.5, 43.9)])
    return gpd.GeoDataFrame(
        {"DAUID": ["1"], "Population": [population], "Median_Income": [42000]},
        geometry=[poly],
        crs="EPSG:4326",
    )


def _crime(groups, dates=None):
    n = len(groups)
    return pd.DataFrame(
        {
            "lat": [43.8] * n,
            "lon": [-79.4] * n,
            "crime_group": groups,
            "occurrence_date": dates if dates is not None else ["2025-01-01"] * n,
        }
    )


def test_emits_all_eight_bucket_columns(tmp_path):
    crime = _crime(["Violent", "Property", "Nuisance", "Other"])
    enriched = enrich_census_with_crime_rate(
        crime_df=crime, census_gdf=_census(), output_dir=str(tmp_path), verbose=False
    )
    for col in _BUCKET_COUNT_COLUMNS + _BUCKET_RATE_COLUMNS:
        assert col in enriched.columns


def test_bucket_counts_sum_to_total(tmp_path):
    crime = _crime(
        ["Violent", "Violent", "Property", "Nuisance", "Nuisance", "Nuisance", "Other"]
    )
    enriched = enrich_census_with_crime_rate(
        crime_df=crime, census_gdf=_census(), output_dir=str(tmp_path), verbose=False
    )
    row = enriched.loc[0]
    assert int(row["crime_count_violent"]) == 2
    assert int(row["crime_count_property"]) == 1
    assert int(row["crime_count_nuisance"]) == 3
    assert int(row["crime_count_other"]) == 1
    bucket_sum = sum(int(row[c]) for c in _BUCKET_COUNT_COLUMNS)
    assert bucket_sum == int(row["crime_count"]) == 7


def test_bucket_rate_matches_count_over_pop(tmp_path):
    crime = _crime(["Violent", "Violent", "Property"])
    enriched = enrich_census_with_crime_rate(
        crime_df=crime, census_gdf=_census(population=1000),
        output_dir=str(tmp_path), verbose=False,
    )
    # 2 violent / 1000 people * 1000 = 2.0
    assert enriched.loc[0, "crime_rate_violent_per_1k"] == 2.0
    assert enriched.loc[0, "crime_rate_property_per_1k"] == 1.0
    # A bucket with no incidents in this DA → rate 0.
    assert enriched.loc[0, "crime_rate_nuisance_per_1k"] == 0.0


def test_small_population_nulls_bucket_rates(tmp_path):
    crime = _crime(["Violent", "Property"])
    enriched = enrich_census_with_crime_rate(
        crime_df=crime, census_gdf=_census(population=10),  # below 50 threshold
        output_dir=str(tmp_path), verbose=False,
    )
    for col in _BUCKET_RATE_COLUMNS + _BUCKET_COUNT_COLUMNS:
        assert pd.isna(enriched.loc[0, col])
    # The total is nulled too (existing behaviour, unchanged).
    assert pd.isna(enriched.loc[0, "crime_rate_per_1k"])


def test_reference_year_narrows_bucket_counts(tmp_path):
    crime = _crime(
        ["Violent", "Violent", "Property"],
        dates=["2025-03-01", "2024-03-01", "2025-06-01"],
    )
    enriched = enrich_census_with_crime_rate(
        crime_df=crime, census_gdf=_census(), output_dir=str(tmp_path),
        reference_year=2025, verbose=False,
    )
    # Only the two 2025 incidents count: 1 Violent + 1 Property.
    assert int(enriched.loc[0, "crime_count_violent"]) == 1
    assert int(enriched.loc[0, "crime_count_property"]) == 1


def test_bivariate_unaffected_and_bare_fixtures_still_work(tmp_path):
    # A bare lat/lon frame (no crime_group) must not raise; buckets become 0.
    crime = pd.DataFrame({"lat": [43.8, 43.8], "lon": [-79.4, -79.4]})
    enriched = enrich_census_with_crime_rate(
        crime_df=crime, census_gdf=_census(), output_dir=str(tmp_path), verbose=False
    )
    assert int(enriched.loc[0, "crime_count"]) == 2
    for col in _BUCKET_COUNT_COLUMNS:
        assert int(enriched.loc[0, col]) == 0
    # The bivariate classification still computed.
    assert enriched.loc[0, "bivariate_class"] in set("ABCDEFGHI")
