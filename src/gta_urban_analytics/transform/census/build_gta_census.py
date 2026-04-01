"""
Census Transform
================
Loads StatCan census data and DA boundary shapefiles, filters to the GTA,
and produces a merged GeoJSON with population and income per DA.

Output: data/02_transformed/gta_census_da.geojson
"""

import os
import logging

import geopandas as gpd
import numpy as np
import pandas as pd
from tqdm.auto import tqdm

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
logger = logging.getLogger(__name__)

_project_root = os.path.normpath(
    os.path.join(os.path.dirname(__file__), "..", "..", "..", "..")
)

# CDUIDs that make up the Greater Toronto Area
GTA_CDUIDS = ["3520", "3521", "3519", "3518", "3524"]


def filter_gta_boundaries() -> gpd.GeoDataFrame:
    """Load the Canada-wide DA shapefile, filter to GTA CDUIDs, and reproject to EPSG:4326."""
    shapefile = os.path.join(
        _project_root, "data", "01_raw", "statcan_census", "lda_000b21a_e.shp"
    )

    logger.info("Loading Canada-wide DA boundaries...")
    da_boundaries = gpd.read_file(shapefile)

    logger.info("Clipping boundaries to the GTA...")
    gta_boundaries = da_boundaries[
        da_boundaries["DAUID"].str[:4].isin(GTA_CDUIDS)
    ]

    gta_boundaries = gta_boundaries.to_crs(epsg=4326)
    logger.info(f"Isolated {len(gta_boundaries)} GTA dissemination areas.")
    return gta_boundaries


def load_census_demographics(verbose: bool = True) -> pd.DataFrame:
    """Stream the Ontario census CSV and extract Population + Median Income per DA."""
    csv_path = os.path.join(
        _project_root,
        "data",
        "01_raw",
        "statcan_census",
        "98-401-X2021006_English_CSV_data_Ontario.csv",
    )

    columns_we_need = ["ALT_GEO_CODE", "CHARACTERISTIC_NAME", "C1_COUNT_TOTAL"]
    chunksize = 100_000

    if verbose:
        logger.info("Loading and filtering the Ontario Census CSV data...")

    # Count total lines for progress bar
    with open(csv_path, "rb") as f:
        total_lines = sum(
            buf.count(b"\n") for buf in iter(lambda: f.read(1024 * 1024), b"")
        ) - 1
    total_chunks = (total_lines + chunksize - 1) // chunksize

    filtered_chunks = []
    chunk_iterator = pd.read_csv(
        csv_path,
        usecols=columns_we_need,
        dtype={"ALT_GEO_CODE": str},
        chunksize=chunksize,
        low_memory=False,
        encoding="cp1252",
    )

    iterator = (
        tqdm(chunk_iterator, total=total_chunks, desc="Filtering chunks")
        if verbose
        else chunk_iterator
    )

    for chunk in iterator:
        pop_mask = chunk["CHARACTERISTIC_NAME"] == "Population, 2021"
        income_mask = chunk["CHARACTERISTIC_NAME"].str.contains(
            "Median total income in 2020 among recipients", na=False, regex=False
        )
        filtered_chunks.append(chunk[pop_mask | income_mask])

    if verbose:
        logger.info("Combining filtered chunks...")
    master_filtered_df = pd.concat(filtered_chunks, ignore_index=True)

    if verbose:
        logger.info("Pivoting the final dataset...")
    master_filtered_df["Metric"] = np.where(
        master_filtered_df["CHARACTERISTIC_NAME"] == "Population, 2021",
        "Population",
        "Median_Income",
    )

    clean_demographics = (
        master_filtered_df.pivot_table(
            index="ALT_GEO_CODE",
            columns="Metric",
            values="C1_COUNT_TOTAL",
            aggfunc="first",
        )
        .reset_index()
    )

    clean_demographics["Population"] = pd.to_numeric(
        clean_demographics["Population"], errors="coerce"
    )
    clean_demographics["Median_Income"] = pd.to_numeric(
        clean_demographics["Median_Income"], errors="coerce"
    )

    logger.info("Census demographic table created.")
    return clean_demographics


def build_gta_census_geojson(
    boundaries: gpd.GeoDataFrame | None = None,
    demographics: pd.DataFrame | None = None,
    verbose: bool = True,
) -> gpd.GeoDataFrame:
    """Merge boundaries + demographics, compute centroids, and save GeoJSON.

    Parameters can be passed in (e.g. from a notebook) or will be computed
    automatically when called from the pipeline.
    """
    if boundaries is None:
        boundaries = filter_gta_boundaries()
    if demographics is None:
        demographics = load_census_demographics(verbose=verbose)

    gta_census = boundaries.merge(
        demographics,
        left_on="DAUID",
        right_on="ALT_GEO_CODE",
        how="inner",
    )

    gta_census = gta_census.dropna(subset=["Population"])
    gta_census = gta_census[gta_census["Population"] > 0]

    # Compute centroids in UTM 17N for accuracy, then convert to lat/lon
    centroids = gta_census.geometry.to_crs(epsg=26917).centroid.to_crs(epsg=4326)
    gta_census["centroid_lat"] = centroids.y
    gta_census["centroid_lon"] = centroids.x

    gta_census = gta_census[
        ["DAUID", "Population", "Median_Income", "centroid_lat", "centroid_lon", "geometry"]
    ]

    output_dir = os.path.join(_project_root, "data", "02_transformed")
    os.makedirs(output_dir, exist_ok=True)
    output_path = os.path.join(output_dir, "gta_census_da.geojson")

    gta_census.to_file(output_path, driver="GeoJSON")
    logger.info(
        f"Saved {len(gta_census)} DAs to {output_path} "
        f"(total GTA population: {gta_census['Population'].sum():,.0f})"
    )
    return gta_census
