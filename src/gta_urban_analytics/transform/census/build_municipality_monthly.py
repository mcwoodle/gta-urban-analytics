"""
Monthly Municipality Crime Choropleth
=====================================
Builds a *single* municipality-level GeoJSON that carries **every month's** crime
counts as separate columns, so the standalone-monthly Kepler map can switch month,
mode (single-month vs year-over-year), and metric (absolute vs per-1,000) entirely
client-side from one embedded payload — no per-month files, no network fetch.

Geometry is identical to ``build_municipality_choropleth`` (one polygon per GTA
municipality, built by dissolving the census DAs): the same
``_assign_da_municipality`` + ``_dissolve_to_municipalities`` helpers are reused so
the monthly map lines up pixel-for-pixel with the yearly one.

Scope: months in 2025 + 2026 only — that covers every year-over-year 2026-vs-2025
comparison the viz offers plus single-month views over the recent window.

For each observed month ``YYYY-MM`` the output carries:
  - ``count_YYYY_MM``         — incidents in that municipality that month
  - ``rate_YYYY_MM_per_1k``   — count / population * 1,000 (3 dp)

Column slugs use ``_`` (``count_2026_05``) to stay JS-key / CSV friendly. The viz
derives the list of available months by scanning the ``count_\\d{4}_\\d{2}`` keys —
no separate manifest is needed.

Output: data/02_transformed/standalone/gta_municipalities_monthly.geojson
"""

import os
import logging

import geopandas as gpd
import pandas as pd

from gta_urban_analytics.transform.census.build_municipality_choropleth import (
    _assign_da_municipality,
    _dissolve_to_municipalities,
    _NON_MUNICIPALITIES,
)

logger = logging.getLogger(__name__)

_project_root = os.path.normpath(
    os.path.join(os.path.dirname(__file__), "..", "..", "..", "..")
)

# Months are partitioned for these years only (the viz's YoY mode pairs each 2026
# month with its 2025 twin).
_MONTHLY_YEARS = (2025, 2026)


def build_municipality_monthly(
    crime_df: pd.DataFrame | None = None,
    census_gdf: gpd.GeoDataFrame | None = None,
    output_dir: str | None = None,
    years: tuple[int, ...] = _MONTHLY_YEARS,
    verbose: bool = True,
) -> gpd.GeoDataFrame:
    """Build the per-month municipality crime GeoJSON.

    Parameters mirror ``build_municipality_choropleth``: pass pre-loaded frames
    (tests / partitioner) or let it read the transformed files from disk. The
    output is written to ``<output_dir>/standalone/`` since it only feeds the
    standalone-monthly single-file map.
    """
    if output_dir is None:
        output_dir = os.path.join(_project_root, "data", "02_transformed")
    standalone_dir = os.path.join(output_dir, "standalone")
    out_path = os.path.join(standalone_dir, "gta_municipalities_monthly.geojson")

    # --- Census DAs (geometry + population) ---
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
    das = das.reset_index(drop=True)
    das["Population"] = pd.to_numeric(das["Population"], errors="coerce").fillna(0)

    # --- Crime points (lat/lon + municipality + occurrence_date) ---
    cols = ["lat", "lon", "municipality", "occurrence_date"]
    if crime_df is not None:
        cdf = crime_df[cols].copy()
    else:
        crime_csv = os.path.join(output_dir, "unified_data.csv")
        if not os.path.exists(crime_csv):
            raise FileNotFoundError(
                f"Missing {crime_csv}. Run the unify/filter/deduplicate steps first."
            )
        if verbose:
            logger.info("Loading unified crime points...")
        cdf = pd.read_csv(crime_csv, usecols=cols, low_memory=False)

    cdf = cdf.dropna(subset=["lat", "lon"])
    dates = pd.to_datetime(cdf["occurrence_date"], errors="coerce")
    cdf = cdf[dates.dt.year.isin(years)].copy()
    cdf["month"] = dates[dates.dt.year.isin(years)].dt.strftime("%Y_%m").values
    cdf = cdf[cdf["month"].notna()]
    cdf["municipality"] = cdf["municipality"].astype(str).str.strip()

    crime_points = gpd.GeoDataFrame(
        cdf,
        geometry=gpd.points_from_xy(cdf["lon"], cdf["lat"]),
        crs="EPSG:4326",
    ).reset_index(drop=True)

    # --- Assign every DA a municipality (stable across months) ---
    if verbose:
        logger.info("Assigning DAs to municipalities (modal crime label + NN fill)...")
    das["municipality"] = _assign_da_municipality(das, crime_points)
    das = das[das["municipality"].notna()]
    das = das[~das["municipality"].isin(_NON_MUNICIPALITIES)]

    # --- Dissolve DA geometry by municipality + sum population ---
    if verbose:
        logger.info("Dissolving DAs into municipality polygons...")
    out = _dissolve_to_municipalities(das)

    # --- Count crime points toward the municipality of the DA they fell in ---
    joined = gpd.sjoin(
        crime_points[["month", "geometry"]],
        das[["municipality", "geometry"]],
        how="inner",
        predicate="within",
    )
    joined = joined[~joined["municipality"].isin(_NON_MUNICIPALITIES)]

    pop = out["Population"].replace(0, pd.NA)

    # month → per-municipality count, pivoted so each month is its own column.
    counts = (
        joined.groupby(["municipality", "month"]).size().rename("n").reset_index()
    )
    months = sorted(counts["month"].unique())
    if verbose:
        logger.info(f"Observed {len(months)} months: {months[0]}..{months[-1]}")

    pivot = (
        counts.pivot(index="municipality", columns="month", values="n")
        .reindex(columns=months)
        .fillna(0)
        .astype(int)
    )

    for m in months:
        merged = out.merge(
            pivot[m].rename(f"count_{m}"), on="municipality", how="left"
        )
        out[f"count_{m}"] = merged[f"count_{m}"].fillna(0).astype(int).values
        out[f"rate_{m}_per_1k"] = (
            (out[f"count_{m}"] / pop * 1000).astype(float).round(3)
        )

    out = out.set_geometry("geometry")
    if out.crs is None:
        out = out.set_crs(epsg=4326)

    os.makedirs(standalone_dir, exist_ok=True)
    if os.path.exists(out_path):
        os.remove(out_path)
    out.to_file(out_path, driver="GeoJSON")

    if verbose:
        logger.info(
            f"Wrote {len(out)} municipalities × {len(months)} months to {out_path}."
        )

    return out


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
    build_municipality_monthly()
