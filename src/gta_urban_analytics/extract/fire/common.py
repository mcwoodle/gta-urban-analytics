"""Shared helpers for the municipal fire extractors.

Unlike Toronto (CKAN datastore dump, see ``toronto.py``), the other GTA
municipalities publish fire data as ArcGIS **FeatureServer query** endpoints —
the same mechanism Peel/Halton crime use. Requesting ``f=geojson`` makes ArcGIS
reproject every source CRS (Web Mercator, UTM 17N, …) to WGS84, so the lat/lon
columns the paginated downloader derives from the geometry are always 4326.
"""

import os

from gta_urban_analytics.extract.arcgis.paginated import download_paginated_geojson


def raw_dir() -> str:
    """Resolve (and create) the shared ``data/01_raw`` directory."""
    output_dir = os.path.normpath(
        os.path.join(os.path.dirname(__file__), "..", "..", "..", "..", "data", "01_raw")
    )
    os.makedirs(output_dir, exist_ok=True)
    return output_dir


def download_feature_layer(url: str, filename: str, label: str, *, skip_if_present: bool = True):
    """Download an ArcGIS FeatureServer query endpoint to ``data/01_raw/filename``.

    Station locations and closed historical incident sets rarely change, so by
    default an existing file is left in place (mirrors the Toronto station skip).
    """
    path = os.path.join(raw_dir(), filename)
    if skip_if_present and os.path.exists(path):
        print(f"{label} already exists at {path}. Skipping.\n")
        return
    download_paginated_geojson(url, path, label)
