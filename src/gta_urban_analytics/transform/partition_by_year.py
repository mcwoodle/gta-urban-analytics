"""
Year Partitioner
================
Slices the all-years transformed outputs into per-year subfolders under
``data/02_transformed/<year>/``.  Each year folder mirrors the top-level
structure:

    <year>/
    ├── unified_data.csv
    ├── gta_census_da.geojson        (re-enriched with that year's crimes)
    ├── shooting_arcs.csv
    └── standalone/
        ├── unified_data_compact.csv
        ├── gta_census_da_compact.geojson
        └── shooting_arcs.csv

Only years from 2020 to the current calendar year are emitted.

Depends on all prior pipeline steps having completed (Steps 1–7).
"""

import datetime
import os
import logging
import shutil

import geopandas as gpd
import pandas as pd

logger = logging.getLogger(__name__)

_project_root = os.path.normpath(
    os.path.join(os.path.dirname(__file__), "..", "..", "..")
)


def partition_all_years(verbose: bool = True) -> None:
    """Partition the full transformed dataset into per-year subfolders."""
    from gta_urban_analytics.transform.crime.build_shooting_arcs import build_shooting_arcs
    from gta_urban_analytics.transform.census.enrich_with_crime_rate import enrich_census_with_crime_rate
    from gta_urban_analytics.transform.build_standalone_compact import build_standalone_compact

    transformed_dir = os.path.join(_project_root, "data", "02_transformed")

    # ── Load the all-years datasets once ────────────────────────────────
    if verbose:
        logger.info("Loading all-years unified crime data...")
    crime_df = pd.read_csv(
        os.path.join(transformed_dir, "unified_data.csv"),
        low_memory=False,
    )
    crime_df["occurrence_date"] = pd.to_datetime(
        crime_df["occurrence_date"], errors="coerce"
    )
    crime_df["_year"] = crime_df["occurrence_date"].dt.year

    # Load the *un-enriched* census GeoJSON (before crime stats were added)
    # so each year gets a clean enrichment.  We read the enriched version and
    # strip the crime columns — this avoids re-running the costly census build.
    if verbose:
        logger.info("Loading census GeoJSON (stripping prior enrichment)...")
    census_gdf = gpd.read_file(
        os.path.join(transformed_dir, "gta_census_da.geojson")
    )
    for col in ("crime_count", "crime_rate_per_1k"):
        if col in census_gdf.columns:
            census_gdf = census_gdf.drop(columns=col)

    # ── Determine year range ────────────────────────────────────────────
    current_year = datetime.datetime.now().year
    years = range(2020, current_year + 1)

    if verbose:
        logger.info(f"Partitioning into {len(years)} yearly folders (2020–{current_year})...")

    for year in years:
        year_dir = os.path.join(transformed_dir, str(year))
        os.makedirs(year_dir, exist_ok=True)

        year_df = crime_df[crime_df["_year"] == year].drop(columns=["_year"]).copy()

        if year_df.empty:
            if verbose:
                logger.info(f"  {year}: no data — skipping")
            continue

        # 1. Write year-specific unified_data.csv
        year_csv = os.path.join(year_dir, "unified_data.csv")
        year_df.to_csv(year_csv, index=False)
        if verbose:
            logger.info(f"  {year}: {len(year_df):>8,} rows → unified_data.csv")

        # 2. Build year-specific shooting arcs
        build_shooting_arcs(
            crime_df=year_df, output_dir=year_dir, verbose=False
        )
        arcs_path = os.path.join(year_dir, "shooting_arcs.csv")
        if verbose:
            arcs_count = sum(1 for _ in open(arcs_path)) - 1 if os.path.exists(arcs_path) else 0
            logger.info(f"  {year}: {arcs_count:>8,} arcs → shooting_arcs.csv")

        # 3. Re-enrich census with only this year's crime points
        enrich_census_with_crime_rate(
            crime_df=year_df,
            census_gdf=census_gdf,
            output_dir=year_dir,
            verbose=False,
        )
        if verbose:
            logger.info(f"  {year}: gta_census_da.geojson (re-enriched)")

        # 4. Build standalone compact variants for this year
        build_standalone_compact(source_dir=year_dir, verbose=False)
        if verbose:
            logger.info(f"  {year}: standalone/ compact variants built")

    # Drop our temp column from the in-memory frame (defensive)
    if "_year" in crime_df.columns:
        crime_df.drop(columns=["_year"], inplace=True)

    if verbose:
        logger.info("Year partitioning complete.")


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
    partition_all_years()
