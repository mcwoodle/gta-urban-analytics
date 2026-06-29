"""
Fire-Rate Choropleth (Dissemination Area)
=========================================
Per-capita fire-incident rate per census DA — the fire analogue of the crime-rate
enrichment. Reuses the DA geometry + population from ``gta_census_da.geojson`` but
writes a SEPARATE top-level ``fire_da.geojson`` so it stays independent of the
crime-enriched, year-partitioned census file (fire data is Toronto-only and not
year-partitioned, like ``coordinate_anomalies``).

Mirrors ``enrich_with_crime_rate``: point-in-polygon count → ``fire_count`` and
``fire_rate_per_1k``, nulling small-population DAs to avoid noisy spikes.

Output: data/02_transformed/fire_da.geojson
"""

import os
import logging

import geopandas as gpd
import pandas as pd

logger = logging.getLogger(__name__)

_project_root = os.path.normpath(
    os.path.join(os.path.dirname(__file__), "..", "..", "..", "..")
)

# Same small-DA guard the crime enrichment uses.
_MIN_POPULATION_FOR_RATE = 50


def build_fire_choropleth(
    fire_df: pd.DataFrame | None = None,
    census_gdf: gpd.GeoDataFrame | None = None,
    output_dir: str | None = None,
    verbose: bool = True,
) -> gpd.GeoDataFrame:
    """Build the per-DA fire-rate choropleth GeoJSON.

    Parameters:
        fire_df:    Pre-loaded unified fire frame (needs ``lat``/``lon``); reads
                    ``fire_incidents.csv`` when None.
        census_gdf: Pre-loaded DA frame (needs ``DAUID``, ``Population``,
                    geometry); reads ``gta_census_da.geojson`` when None.
        output_dir: Output dir (also holds the inputs). Defaults to
                    data/02_transformed/.
        verbose:    Log progress.
    """
    if output_dir is None:
        output_dir = os.path.join(_project_root, "data", "02_transformed")
    out_path = os.path.join(output_dir, "fire_da.geojson")

    # --- Census DAs (geometry + population only) ---
    if census_gdf is not None:
        das = census_gdf.copy()
    else:
        census_geojson = os.path.join(output_dir, "gta_census_da.geojson")
        if not os.path.exists(census_geojson):
            raise FileNotFoundError(
                f"Missing {census_geojson}. Run build_gta_census_geojson() first."
            )
        if verbose:
            logger.info("Loading census Dissemination Areas...")
        das = gpd.read_file(census_geojson)
    if das.crs is None or das.crs.to_epsg() != 4326:
        das = das.to_crs(epsg=4326)
    das = das[["DAUID", "Population", "geometry"]].copy()
    das["Population"] = pd.to_numeric(das["Population"], errors="coerce")

    # --- Fire incident points ---
    if fire_df is not None:
        fire = fire_df[["lat", "lon"]].dropna(subset=["lat", "lon"]).copy()
    else:
        fire_csv = os.path.join(output_dir, "fire_incidents.csv")
        if not os.path.exists(fire_csv):
            raise FileNotFoundError(f"Missing {fire_csv}. Run unify_fire() first.")
        if verbose:
            logger.info("Loading unified fire points...")
        fire = pd.read_csv(fire_csv, usecols=["lat", "lon"], low_memory=False).dropna(
            subset=["lat", "lon"]
        )

    points = gpd.GeoDataFrame(
        fire,
        geometry=gpd.points_from_xy(fire["lon"], fire["lat"]),
        crs="EPSG:4326",
    )

    if verbose:
        logger.info("Running point-in-polygon join...")
    joined = gpd.sjoin(points, das[["DAUID", "geometry"]], how="inner", predicate="within")
    counts = joined.groupby("DAUID").size().rename("fire_count").reset_index()

    enriched = das.merge(counts, on="DAUID", how="left")
    enriched["fire_count"] = enriched["fire_count"].fillna(0).astype(int)

    pop = pd.to_numeric(enriched["Population"], errors="coerce")
    rate = enriched["fire_count"] / pop * 1000
    too_small = pop < _MIN_POPULATION_FOR_RATE
    enriched["fire_rate_per_1k"] = rate.where(~too_small).round(3)
    enriched.loc[too_small, "fire_count"] = pd.NA

    enriched = enriched.set_geometry("geometry")
    if enriched.crs is None:
        enriched = enriched.set_crs(epsg=4326)

    os.makedirs(output_dir, exist_ok=True)
    if os.path.exists(out_path):
        os.remove(out_path)
    enriched.to_file(out_path, driver="GeoJSON")

    if verbose:
        valid = enriched["fire_rate_per_1k"].dropna()
        logger.info(
            f"Wrote {len(enriched):,} DAs to {out_path}. "
            f"fire_rate_per_1k: median={valid.median():.2f}, max={valid.max():.2f}, "
            f"n_valid={len(valid):,}."
        )

    return enriched


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
    build_fire_choropleth()
