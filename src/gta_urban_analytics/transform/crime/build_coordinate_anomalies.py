"""
Coordinate Anomaly Layer
========================
Flags coordinates that carry an implausibly high number of incidents at the
*exact same* lat/lon — the signature of source-side address/centroid snapping or
placeholder geocoding (audit F-19). For example, one York coordinate carries
~5,000 distinct incidents; "ROADSIDE TEST" incidents pile onto checkpoint points.

The incidents themselves are REAL and distinct, so they are LEFT INTACT in
unified_data.csv and still counted everywhere. This module only emits a *separate*
layer so the visualization can render these points distinctly (flagged anomalies)
instead of letting them masquerade as organic crime hotspots.

Each flagged coordinate is further classified against a curated list of
high-foot-traffic GTA venues (malls, hospitals, attractions, transit hubs — see
``high_traffic_locations``): an anomaly that sits on top of a known venue is at
least partly *organic* (``anomaly_type="high_traffic_area"``), whereas one with no
nearby venue is more likely a pure placeholder/geocoding artifact
(``anomaly_type="unexplained"``). The viz colours the two classes differently.

Depends on:
  - data/02_transformed/unified_data.csv  (Step 3)

Output: data/02_transformed/coordinate_anomalies.csv
Columns: lat, lon, description, anomaly_type, nearest_location, location_category,
         incident_count, top_category, regions, first_date, last_date

``description`` is a plain-English summary of the classification; it (and the
other classification columns) lead the column order so they surface in Kepler's
hover tooltip, which defaults to a dataset's first few fields (audit F-19).
"""

import os
import logging

import pandas as pd

from .high_traffic_locations import classify_coordinate

logger = logging.getLogger(__name__)

_project_root = os.path.normpath(
    os.path.join(os.path.dirname(__file__), "..", "..", "..", "..")
)

# A single identical full-precision coordinate carrying MORE THAN this many
# incidents is treated as a placeholder/snapped location rather than an organic
# hotspot. Tunable — inspect the output and adjust per the data distribution.
_ANOMALY_MIN_INCIDENTS_PER_COORD = 200

_INPUT_COLUMNS = ["lat", "lon", "region", "municipality", "mapped_crime_category", "occurrence_date"]
# Per-coordinate context columns and the high-traffic classification columns.
_CONTEXT_COLUMNS = ["lat", "lon", "incident_count", "regions", "top_category", "first_date", "last_date"]
_CLASS_COLUMNS = ["anomaly_type", "nearest_location", "location_category", "description"]
# Final column order leads with the human-readable description + classification so
# they head Kepler's hover tooltip (which shows a dataset's first few fields).
_OUTPUT_COLUMNS = [
    "lat", "lon", "description", "anomaly_type", "nearest_location", "location_category",
    "incident_count", "top_category", "regions", "first_date", "last_date",
]


def _classify_row(lat: float, lon: float) -> pd.Series:
    """Tag one coordinate as near a known high-traffic venue, or unexplained."""
    match = classify_coordinate(lat, lon)
    if match is None:
        return pd.Series(
            {
                "anomaly_type": "unexplained",
                "nearest_location": "",
                "location_category": "",
                "description": (
                    "Unexplained — no known high-traffic venue nearby; "
                    "likely placeholder/snapped geocoding"
                ),
            }
        )
    loc, _dist = match
    return pd.Series(
        {
            "anomaly_type": "high_traffic_area",
            "nearest_location": loc.name,
            "location_category": loc.category,
            "description": (
                f"High-traffic area — near {loc.name} ({loc.category}); "
                "incidents are likely organic"
            ),
        }
    )


def build_coordinate_anomalies(
    crime_df: pd.DataFrame | None = None,
    output_dir: str | None = None,
    threshold: int = _ANOMALY_MIN_INCIDENTS_PER_COORD,
    verbose: bool = True,
) -> pd.DataFrame:
    """Emit the coordinate-anomaly layer.

    Parameters:
        crime_df:   Pre-loaded crime DataFrame. When *None* the full
                    ``unified_data.csv`` is read from disk.
        output_dir: Directory to write ``coordinate_anomalies.csv`` into.
                    Defaults to ``data/02_transformed/``.
        threshold:  Minimum incident count at one identical coordinate to flag it.
        verbose:    Log progress messages.

    Returns:
        The output DataFrame (same content as the written CSV).
    """
    if output_dir is None:
        output_dir = os.path.join(_project_root, "data", "02_transformed")
    output_csv = os.path.join(output_dir, "coordinate_anomalies.csv")

    if crime_df is None:
        crime_csv = os.path.join(_project_root, "data", "02_transformed", "unified_data.csv")
        if not os.path.exists(crime_csv):
            raise FileNotFoundError(
                f"Missing {crime_csv}. Run the unify/filter/deduplicate steps first."
            )
        if verbose:
            logger.info("Loading unified crime data...")
        df = pd.read_csv(crime_csv, usecols=_INPUT_COLUMNS, low_memory=False)
    else:
        df = crime_df[[c for c in _INPUT_COLUMNS if c in crime_df.columns]].copy()

    df = df.dropna(subset=["lat", "lon"])

    # Count incidents per exact coordinate; keep only those above the threshold.
    counts = df.groupby(["lat", "lon"]).size().rename("incident_count")
    flagged = counts[counts > threshold]

    os.makedirs(output_dir, exist_ok=True)

    if flagged.empty:
        out = pd.DataFrame(columns=_OUTPUT_COLUMNS)
        out.to_csv(output_csv, index=False)
        if verbose:
            logger.info(f"No coordinates reached the anomaly threshold (> {threshold}). Wrote empty {output_csv}.")
        return out

    # Build context (regions, dominant category, date span) only for flagged coords.
    flagged_keys = flagged.reset_index()[["lat", "lon"]]
    adf = df.merge(flagged_keys, on=["lat", "lon"], how="inner")

    def _join_regions(s: pd.Series) -> str:
        return ",".join(sorted(set(s.dropna().astype(str))))

    def _top_category(s: pd.Series) -> str:
        modes = s.dropna().astype(str).mode()
        return modes.iat[0] if not modes.empty else ""

    meta = (
        adf.groupby(["lat", "lon"])
        .agg(
            regions=("region", _join_regions),
            top_category=("mapped_crime_category", _top_category),
            first_date=("occurrence_date", "min"),
            last_date=("occurrence_date", "max"),
        )
        .reset_index()
    )

    out = (
        flagged.reset_index()
        .merge(meta, on=["lat", "lon"], how="left")
        .sort_values("incident_count", ascending=False)
        .reset_index(drop=True)
    )[_CONTEXT_COLUMNS]

    # Classify each flagged coordinate against known high-traffic venues so the
    # viz can flag organic hotspots (malls/hospitals) apart from unexplained
    # placeholders.
    classes = out.apply(lambda r: _classify_row(r["lat"], r["lon"]), axis=1)
    out = pd.concat([out, classes], axis=1)[_OUTPUT_COLUMNS]

    out.to_csv(output_csv, index=False)
    if verbose:
        n_high = int((out["anomaly_type"] == "high_traffic_area").sum())
        logger.info(
            f"Flagged {len(out):,} placeholder/snapped coordinates (> {threshold} incidents each), "
            f"covering {int(out['incident_count'].sum()):,} incidents "
            f"({n_high:,} near known high-traffic venues, {len(out) - n_high:,} unexplained) "
            f"→ {output_csv}"
        )
    return out


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
    build_coordinate_anomalies()
