"""
CKAN open-data downloader (City of Toronto Open Data Portal).

Toronto publishes fire data through a CKAN portal rather than the ArcGIS Hub
export API the police feeds use. Datastore-active resources expose a streaming
``/datastore/dump/<resource_id>`` endpoint that returns the full resource as a
single file (CSV for tabular data, GeoJSON for spatial) — far simpler than
paging ``datastore_search``.

Hardened like ``extract/arcgis/hub.py``: a request timeout, retry on transient
network errors, and chunked streaming to disk for large files.
"""

import time
import urllib.request
from urllib.error import HTTPError, URLError

_CKAN_BASE = "https://ckan0.cf.opendata.inter.prod-toronto.ca"
_TIMEOUT_S = 60
_MAX_RETRIES = 5
_RETRY_WAIT_S = 5


def dump_url(resource_id: str, fmt: str = "csv") -> str:
    """Return the CKAN datastore dump URL for a resource id."""
    return f"{_CKAN_BASE}/datastore/dump/{resource_id}?format={fmt}"


def download_ckan_resource(resource_id, output_path, data_label, fmt="csv"):
    """Download a CKAN datastore resource to ``output_path``.

    Retries transient network errors; streams the body to disk in chunks.
    """
    url = dump_url(resource_id, fmt=fmt)
    print(f"Starting download of {data_label} from {url} ...")

    for attempt in range(1, _MAX_RETRIES + 1):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
            with urllib.request.urlopen(req, timeout=_TIMEOUT_S) as response, open(
                output_path, "wb"
            ) as out_file:
                block_size = 8192
                downloaded = 0
                while True:
                    buffer = response.read(block_size)
                    if not buffer:
                        break
                    downloaded += len(buffer)
                    out_file.write(buffer)
            print(f"Download complete! Saved {downloaded / (1024 * 1024):.2f} MB.\n")
            return
        except HTTPError as e:
            print(f"HTTP Error {e.code}: {e.reason} for {data_label}.")
            break  # an HTTP error (404/500) won't fix itself on retry
        except (URLError, TimeoutError) as e:
            print(
                f"Network error ({e}) on attempt {attempt}/{_MAX_RETRIES}; "
                f"retrying in {_RETRY_WAIT_S}s..."
            )
            time.sleep(_RETRY_WAIT_S)

    print(f"Failed to download {data_label} after {_MAX_RETRIES} attempts.\n")
