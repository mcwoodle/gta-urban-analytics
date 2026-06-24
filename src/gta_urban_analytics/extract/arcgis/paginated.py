"""
Paginated ArcGIS FeatureServer → CSV downloader (Peel, Halton, Toronto YTD).

Hardened per audit F-12:
  - urlopen has a timeout and bounded exponential-backoff retries;
  - pagination stops when a page returns no features (guards against an infinite
    loop when the server keeps reporting exceededTransferLimit with an empty page);
  - CSV headers are the UNION of every feature's property keys (not just the first
    feature's), so columns absent from feature 0 are not silently dropped.

The network-free helpers (`_paginate_features`, `_collect_headers`,
`_feature_to_row`, `_write_features_csv`) are unit-tested.
"""

import urllib.request
import urllib.parse
import json
import csv
import time
from urllib.error import URLError, HTTPError

_TIMEOUT_S = 60
_MAX_RETRIES = 4
_PAGE_SIZE = 2000
_MAX_PAGES = 100_000  # hard stop so a misbehaving server can't loop forever


def _fetch_json(url, timeout=_TIMEOUT_S, max_retries=_MAX_RETRIES):
    """GET a URL and parse JSON, with a timeout and bounded exponential backoff."""
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    last_err = None
    for attempt in range(max_retries):
        try:
            with urllib.request.urlopen(req, timeout=timeout) as response:
                return json.loads(response.read().decode("utf-8"))
        except (URLError, HTTPError, TimeoutError) as e:
            last_err = e
            wait = 2 ** attempt
            print(f"  request failed ({e}); retry {attempt + 1}/{max_retries} in {wait}s...")
            time.sleep(wait)
    raise RuntimeError(f"Failed to fetch {url} after {max_retries} attempts: {last_err}")


def _paginate_features(fetch_page, page_size=_PAGE_SIZE, max_pages=_MAX_PAGES):
    """Accumulate features across pages until the server stops reporting more.

    ``fetch_page(offset, page_size)`` returns a parsed GeoJSON dict. Terminates
    when a page yields no features (avoids an infinite loop when the server keeps
    setting exceededTransferLimit on an empty page) or stops setting
    exceededTransferLimit.
    """
    offset = 0
    all_features = []
    for _ in range(max_pages):
        data = fetch_page(offset, page_size)
        features = data.get("features", [])
        all_features.extend(features)
        exceeded = data.get("properties", {}).get("exceededTransferLimit") is True
        if not features or not exceeded:
            break
        offset += page_size
    return all_features


def _collect_headers(features):
    """Union of every feature's property keys (first-seen order), plus lat/lon."""
    headers, seen = [], set()
    for feat in features:
        for key in feat.get("properties", {}).keys():
            if key not in seen:
                seen.add(key)
                headers.append(key)
    headers.extend(["lat", "lon"])
    return headers


def _feature_to_row(feature, headers):
    """Flatten a GeoJSON feature to a dict keyed by ``headers`` (adds lat/lon)."""
    row = dict(feature.get("properties", {}))
    geom = feature.get("geometry")
    if geom and geom.get("type") == "Point" and geom.get("coordinates"):
        coords = geom.get("coordinates")
        if len(coords) >= 2:
            row["lon"], row["lat"] = coords[0], coords[1]
    return {k: row.get(k) for k in headers}


def _write_features_csv(all_features, output_path):
    """Write features to CSV using union headers. No-op for an empty list."""
    if not all_features:
        return
    headers = _collect_headers(all_features)
    with open(output_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=headers)
        writer.writeheader()
        for feature in all_features:
            writer.writerow(_feature_to_row(feature, headers))


def download_paginated_geojson(base_url, output_path, data_label):
    print(f"Starting download of {data_label} from ArcGIS FeatureServer...")

    def fetch_page(offset, page_size):
        params = {
            "where": "1=1",
            "outFields": "*",
            "f": "geojson",
            "resultOffset": offset,
            "resultRecordCount": page_size,
        }
        url = f"{base_url}?{urllib.parse.urlencode(params)}"
        print(f"Fetching up to {page_size} records (offset {offset})...", end="\r", flush=True)
        return _fetch_json(url)

    all_features = _paginate_features(fetch_page)
    print(f"\nFinal count: {len(all_features)} records retrieved.")

    print(f"Saving {len(all_features)} records to {output_path}...")
    _write_features_csv(all_features, output_path)
    print(f"Download complete for {data_label}!\n")
