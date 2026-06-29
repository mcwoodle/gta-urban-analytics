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

Other GTA municipalities (Mississauga, Brampton, Markham) publish station
**locations** but no per-station incident counts, so they are appended as points
with ``has_volume = False`` and null ``fires_handled``/``total_dollar_loss`` —
they extend station coverage on the map without faking a zero-volume reading.

Output: data/02_transformed/fire_stations.geojson
"""

import os
import json
import logging

import geopandas as gpd
import numpy as np
import pandas as pd

logger = logging.getLogger(__name__)

_project_root = os.path.normpath(
    os.path.join(os.path.dirname(__file__), "..", "..", "..", "..")
)

# Municipal station-location feeds with no per-station volume data. Each raw CSV
# comes from the ArcGIS GeoJSON download (so lat/lon are present); ``station_col``
# is the station-number/id and ``address_cols`` are joined (space-separated) into
# a single address string.
_MUNICIPAL_STATIONS = [
    {
        "municipality": "Mississauga", "region": "Peel",
        "filename": "Mississauga_Fire_Stations.csv",
        "station_col": "UNITID", "address_cols": ["STNO", "STNAME", "SUFFIX"],
    },
    {
        "municipality": "Brampton", "region": "Peel",
        "filename": "Brampton_Fire_Stations.csv",
        "station_col": "FIRE_STATION_NUMBER", "address_cols": ["FIRE_STN_ADDRESS"],
    },
    {
        "municipality": "Markham", "region": "York",
        "filename": "Markham_Fire_Stations.csv",
        "station_col": "LABEL", "address_cols": ["ADDRESS"],
    },
]

# Final column order shared by the Toronto (with-volume) and municipal layers.
_OUTPUT_COLUMNS = [
    "station", "region", "municipality", "address",
    "fires_handled", "total_dollar_loss", "has_volume", "lat", "lon",
]


def _build_municipal_layer(raw_df: pd.DataFrame, cfg: dict) -> gpd.GeoDataFrame:
    """Turn a raw municipal station CSV into the shared station-point schema.

    No incident volume is available for these municipalities, so ``fires_handled``
    and ``total_dollar_loss`` are null and ``has_volume`` is False.
    """
    df = raw_df.copy().reset_index(drop=True)
    station = _norm_station(df[cfg["station_col"]])

    address_parts = []
    for col in cfg["address_cols"]:
        part = df.get(col, pd.Series([""] * len(df))).astype(str).str.strip()
        address_parts.append(part.replace({"nan": "", "None": ""}))
    address = address_parts[0]
    for part in address_parts[1:]:
        address = (address + " " + part).str.strip()
    address = address.str.replace(r"\s+", " ", regex=True).str.strip()

    out = gpd.GeoDataFrame(
        {
            "station": station,
            "region": cfg["region"],
            "municipality": cfg["municipality"],
            "address": address,
            "fires_handled": np.nan,
            "total_dollar_loss": np.nan,
            "has_volume": False,
            "lat": pd.to_numeric(df.get("lat"), errors="coerce"),
            "lon": pd.to_numeric(df.get("lon"), errors="coerce"),
        },
        geometry=gpd.points_from_xy(
            pd.to_numeric(df.get("lon"), errors="coerce"),
            pd.to_numeric(df.get("lat"), errors="coerce"),
        ),
        crs="EPSG:4326",
    )
    return out[out.geometry.notna() & out.geometry.is_valid]


def _load_municipal_stations(raw_dir: str, verbose: bool) -> list[gpd.GeoDataFrame]:
    """Build municipal station layers for every configured CSV present in raw_dir."""
    layers = []
    for cfg in _MUNICIPAL_STATIONS:
        path = os.path.join(raw_dir, cfg["filename"])
        if not os.path.exists(path):
            continue
        raw = pd.read_csv(path, low_memory=False)
        layer = _build_municipal_layer(raw, cfg)
        if verbose:
            logger.info(f"Added {len(layer)} {cfg['municipality']} station points (no volume data).")
        layers.append(layer)
    return layers


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
    municipal_station_dfs: dict[str, pd.DataFrame] | None = None,
    verbose: bool = True,
) -> gpd.GeoDataFrame:
    """Build the per-station fires-handled point layer.

    Toronto stations carry ``fires_handled`` (``has_volume = True``); the other
    municipalities are appended as station points with null volume.

    Parameters:
        raw_dir:     Holds ``Toronto_Fire_Stations.csv`` (+ municipal station
                     CSVs). Defaults to data/01_raw/.
        output_dir:  Holds ``fire_incidents.csv`` and receives the output GeoJSON.
                     Defaults to data/02_transformed/.
        fire_df:     Pre-loaded unified fire frame (tests).
        stations_df: Pre-loaded raw Toronto stations frame (tests). When passed
                     (test mode) the municipal station CSVs are NOT read from
                     disk, keeping tests deterministic.
        municipal_station_dfs: Pre-loaded raw municipal station frames keyed by
                     municipality name (tests), e.g. ``{"Brampton": df}``.
        verbose:     Log progress.
    """
    if raw_dir is None:
        raw_dir = os.path.join(_project_root, "data", "01_raw")
    if output_dir is None:
        output_dir = os.path.join(_project_root, "data", "02_transformed")

    # Capture test mode now: ``stations_df`` is reassigned to the loaded Toronto
    # frame below, so we can't use it to detect injection after that point.
    stations_injected = stations_df is not None

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

    merged["region"] = "Toronto"
    merged["has_volume"] = True
    toronto = gpd.GeoDataFrame(
        merged.rename(columns={"MUNICIPALITY_NAME": "municipality", "ADDRESS": "address"})[
            _OUTPUT_COLUMNS
        ],
        geometry=gpd.points_from_xy(merged["lon"], merged["lat"]),
        crs="EPSG:4326",
    )
    toronto = toronto[toronto.geometry.notna() & toronto.geometry.is_valid]

    # --- Municipal station-location feeds (no per-station volume) ---
    municipal_layers = []
    if municipal_station_dfs is not None:
        cfg_by_name = {c["municipality"]: c for c in _MUNICIPAL_STATIONS}
        for name, raw in municipal_station_dfs.items():
            municipal_layers.append(_build_municipal_layer(raw, cfg_by_name[name]))
    elif not stations_injected:
        # Production: read whatever municipal CSVs were downloaded.
        municipal_layers = _load_municipal_stations(raw_dir, verbose)

    out = gpd.GeoDataFrame(
        pd.concat([toronto, *municipal_layers], ignore_index=True),
        crs="EPSG:4326",
    )

    os.makedirs(output_dir, exist_ok=True)
    out_path = os.path.join(output_dir, "fire_stations.geojson")
    if os.path.exists(out_path):
        os.remove(out_path)
    out.to_file(out_path, driver="GeoJSON")

    if verbose:
        with_vol = out[out["has_volume"]]
        logger.info(
            f"Wrote {len(out)} stations to {out_path} "
            f"({len(with_vol)} with volume, {len(out) - len(with_vol)} location-only). "
            f"fires_handled: total={int(with_vol['fires_handled'].sum()):,}, "
            f"max={int(with_vol['fires_handled'].max())}."
        )

    return out


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
    build_fire_stations()
