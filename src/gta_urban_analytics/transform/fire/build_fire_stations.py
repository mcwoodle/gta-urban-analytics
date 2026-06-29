"""
Fire Station Volume
===================
The headline "how many fires did each station handle?" product. Every Toronto
fire incident carries the responding ``Incident_Station_Area`` (→ ``station_area``
in the unified fire data); grouping on it and joining to the 85 fire-station
points gives one point per station carrying ``fires_handled`` + ``total_dollar_loss``.

The station CSV's ``STATION`` number is the join key. Station areas with no
matching physical station (e.g. mutual-aid / unknown) are reported as a small
"unmatched" summary in the log but dropped from the point layer.

Output: data/02_transformed/fire_stations.geojson
"""

import os
import json
import logging

import geopandas as gpd
import pandas as pd

logger = logging.getLogger(__name__)

_project_root = os.path.normpath(
    os.path.join(os.path.dirname(__file__), "..", "..", "..", "..")
)


def _norm_station(s: pd.Series) -> pd.Series:
    """Normalise a station-number column to a clean string key. Reading a CSV
    column that mixes integers with blanks yields floats, so "115" comes back as
    "115.0" — strip the trailing ".0" (and surrounding whitespace) so the incident
    station areas and the station numbers join."""
    return (
        s.astype(str)
        .str.strip()
        .str.replace(r"\.0$", "", regex=True)
    )


def _parse_point(geom_str):
    """Extract (lon, lat) from a GeoJSON Point string in the station CSV."""
    try:
        coords = json.loads(geom_str)["coordinates"]
        return float(coords[0]), float(coords[1])
    except (TypeError, ValueError, KeyError, json.JSONDecodeError):
        return (None, None)


def build_fire_stations(
    raw_dir: str | None = None,
    output_dir: str | None = None,
    fire_df: pd.DataFrame | None = None,
    stations_df: pd.DataFrame | None = None,
    verbose: bool = True,
) -> gpd.GeoDataFrame:
    """Build the per-station fires-handled point layer.

    Parameters:
        raw_dir:     Holds ``Toronto_Fire_Stations.csv``. Defaults to data/01_raw/.
        output_dir:  Holds ``fire_incidents.csv`` and receives the output GeoJSON.
                     Defaults to data/02_transformed/.
        fire_df:     Pre-loaded unified fire frame (tests).
        stations_df: Pre-loaded raw stations frame (tests).
        verbose:     Log progress.
    """
    if raw_dir is None:
        raw_dir = os.path.join(_project_root, "data", "01_raw")
    if output_dir is None:
        output_dir = os.path.join(_project_root, "data", "02_transformed")

    # --- Unified fire incidents (station_area + dollar loss) ---
    if fire_df is None:
        fire_csv = os.path.join(output_dir, "fire_incidents.csv")
        if not os.path.exists(fire_csv):
            raise FileNotFoundError(f"Missing {fire_csv}. Run unify_fire() first.")
        fire_df = pd.read_csv(fire_csv, low_memory=False)
    fire = fire_df.copy()
    fire["station_area"] = _norm_station(fire["station_area"])
    fire = fire[fire["station_area"].ne("") & fire["station_area"].ne("nan")]

    grouped = (
        fire.groupby("station_area")
        .agg(
            fires_handled=("station_area", "size"),
            total_dollar_loss=("estimated_dollar_loss", "sum"),
        )
        .reset_index()
    )

    # --- Station locations ---
    if stations_df is None:
        stations_csv = os.path.join(raw_dir, "Toronto_Fire_Stations.csv")
        if not os.path.exists(stations_csv):
            raise FileNotFoundError(
                f"Missing {stations_csv}. Run download_toronto_fire_data() first."
            )
        stations_df = pd.read_csv(stations_csv, low_memory=False)
    stations = stations_df.copy()
    stations["station"] = _norm_station(stations["STATION"])
    lonlat = stations["geometry"].apply(_parse_point)
    stations["lon"] = [p[0] for p in lonlat]
    stations["lat"] = [p[1] for p in lonlat]

    merged = stations.merge(
        grouped, left_on="station", right_on="station_area", how="left"
    )
    merged["fires_handled"] = merged["fires_handled"].fillna(0).astype(int)
    merged["total_dollar_loss"] = merged["total_dollar_loss"].fillna(0.0).round(0)

    # Report station areas in the incidents that didn't match a physical station.
    matched = set(stations["station"])
    unmatched = grouped[~grouped["station_area"].isin(matched)]
    if verbose and not unmatched.empty:
        logger.info(
            f"{len(unmatched)} incident station-area(s) had no matching station "
            f"(e.g. mutual-aid/unknown), covering "
            f"{int(unmatched['fires_handled'].sum()):,} incidents — dropped from the layer."
        )

    out = gpd.GeoDataFrame(
        merged[
            [
                "station",
                "MUNICIPALITY_NAME",
                "ADDRESS",
                "fires_handled",
                "total_dollar_loss",
                "lat",
                "lon",
            ]
        ].rename(columns={"MUNICIPALITY_NAME": "municipality", "ADDRESS": "address"}),
        geometry=gpd.points_from_xy(merged["lon"], merged["lat"]),
        crs="EPSG:4326",
    )
    out = out[out.geometry.notna() & out.geometry.is_valid]

    os.makedirs(output_dir, exist_ok=True)
    out_path = os.path.join(output_dir, "fire_stations.geojson")
    if os.path.exists(out_path):
        os.remove(out_path)
    out.to_file(out_path, driver="GeoJSON")

    if verbose:
        logger.info(
            f"Wrote {len(out)} stations to {out_path}. "
            f"fires_handled: total={int(out['fires_handled'].sum()):,}, "
            f"max={int(out['fires_handled'].max())}."
        )

    return out


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
    build_fire_stations()
