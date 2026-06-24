"""Tests for the standalone-compact builder: slim crime columns with rounded
coords, simplified census polygons, and a copied arcs file (closes a T12/F-14 gap)."""

import geopandas as gpd
import pandas as pd
from shapely.geometry import Polygon

from gta_urban_analytics.transform.build_standalone_compact import build_standalone_compact


def test_build_standalone_compact(tmp_path):
    src = tmp_path

    pd.DataFrame(
        {
            "lat": [43.123456789, None], "lon": [-79.987654321, None],
            "mapped_crime_category": ["Assault", "Theft"],
            "occurrence_date": ["2025-01-01", "2025-01-02"],
            "region": ["Toronto", "York"],
            "extra_col": ["x", "y"],  # must be dropped by the compact column selection
        }
    ).to_csv(src / "unified_data.csv", index=False)

    gpd.GeoDataFrame(
        {
            "DAUID": ["1"], "Population": [1000], "Median_Income": [50000],
            "crime_count": [5], "crime_rate_per_1k": [5.0],
        },
        geometry=[Polygon([(-79.6, 43.6), (-79.5, 43.6), (-79.5, 43.7), (-79.6, 43.7)])],
        crs="EPSG:4326",
    ).to_file(src / "gta_census_da.geojson", driver="GeoJSON")

    pd.DataFrame({"id": [0], "src_lat": [43.6]}).to_csv(src / "shooting_arcs.csv", index=False)

    build_standalone_compact(source_dir=str(src), verbose=False)

    out = src / "standalone"
    crime = pd.read_csv(out / "unified_data_compact.csv")
    # NaN-coord row dropped; coords rounded to 5 dp; only the slim columns kept.
    assert len(crime) == 1
    assert crime.loc[0, "lat"] == 43.12346
    assert set(crime.columns) == {"lat", "lon", "mapped_crime_category", "occurrence_date", "region"}
    # Census compact + copied arcs present.
    assert (out / "gta_census_da_compact.geojson").exists()
    assert (out / "shooting_arcs.csv").exists()
