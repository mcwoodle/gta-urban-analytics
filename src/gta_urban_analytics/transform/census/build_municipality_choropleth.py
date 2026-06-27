"""
Municipality Crime-Rate Choropleth
==================================
Builds a *municipality*-level (city/town) crime-rate polygon layer — a much
simpler read than the ~8,500 Dissemination Areas: one polygon per GTA
municipality (Toronto, Newmarket, Aurora, Vaughan, …), each carrying total and
per-crime-group per-capita rates.

We have no off-the-shelf municipality boundary file, so municipalities are built
by **dissolving the census DAs**:

  1. Spatially join reference-year crime points into the DA polygons and give
     each DA the *modal* municipality of the crime points it contains (the crime
     feed already labels every incident with a municipality).
  2. DAs that contain no crime points are filled from their nearest assigned DA.
  3. Dissolve DA geometry by municipality and sum DA population — this is the
     municipality polygon + denominator.
  4. Count each crime point toward the municipality of the DA it fell in (so the
     numerator and the population denominator share one grouping), split by
     `crime_group`, and divide by population for per-1,000 rates.

`selected_rate` / `selected_count` start equal to the totals; the viz control
recomputes them client-side when the user picks a subset of crime groups (the
per-group rates are additive over a shared population denominator).

Output: data/02_transformed/gta_municipalities.geojson
"""

import os
import logging

import geopandas as gpd
import pandas as pd

from gta_urban_analytics.transform.crime.crime_groups import GROUP_SLUGS

logger = logging.getLogger(__name__)

_project_root = os.path.normpath(
    os.path.join(os.path.dirname(__file__), "..", "..", "..", "..")
)

# Labels that are not real municipalities — dropped from the choropleth.
_NON_MUNICIPALITIES = {"Outside Region", "Outside", "Cmn", ""}


def _assign_da_municipality(
    das: gpd.GeoDataFrame, crime_points: gpd.GeoDataFrame
) -> pd.Series:
    """Return a Series (index = DA row index) of each DA's municipality.

    A DA's municipality is the modal `municipality` of the crime points within
    it; DAs with no crime points are filled from their nearest assigned DA.
    """
    joined = gpd.sjoin(
        crime_points[["municipality", "geometry"]],
        das[["geometry"]],
        how="inner",
        predicate="within",
    )
    # Modal municipality per DA (index_right is the DA's positional index).
    modal = (
        joined.groupby("index_right")["municipality"]
        .agg(lambda s: s.value_counts().idxmax())
    )

    muni = pd.Series(index=das.index, dtype="object")
    muni.loc[modal.index] = modal.values

    # Nearest-assigned fill for DAs with no contained crime points.
    unassigned = muni.isna()
    if unassigned.any() and (~unassigned).any():
        centroids = das.geometry.to_crs(epsg=26917).centroid
        assigned_pts = gpd.GeoDataFrame(
            {"municipality": muni[~unassigned].values},
            geometry=centroids[~unassigned].values,
            crs="EPSG:26917",
        )
        target_pts = gpd.GeoDataFrame(
            geometry=centroids[unassigned].values, crs="EPSG:26917"
        )
        nearest = gpd.sjoin_nearest(target_pts, assigned_pts, how="left")
        # sjoin_nearest can emit duplicate ties; keep the first per target.
        nearest = nearest[~nearest.index.duplicated(keep="first")]
        muni.loc[das.index[unassigned]] = nearest["municipality"].values

    return muni


