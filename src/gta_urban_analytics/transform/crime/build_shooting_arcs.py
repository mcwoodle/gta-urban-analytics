"""
Shooting Arcs Builder
=====================
Produces `data/02_transformed/shooting_arcs.csv` — one row per shooting-style
incident, paired with the centroid of its municipality. Used by the Kepler
arc layer in the visualization sub-project.

Depends on:
  - data/02_transformed/unified_data.csv  (Step 3)

Output columns:
  id, src_lat, src_lon, dst_lat, dst_lon, year, municipality, count_in_muni
"""

import os
import logging

import pandas as pd

logger = logging.getLogger(__name__)

_project_root = os.path.normpath(
    os.path.join(os.path.dirname(__file__), "..", "..", "..", "..")
)

# Match anything that looks like a shooting or firearm offense.
_SHOOTING_REGEX = r"(?i)shoot|firearm"


def build_shooting_arcs(
    crime_df: pd.DataFrame | None = None,
    output_dir: str | None = None,
    verbose: bool = True,
) -> pd.DataFrame:
    """Build the shooting-arcs CSV for the Kepler arc layer.

    Parameters:
        crime_df:   Pre-loaded crime DataFrame.  When *None* (default) the
                    full ``unified_data.csv`` is read from disk.
        output_dir: Directory to write ``shooting_arcs.csv`` into.  Defaults
                    to ``data/02_transformed/``.
        verbose:    Log progress messages.

    Returns:
        The output DataFrame (same content as the written CSV).
    """
    if output_dir is None:
        output_dir = os.path.join(_project_root, "data", "02_transformed")
    output_csv = os.path.join(output_dir, "shooting_arcs.csv")

    if crime_df is None:
        crime_csv = os.path.join(_project_root, "data", "02_transformed", "unified_data.csv")
        if not os.path.exists(crime_csv):
            raise FileNotFoundError(
                f"Missing {crime_csv}. Run the unify/filter/deduplicate steps first."
            )
        if verbose:
            logger.info("Loading unified crime data...")
        df = pd.read_csv(
            crime_csv,
            usecols=[
                "mapped_crime_category",
                "original_crime_type",
                "occurrence_date",
                "lat",
                "lon",
                "municipality",
            ],
            low_memory=False,
        )
    else:
        needed = {"mapped_crime_category", "original_crime_type",
                  "occurrence_date", "lat", "lon", "municipality"}
        df = crime_df[list(needed & set(crime_df.columns))].copy()

    # Require coordinates and municipality to be able to emit an arc at all.
    df = df.dropna(subset=["lat", "lon", "municipality"])
    df = df[df["municipality"].astype(str).str.strip() != ""]

    # Compute each municipality's centroid from ALL crime points (not just shootings)
    # — a robust approximation of the municipality's population-weighted centre.
    if verbose:
        logger.info("Computing municipality centroids...")
    muni_centroids = (
        df.groupby("municipality")
        .agg(
            dst_lat=("lat", "mean"),
            dst_lon=("lon", "mean"),
            count_in_muni=("lat", "size"),
        )
        .reset_index()
    )

    if verbose:
        logger.info("Filtering for shooting / firearm incidents...")
    original = df["original_crime_type"].fillna("").astype(str)
    mapped = df["mapped_crime_category"].fillna("").astype(str)
    shooting_mask = original.str.contains(_SHOOTING_REGEX, regex=True, na=False) | (
        mapped == "Weapons"
    )
    shootings = df[shooting_mask].copy()

    if verbose:
        logger.info(f"Found {len(shootings):,} shooting/firearm incidents.")

    # Parse year from the ISO date string.
    shootings["year"] = (
        pd.to_datetime(shootings["occurrence_date"], errors="coerce").dt.year
    )
    shootings = shootings.dropna(subset=["year"])
    shootings["year"] = shootings["year"].astype(int)

    # Join centroids.
    merged = shootings.merge(muni_centroids, on="municipality", how="inner")

    # Reshape to the arc layer's expected schema.
    out = pd.DataFrame({
        "id": range(len(merged)),
        "src_lat": merged["lat"].values,
        "src_lon": merged["lon"].values,
        "dst_lat": merged["dst_lat"].values,
        "dst_lon": merged["dst_lon"].values,
        "year": merged["year"].values,
        "municipality": merged["municipality"].values,
        "count_in_muni": merged["count_in_muni"].astype(int).values,
    })

    os.makedirs(output_dir, exist_ok=True)
    if verbose:
        logger.info(f"Writing {len(out):,} arcs to {output_csv}")
    out.to_csv(output_csv, index=False)
    return out


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
    build_shooting_arcs()
