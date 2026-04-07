"""
Standalone Compact Builder
==========================
Produces slim variants of the three viz datasets for embedding inside the
single-file `dist/standalone.html` build of the Kepler.gl visualization.
The dev server and the multi-file static build still use the full datasets.

This is the ONLY place where viz-driven downsizing happens; the viz code
itself never simplifies, samples, or drops columns.

Depends on:
  - data/02_transformed/unified_data.csv            (Step 3)
  - data/02_transformed/gta_census_da.geojson       (Step 5, enriched)
  - data/02_transformed/shooting_arcs.csv           (Step 6)

Outputs (all under data/02_transformed/standalone/):
  - unified_data_compact.csv         — slim columns, 5-decimal lat/lon
  - gta_census_da_compact.geojson    — simplified polygons, slim properties
  - shooting_arcs.csv                — copied unchanged
"""

import os
import shutil
import logging

import geopandas as gpd
import pandas as pd

logger = logging.getLogger(__name__)

_project_root = os.path.normpath(
    os.path.join(os.path.dirname(__file__), "..", "..", "..")
)

# Douglas-Peucker simplification tolerance in metres (EPSG:26917 = UTM Zone 17N).
# 20 m is invisible at the GTA-wide zoom the map renders at.
_SIMPLIFY_TOLERANCE_M = 20

# Columns the four Kepler layers actually need.
_COMPACT_CRIME_COLUMNS = [
    "lat",
    "lon",
    "mapped_crime_category",
    "occurrence_date",
    "region",
]

# Properties Layers 2 and 3 use.
_COMPACT_CENSUS_PROPERTIES = [
    "DAUID",
    "Population",
    "Median_Income",
    "crime_count",
    "crime_rate_per_1k",
]


def _compact_crime(verbose: bool) -> pd.DataFrame:
    transformed_dir = os.path.join(_project_root, "data", "02_transformed")
    src = os.path.join(transformed_dir, "unified_data.csv")

    if verbose:
        logger.info("Reading full unified crime CSV...")
    df = pd.read_csv(src, usecols=_COMPACT_CRIME_COLUMNS, low_memory=False)

    # Drop rows without coordinates — they can't render on the map anyway.
    df = df.dropna(subset=["lat", "lon"])

    # Round to 5 decimal places (~1 m precision, far beyond what the hexbin needs).
    df["lat"] = df["lat"].round(5)
    df["lon"] = df["lon"].round(5)

    return df


def _compact_census(verbose: bool) -> gpd.GeoDataFrame:
    transformed_dir = os.path.join(_project_root, "data", "02_transformed")
    src = os.path.join(transformed_dir, "gta_census_da.geojson")

    if verbose:
        logger.info("Reading enriched census GeoJSON...")
    gdf = gpd.read_file(src)

    # Keep only the properties the viz actually uses.
    keep_cols = [c for c in _COMPACT_CENSUS_PROPERTIES if c in gdf.columns]
    missing = set(_COMPACT_CENSUS_PROPERTIES) - set(keep_cols)
    if missing:
        logger.warning(
            f"Census GeoJSON missing expected columns: {sorted(missing)}. "
            "Did the enrichment step run?"
        )
    gdf = gdf[keep_cols + ["geometry"]].copy()

    # Simplify polygons in a metric CRS for correct tolerance units.
    if verbose:
        logger.info(f"Simplifying polygons ({_SIMPLIFY_TOLERANCE_M} m tolerance)...")
    utm = gdf.to_crs(epsg=26917)
    utm["geometry"] = utm.geometry.simplify(
        tolerance=_SIMPLIFY_TOLERANCE_M, preserve_topology=True
    )
    gdf = utm.to_crs(epsg=4326)

    return gdf


def build_standalone_compact(verbose: bool = True) -> None:
    """Produce compact variants of all three viz datasets."""
    transformed_dir = os.path.join(_project_root, "data", "02_transformed")
    out_dir = os.path.join(transformed_dir, "standalone")
    os.makedirs(out_dir, exist_ok=True)

    # --- Crime points ---
    crime = _compact_crime(verbose)
    crime_out = os.path.join(out_dir, "unified_data_compact.csv")
    if verbose:
        logger.info(f"Writing {len(crime):,} rows to {crime_out}")
    crime.to_csv(crime_out, index=False)

    # --- Census DAs ---
    census = _compact_census(verbose)
    census_out = os.path.join(out_dir, "gta_census_da_compact.geojson")
    if os.path.exists(census_out):
        os.remove(census_out)
    if verbose:
        logger.info(f"Writing {len(census):,} DAs to {census_out}")
    census.to_file(census_out, driver="GeoJSON")

    # --- Shooting arcs (copy unchanged) ---
    arcs_src = os.path.join(transformed_dir, "shooting_arcs.csv")
    arcs_out = os.path.join(out_dir, "shooting_arcs.csv")
    if os.path.exists(arcs_src):
        if verbose:
            logger.info(f"Copying shooting arcs to {arcs_out}")
        shutil.copyfile(arcs_src, arcs_out)
    else:
        logger.warning(f"Missing {arcs_src}; standalone build will lack arc layer data.")

    # --- Size report ---
    if verbose:
        def _size(p):
            return os.path.getsize(p) / (1024 * 1024) if os.path.exists(p) else 0.0

        logger.info(
            f"Compact sizes — crime: {_size(crime_out):.1f} MB, "
            f"census: {_size(census_out):.1f} MB, "
            f"arcs: {_size(arcs_out):.1f} MB"
        )


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
    build_standalone_compact()