def build_municipality_choropleth(
    crime_df: pd.DataFrame | None = None,
    census_gdf: gpd.GeoDataFrame | None = None,
    output_dir: str | None = None,
    reference_year: int | None = None,
    verbose: bool = True,
) -> gpd.GeoDataFrame:
    """Build the per-municipality crime-rate choropleth GeoJSON.

    Parameters mirror ``enrich_census_with_crime_rate``: pass pre-loaded frames
    (per-year partitioner) or let it read the transformed files from disk.
    """
    if output_dir is None:
        output_dir = os.path.join(_project_root, "data", "02_transformed")
    out_path = os.path.join(output_dir, "gta_municipalities.geojson")

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

    # --- Crime points (lat/lon + municipality + crime_group) ---
    base_cols = ["lat", "lon", "municipality"]
    if reference_year is not None:
        base_cols.append("occurrence_date")
    if crime_df is not None:
        cols = base_cols + (["crime_group"] if "crime_group" in crime_df.columns else [])
        cdf = crime_df[cols].copy()
    else:
        crime_csv = os.path.join(output_dir, "unified_data.csv")
        if not os.path.exists(crime_csv):
            raise FileNotFoundError(
                f"Missing {crime_csv}. Run the unify/filter/deduplicate steps first."
            )
        if verbose:
            logger.info("Loading unified crime points...")
        available = pd.read_csv(crime_csv, nrows=0).columns
        cols = base_cols + (["crime_group"] if "crime_group" in available else [])
        cdf = pd.read_csv(crime_csv, usecols=cols, low_memory=False)

    cdf = cdf.dropna(subset=["lat", "lon"])
    if reference_year is not None:
        years = pd.to_datetime(cdf["occurrence_date"], errors="coerce").dt.year
        cdf = cdf[years == reference_year]
    cdf["municipality"] = cdf["municipality"].astype(str).str.strip()
    if "crime_group" not in cdf.columns:
        cdf["crime_group"] = "Other"

    crime_points = gpd.GeoDataFrame(
        cdf,
        geometry=gpd.points_from_xy(cdf["lon"], cdf["lat"]),
        crs="EPSG:4326",
    )

    # --- 1+2. Assign every DA a municipality ---
    if verbose:
        logger.info("Assigning DAs to municipalities (modal crime label + NN fill)...")
    das["municipality"] = _assign_da_municipality(das, crime_points)
    das = das[das["municipality"].notna()]
    das = das[~das["municipality"].isin(_NON_MUNICIPALITIES)]

    # --- 3. Dissolve DA geometry by municipality + sum population ---
    if verbose:
        logger.info("Dissolving DAs into municipality polygons...")
    polygons = das.dissolve(by="municipality", aggfunc={"Population": "sum"})
    polygons = polygons.reset_index()

    # Dissolving keeps every DA vertex (~7 MB for 27 polygons). Simplify in a
    # metric CRS — 60 m is invisible at the city-wide zoom this layer renders at.
    utm = polygons.to_crs(epsg=26917)
    utm["geometry"] = utm.geometry.simplify(tolerance=60, preserve_topology=True)
    polygons = utm.to_crs(epsg=4326)

    # --- 4. Count crime points toward the municipality of the DA they fell in ---
    joined = gpd.sjoin(
        crime_points[["crime_group", "geometry"]],
        das[["municipality", "geometry"]],
        how="inner",
        predicate="within",
    )
    total_counts = joined.groupby("municipality").size().rename("crime_count")
    out = polygons.merge(total_counts, on="municipality", how="left")
    out["crime_count"] = out["crime_count"].fillna(0).astype(int)

    pop = out["Population"].replace(0, pd.NA)
    out["crime_rate_per_1k"] = (out["crime_count"] / pop * 1000).astype(float)

    for group, slug in GROUP_SLUGS.items():
        c = (
            joined[joined["crime_group"] == group]
            .groupby("municipality")
            .size()
            .rename(f"crime_count_{slug}")
        )
        out = out.merge(c, on="municipality", how="left")
        out[f"crime_count_{slug}"] = out[f"crime_count_{slug}"].fillna(0).astype(int)
        out[f"crime_rate_{slug}_per_1k"] = (
            out[f"crime_count_{slug}"] / pop * 1000
        ).astype(float)

    # selected_* drive the (initially Total) choropleth; the viz recomputes them.
    out["selected_count"] = out["crime_count"]
    out["selected_rate"] = out["crime_rate_per_1k"]

    # Round rates for a tidy, lighter file.
    rate_cols = [c for c in out.columns if c.endswith("_per_1k") or c == "selected_rate"]
    for c in rate_cols:
        out[c] = out[c].round(3)

    # Label anchor (UTM-accurate centroid → lat/lon).
    cents = out.geometry.to_crs(epsg=26917).centroid.to_crs(epsg=4326)
    out["centroid_lat"] = cents.y
    out["centroid_lon"] = cents.x

    out = out.set_geometry("geometry")
    if out.crs is None:
        out = out.set_crs(epsg=4326)

    os.makedirs(output_dir, exist_ok=True)
    if os.path.exists(out_path):
        os.remove(out_path)
    out.to_file(out_path, driver="GeoJSON")

    if verbose:
        valid = out["crime_rate_per_1k"].dropna()
        logger.info(
            f"Wrote {len(out)} municipalities to {out_path}. "
            f"crime_rate_per_1k: median={valid.median():.1f}, max={valid.max():.1f}."
        )

    return out


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
    build_municipality_choropleth(reference_year=2025)
