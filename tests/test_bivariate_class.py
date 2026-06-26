"""Tests for the bivariate income × crime-rate classification added to the
census enrichment step. Each Dissemination Area is pre-binned (in the pipeline,
not the viz) into one of 9 classes = income tercile × crime-rate tercile,
encoded A..I with a human-readable `bivariate_label`."""

import geopandas as gpd
import pandas as pd
from shapely.geometry import Polygon

from gta_urban_analytics.transform.census.enrich_with_crime_rate import (
    _assign_bivariate,
    enrich_census_with_crime_rate,
)


def _grid_gdf():
    """9 DAs covering every income × crime-rate tercile combination.

    income ∈ {30k, 40k, 50k} → terciles 0/1/2; rate ∈ {1, 10, 100} → 0/1/2.
    Geometry is irrelevant here (we call _assign_bivariate directly), so reuse
    one dummy polygon.
    """
    poly = Polygon([(0, 0), (1, 0), (1, 1), (0, 1)])
    rows = []
    for income in (30000, 40000, 50000):
        for rate in (1.0, 10.0, 100.0):
            rows.append({"Median_Income": income, "crime_rate_per_1k": rate})
    return gpd.GeoDataFrame(rows, geometry=[poly] * len(rows), crs="EPSG:4326")


def test_assign_bivariate_full_grid():
    gdf = _grid_gdf()
    _assign_bivariate(gdf)

    by_combo = {
        (r.Median_Income, r.crime_rate_per_1k): (r.bivariate_class, r.bivariate_label)
        for r in gdf.itertuples()
    }

    # Class index k = income_tercile * 3 + rate_tercile, encoded A..I.
    assert by_combo[(30000, 1.0)] == ("A", "Lower-income · Lower-crime")
    assert by_combo[(30000, 100.0)] == ("C", "Lower-income · Higher-crime")
    assert by_combo[(40000, 10.0)] == ("E", "Mid-income · Mid-crime")
    assert by_combo[(50000, 1.0)] == ("G", "Higher-income · Lower-crime")
    assert by_combo[(50000, 100.0)] == ("I", "Higher-income · Higher-crime")

    # All nine classes are represented exactly once.
    assert sorted(c for c, _ in by_combo.values()) == list("ABCDEFGHI")


def test_assign_bivariate_nulls_when_either_missing():
    poly = Polygon([(0, 0), (1, 0), (1, 1), (0, 1)])
    gdf = gpd.GeoDataFrame(
        {
            "Median_Income": [50000, None, 40000],
            "crime_rate_per_1k": [None, 5.0, 12.0],
        },
        geometry=[poly] * 3,
        crs="EPSG:4326",
    )
    _assign_bivariate(gdf)

    # Rows missing income OR crime-rate are unclassified — stored as a missing
    # value that geopandas serializes to GeoJSON `null` (transparent in Kepler).
    assert pd.isna(gdf.loc[0, "bivariate_class"])
    assert pd.isna(gdf.loc[0, "bivariate_label"])
    assert pd.isna(gdf.loc[1, "bivariate_class"])
    # The fully-populated row gets a class.
    assert gdf.loc[2, "bivariate_class"] in set("ABCDEFGHI")


def test_assign_bivariate_handles_missing_income_column():
    """A census frame without Median_Income must not raise — every DA is simply
    left unclassified (mirrors the small-fixture path other enrichment tests use)."""
    poly = Polygon([(0, 0), (1, 0), (1, 1), (0, 1)])
    gdf = gpd.GeoDataFrame(
        {"crime_rate_per_1k": [5.0, 12.0]}, geometry=[poly] * 2, crs="EPSG:4326"
    )
    _assign_bivariate(gdf)
    assert gdf["bivariate_class"].isna().all()


def test_enrich_emits_bivariate_columns(tmp_path):
    """The public enrichment entry point writes the two new columns end-to-end."""
    poly = Polygon([(-79.5, 43.7), (-79.3, 43.7), (-79.3, 43.9), (-79.5, 43.9)])
    census = gpd.GeoDataFrame(
        {"DAUID": ["1"], "Population": [1000], "Median_Income": [42000]},
        geometry=[poly],
        crs="EPSG:4326",
    )
    crime = pd.DataFrame({"lat": [43.8, 43.8], "lon": [-79.4, -79.4]})

    enriched = enrich_census_with_crime_rate(
        crime_df=crime, census_gdf=census, output_dir=str(tmp_path), verbose=False
    )

    assert "bivariate_class" in enriched.columns
    assert "bivariate_label" in enriched.columns
    # One DA with both income and a crime rate → it gets classified.
    assert enriched.loc[0, "bivariate_class"] in set("ABCDEFGHI")
