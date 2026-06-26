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
import numpy as np
import pandas as pd

logger = logging.getLogger(__name__)

_project_root = os.path.normpath(
    os.path.join(os.path.dirname(__file__), "..", "..", "..", "..")
)

# DAs smaller than this threshold produce extremely noisy rates; null them out.
_MIN_POPULATION_FOR_RATE = 50

# Reference year for the top-level (headline) crime rate. All-years counts divided
# by single-year (2021) population were not comparable across regions, whose data
# windows differ wildly (Toronto ~12yr vs Halton ~1yr). 2025 is the only full
# calendar year covered by all five regions, so the headline crime_rate_per_1k is
# computed over 2025 only (audit F-04). Per-year partition folders keep their own
# single-year rates and pass reference_year=None. Revisit as the data grows.
REFERENCE_YEAR = 2025

# --- Bivariate income × crime-rate classification --------------------------
# A bivariate choropleth needs each DA pre-binned into one of 9 classes
# (income tercile × crime-rate tercile). ALL binning happens here in the
# pipeline; the Kepler layer only renders the resulting class. Class index
# k = income_tercile * 3 + rate_tercile (income outer, 0=Lower..2=Higher), then
# encoded as letters A..I so the value is unambiguously categorical (Kepler's
# ordinal colour scale sorts A..I in class order and maps a 9-colour 3×3 palette
# index-for-index). `bivariate_label` carries the human-readable description.
_TERCILE_WORDS = ("Lower", "Mid", "Higher")
_BIVARIATE_LETTERS = "ABCDEFGHI"  # 9 classes, A (class 0) … I (class 8)


def _terciles(values: pd.Series) -> pd.Series:
    """Bin non-null values into 0/1/2 terciles (NaN preserved as NaN).

    Cut points are the 1/3 and 2/3 sample quantiles, so each bin holds roughly
    a third of the DAs. Robust to ties and tiny inputs — degenerate quantiles
    merely collapse bins; nothing raises.
    """
    out = pd.Series(np.nan, index=values.index, dtype="float64")
    numeric = pd.to_numeric(values, errors="coerce")
    valid = numeric.dropna()
    if valid.empty:
        return out
    q1, q2 = valid.quantile([1 / 3, 2 / 3])
    out.loc[valid.index] = np.digitize(valid.to_numpy(), [q1, q2]).astype(float)
    return out


def _assign_bivariate(enriched: gpd.GeoDataFrame) -> None:
    """Add `bivariate_class` (A..I) and `bivariate_label` columns in place.

    A DA is classified only when it has BOTH a median income and a crime rate;
    otherwise both columns are None (Kepler renders the polygon transparent).
    """
    if "Median_Income" in enriched.columns:
        income_t = _terciles(enriched["Median_Income"])
    else:
        income_t = pd.Series(np.nan, index=enriched.index, dtype="float64")
    rate_t = _terciles(enriched["crime_rate_per_1k"])

    both = income_t.notna() & rate_t.notna()
    class_idx = (income_t * 3 + rate_t).where(both)

    enriched["bivariate_class"] = [
        _BIVARIATE_LETTERS[int(k)] if pd.notna(k) else None for k in class_idx
    ]
    enriched["bivariate_label"] = [
        f"{_TERCILE_WORDS[int(i)]}-income · {_TERCILE_WORDS[int(r)]}-crime"
        if b
        else None
        for i, r, b in zip(income_t, rate_t, both)
    ]


def enrich_census_with_crime_rate(
    crime_df: pd.DataFrame | None = None,
    census_gdf: gpd.GeoDataFrame | None = None,
    output_dir: str | None = None,
    reference_year: int | None = None,
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
    for col in ("crime_count", "crime_rate_per_1k", "bivariate_class", "bivariate_label"):
        if col in das.columns:
            das = das.drop(columns=col)

    # --- Load crime points ---
    load_cols = ["lat", "lon"] + (["occurrence_date"] if reference_year is not None else [])
    if crime_df is not None:
        crime_points_df = crime_df[load_cols].dropna(subset=["lat", "lon"]).copy()
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
            crime_csv, usecols=load_cols, low_memory=False
        )
        crime_points_df = crime_points_df.dropna(subset=["lat", "lon"])

    # Restrict to the reference year so cross-region rates are comparable (F-04).
    if reference_year is not None:
        years = pd.to_datetime(
            crime_points_df["occurrence_date"], errors="coerce"
        ).dt.year
        before = len(crime_points_df)
        crime_points_df = crime_points_df[years == reference_year]
        if verbose:
            logger.info(
                f"Restricting crime to reference year {reference_year}: "
                f"{len(crime_points_df):,} of {before:,} points."
            )

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

    # Pre-bin each DA into a bivariate income × crime-rate class for the
    # bivariate-choropleth layer (all binning lives in the pipeline, not the viz).
    _assign_bivariate(enriched)

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
        n_biv = enriched["bivariate_class"].notna().sum()
        logger.info(
            f"Enriched {len(enriched):,} DAs. "
            f"crime_rate_per_1k: median={valid.median():.2f}, "
            f"max={valid.max():.2f}, "
            f"n_valid={len(valid):,}. "
            f"bivariate_class assigned to {n_biv:,} DAs."
        )

    return enriched


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
    enrich_census_with_crime_rate()
