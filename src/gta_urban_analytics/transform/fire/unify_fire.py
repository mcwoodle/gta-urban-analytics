"""
Fire Incident Unifier
=====================
Loads each region's raw fire-incident CSV and standardises it into the
``fire_unified_schema`` — the fire-side analogue of ``unify_datasets`` for crime.

Sources:
  - Toronto Fire Services (CKAN) — the rich feed: incident type, responding
    station, dollar loss, personnel.
  - Brampton BFES residential fires 2012-2016 (ArcGIS) — residential-only and a
    closed historical window, so it has no responding station / dollar loss /
    personnel; it contributes points (and a generic ``incident_type``) only.

Reuses the crime unifier's coordinate sanity box and municipality normaliser so
fire and crime share one notion of "valid GTA point" and one municipality label.

Output: data/02_transformed/fire_incidents.csv
"""

import os
import logging

import numpy as np
import pandas as pd

from gta_urban_analytics.schemas import (
    toronto_fire_schema,
    brampton_fire_incident_schema,
    fire_unified_schema,
)
from gta_urban_analytics.transform.crime.unify_datasets import (
    _null_out_of_bounds_coords,
    _normalize_municipality,
)

logger = logging.getLogger(__name__)

_project_root = os.path.normpath(
    os.path.join(os.path.dirname(__file__), "..", "..", "..", "..")
)


def _unify_toronto(df: pd.DataFrame) -> pd.DataFrame:
    """Standardise raw Toronto Fire Incidents into the unified fire columns."""
    toronto_fire_schema.validate(df)

    dates = pd.to_datetime(df.get("TFS_Alarm_Time"), errors="coerce").dt.strftime("%Y-%m-%d")
    station = df.get("Incident_Station_Area", pd.Series(dtype=str)).astype(str).str.strip()
    station = station.replace({"nan": "", "0": ""})

    return pd.DataFrame({
        "source_file_name": "Toronto_Fire_Incidents",
        "source_identifier": "TorontoFire_"
        + df.get("Incident_Number", df.index.to_series().astype(str)).astype(str),
        "region": "Toronto",
        "municipality": "Toronto",
        "incident_type": df.get("Final_Incident_Type", pd.Series(dtype=str)).astype(str).str.strip(),
        "station_area": station,
        "occurrence_date": dates,
        "lat": df.get("Latitude"),
        "lon": df.get("Longitude"),
        "estimated_dollar_loss": df.get("Estimated_Dollar_Loss"),
        "responding_personnel": df.get("Number_of_responding_personnel"),
    })


def _unify_brampton(df: pd.DataFrame) -> pd.DataFrame:
    """Standardise raw Brampton residential fire incidents into the unified columns.

    These are all residential structure fires, so ``incident_type`` is the
    constant ``"Residential Fire"``; the feed carries no responding station,
    dollar loss, or personnel. ``DATE_`` is ``YY/MM/DD``.
    """
    brampton_fire_incident_schema.validate(df)

    dates = pd.to_datetime(
        df.get("DATE_"), format="%y/%m/%d", errors="coerce"
    ).dt.strftime("%Y-%m-%d")
    fire_id = df.get("FIRE", df.index.to_series().astype(str)).astype(str).str.strip()

    return pd.DataFrame({
        "source_file_name": "Brampton_Residential_Fire_Incidents",
        "source_identifier": "BramptonFire_" + fire_id,
        "region": "Peel",
        "municipality": "Brampton",
        "incident_type": "Residential Fire",
        "station_area": None,
        "occurrence_date": dates,
        "lat": df.get("lat"),
        "lon": df.get("lon"),
        "estimated_dollar_loss": np.nan,
        "responding_personnel": np.nan,
    })


def unify_fire(
    raw_dir: str | None = None,
    output_dir: str | None = None,
    fire_df: pd.DataFrame | None = None,
    brampton_df: pd.DataFrame | None = None,
    verbose: bool = True,
) -> pd.DataFrame:
    """Unify raw fire incidents into the standardised fire schema.

    Parameters:
        raw_dir:    Directory holding the raw fire CSVs. Defaults to
                    ``data/01_raw/``.
        output_dir: Where to write ``fire_incidents.csv``. Defaults to
                    ``data/02_transformed/``.
        fire_df:    Pre-loaded raw Toronto frame (tests); skips the disk read.
        brampton_df: Pre-loaded raw Brampton frame (tests). When ``fire_df`` is
                    passed (test mode) the Brampton CSV is NOT read from disk, so
                    tests stay deterministic regardless of what's downloaded.
        verbose:    Log progress.
    """
    if raw_dir is None:
        raw_dir = os.path.join(_project_root, "data", "01_raw")
    if output_dir is None:
        output_dir = os.path.join(_project_root, "data", "02_transformed")

    all_dfs = []

    # --- Toronto Fire Services ---
    if fire_df is not None:
        toronto_raw = fire_df.copy()
    else:
        src = os.path.join(raw_dir, "Toronto_Fire_Incidents.csv")
        if not os.path.exists(src):
            raise FileNotFoundError(
                f"Missing {src}. Run extract.fire.toronto.download_toronto_fire_data() first."
            )
        if verbose:
            logger.info(f"Processing Toronto fire incidents: {src}")
        toronto_raw = pd.read_csv(src, low_memory=False)
    all_dfs.append(_unify_toronto(toronto_raw))

    # --- Brampton BFES residential fires (optional; appended when present) ---
    if brampton_df is None and fire_df is None:
        bsrc = os.path.join(raw_dir, "Brampton_Fire_Incidents.csv")
        if os.path.exists(bsrc):
            if verbose:
                logger.info(f"Processing Brampton residential fire incidents: {bsrc}")
            brampton_df = pd.read_csv(bsrc, low_memory=False)
    if brampton_df is not None:
        all_dfs.append(_unify_brampton(brampton_df))

    if not all_dfs:
        logger.info("No fire data frames to concatenate.")
        return pd.DataFrame()

    unified = pd.concat(all_dfs, ignore_index=True)

    # Reuse the crime pipeline's GTA box (nulls (0,0) / out-of-bounds) and drop
    # rows we can't place — fire has no separate invalid-row quarantine step.
    unified = _null_out_of_bounds_coords(unified)
    before = len(unified)
    unified = unified.dropna(subset=["lat", "lon"]).reset_index(drop=True)
    dropped = before - len(unified)
    if dropped and verbose:
        logger.info(f"Dropped {dropped:,} fire incidents with missing/out-of-bounds coordinates.")

    unified["municipality"] = unified["municipality"].map(_normalize_municipality)
    fire_unified_schema.validate(unified)

    os.makedirs(output_dir, exist_ok=True)
    out_path = os.path.join(output_dir, "fire_incidents.csv")
    if verbose:
        logger.info(f"Writing {len(unified):,} fire incidents to {out_path}")
    unified.to_csv(out_path, index=False)

    return unified


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
    unify_fire()
