"""Regression tests for audit finding F-04: the headline census enrichment must
restrict crime to a single reference year so rates are comparable across regions."""

import geopandas as gpd
import pandas as pd
from shapely.geometry import Polygon

from gta_urban_analytics.transform.census.enrich_with_crime_rate import (
    enrich_census_with_crime_rate,
)


def _census():
    poly = Polygon([(-79.5, 43.7), (-79.3, 43.7), (-79.3, 43.9), (-79.5, 43.9)])
    return gpd.GeoDataFrame(
        {"DAUID": ["1"], "Population": [1000]}, geometry=[poly], crs="EPSG:4326"
    )


def _crime():
    return pd.DataFrame(
        {
            "lat": [43.8, 43.8, 43.8, 43.8, 43.8],
            "lon": [-79.4, -79.4, -79.4, -79.4, -79.4],
            "occurrence_date": [
                "2025-01-01", "2025-06-01", "2025-12-01", "2024-01-01", "2023-01-01",
            ],
        }
    )


def test_reference_year_filters_crime(tmp_path):
    enriched = enrich_census_with_crime_rate(
        crime_df=_crime(), census_gdf=_census(), output_dir=str(tmp_path),
        reference_year=2025, verbose=False,
    )
    assert int(enriched.loc[0, "crime_count"]) == 3  # only the three 2025 points


def test_no_reference_year_counts_all_years(tmp_path):
    enriched = enrich_census_with_crime_rate(
        crime_df=_crime(), census_gdf=_census(), output_dir=str(tmp_path),
        reference_year=None, verbose=False,
    )
    assert int(enriched.loc[0, "crime_count"]) == 5
