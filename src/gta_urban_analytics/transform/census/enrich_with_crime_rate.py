"""
Census Crime-Rate Enrichment
============================
Spatial-joins unified crime points to the GTA Dissemination Area polygons,
counts incidents per DA, and adds `crime_count` and `crime_rate_per_1k`
properties to the existing `gta_census_da.geojson`.

Depends on two prior pipeline outputs:
  - data/02_transformed/unified_data.csv  (Step 3)
  - data/02_transformed/gta_census_da.geojson  (Step 4)

Overwrites `gta_census_da.geojson` in place with the two additional columns.
"""

import os
import logging

import geopandas as gpd
import pandas as pd

logger = logging.getLogger(__name__)

_project_root = os.path.normpath(
    os.path.join(os.path.dirname(__file__), "..", "..", "..", "..")
)

# DAs smaller than this threshold produce extremely noisy rates; null them out.
_MIN_POPULATION_FOR_RATE = 50


def enrich_census_with_crime_rate(
    crime_df: pd.DataFrame | None = None,
    census_gdf: gpd.GeoDataFrame | None = None,
    output_dir: str | None = None,
    verbose: bool = True,
) -> gpd.GeoDataFrame:
    """Add crime_count and crime_rate_per_1k to gta_census_da.geojson.

    Parameters:
        crime_df:    Pre-loaded crime DataFrame (needs ``lat``, ``lon``).
                     When *None* the full ``unified_data.csv`` is read.
        census_gdf:  Pre-loaded census GeoDataFrame.  When *None* the file
                     at ``<output_dir>/gta_census_da.geojson`` is read.
        output_dir:  Directory containing (and receiving) the GeoJSON.
                     Defaults to ``data/02_transformed/``.
        verbose:     Log progress messages.

    Returns:
        The enriched GeoDataFrame.
    """
    if output_dir is None:
        output_dir = os.path.join(_project_root, "data", "02_transformed")
    census_geojson = os.path.join(output_dir, "gta_census_da.geojson")

    # --- Load census DAs ---
    if census_gdf is not None:
        das = census_gdf.copy()
    else:
        if not os.path.exists(census_geojson):
            raise FileNotFoundError(
                f"Missing {census_geojson}. Run build_gta_census_geojson() first."
            )
        if verbose:
            logger.info("Loading census Dissemination Areas...")
        das = gpd.read_file(census_geojson)

    if das.crs is None or das.crs.to_epsg() != 4326:
        das = das.to_crs(epsg=4326)

    # Drop any prior enrichment columns so this step is safely idempotent
    # (re-running the pipeline shouldn't fail because the columns already exist).
    for col in ("crime_count", "crime_rate_per_1k"):
        if col in das.columns:
            das = das.drop(columns=col)

    # --- Load crime points ---
    if crime_df is not None:
        crime_points_df = crime_df[["lat", "lon"]].dropna().copy()
    else:
        crime_csv = os.path.join(
            _project_root, "data", "02_transformed", "unified_data.csv"
        )
        if not os.path.exists(crime_csv):
            raise FileNotFoundError(
                f"Missing {crime_csv}. Run the unify/filter/deduplicate steps first."
            )
        if verbose:
            logger.info("Loading unified crime points...")
        crime_points_df = pd.read_csv(
            crime_csv, usecols=["lat", "lon"], low_memory=False
        )
        crime_points_df = crime_points_df.dropna(subset=["lat", "lon"])

    if verbose:
        logger.info(f"Building GeoDataFrame of {len(crime_points_df):,} crime points...")
    crime_points = gpd.GeoDataFrame(
        crime_points_df,
        geometry=gpd.points_from_xy(crime_points_df["lon"], crime_points_df["lat"]),
        crs="EPSG:4326",
    )

    if verbose:
        logger.info("Running point-in-polygon join...")
    joined = gpd.sjoin(
        crime_points, das[["DAUID", "geometry"]], how="inner", predicate="within"
    )

    counts = (
        joined.groupby("DAUID").size().rename("crime_count").reset_index()
    )

    if verbose:
        logger.info(f"Matched {counts['crime_count'].sum():,} incidents to {len(counts):,} DAs.")

    # Merge counts back onto the DAs.
    enriched = das.merge(counts, on="DAUID", how="left")
    enriched["crime_count"] = enriched["crime_count"].fillna(0).astype(int)

    # Compute rate, nulling out small-population DAs to avoid noisy spikes.
    pop = pd.to_numeric(enriched["Population"], errors="coerce")
    rate = enriched["crime_count"] / pop * 1000
    too_small = pop < _MIN_POPULATION_FOR_RATE
    enriched["crime_rate_per_1k"] = rate.where(~too_small)
    # Null the count as well for tiny DAs so tooltips don't mislead.
    enriched.loc[too_small, "crime_count"] = pd.NA

    # Overwrite the census file in place.
    os.makedirs(output_dir, exist_ok=True)
    if verbose:
        logger.info(f"Writing enriched GeoJSON back to {census_geojson}...")
    # GeoJSON driver doesn't append; overwrite requires delete first.
    if os.path.exists(census_geojson):
        os.remove(census_geojson)
    enriched.to_file(census_geojson, driver="GeoJSON")

    if verbose:
        valid = enriched["crime_rate_per_1k"].dropna()
        logger.info(
            f"Enriched {len(enriched):,} DAs. "
            f"crime_rate_per_1k: median={valid.median():.2f}, "
            f"max={valid.max():.2f}, "
            f"n_valid={len(valid):,}."
        )

    return enriched


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
    enrich_census_with_crime_rate()
