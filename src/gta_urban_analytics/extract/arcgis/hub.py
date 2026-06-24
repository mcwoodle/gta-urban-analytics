"""
ArcGIS Hub CSV-export downloader (Toronto MCI, York, Durham).

Hardened per audit F-12: urlopen calls have a timeout, transient network errors
(URLError/timeout) are retried instead of crashing, polling is bounded so a stuck
export can't loop forever, and explicit Failed/Error statuses end the wait.
"""

import urllib.request
import json
import time
from urllib.error import HTTPError, URLError

_TIMEOUT_S = 60
_POLL_INTERVAL_S = 5
_MAX_POLLS = 180  # ~15 minutes at 5s between checks


def download_arcgis_hub_csv(api_url, output_path, data_label):
    print(f"Starting download of {data_label} to {output_path}...")
    req = urllib.request.Request(api_url, headers={'User-Agent': 'Mozilla/5.0'})

    result_url = None
    for _ in range(_MAX_POLLS):
        print(f"Checking download generation status for {data_label}...")
        try:
            with urllib.request.urlopen(req, timeout=_TIMEOUT_S) as response:
                data = json.loads(response.read().decode('utf-8'))

            status = data.get("status")
            if status == "Completed":
                result_url = data.get("resultUrl")
                print(f"Download is ready for {data_label}!")
                break
            elif status in ("Pending", "Processing", "Generating", "ExportingData"):
                progress = data.get("progressInPercent")
                progress_msg = f" ({progress}%)" if progress is not None else ""
                print(f"Status is {status}{progress_msg}, waiting {_POLL_INTERVAL_S}s...")
                time.sleep(_POLL_INTERVAL_S)
            elif status in ("Failed", "Error"):
                print(f"Export failed for {data_label}: status={status}.")
                break
            else:
                print(f"Unexpected status: {status}")
                break
        except HTTPError as e:
            if e.code == 202:
                # 202 Accepted often means it's still generating.
                print("Generation in progress (202 Accepted). Waiting 5 seconds...")
                time.sleep(_POLL_INTERVAL_S)
            else:
                print(f"HTTP Error {e.code}: {e.reason}")
                break
        except (URLError, TimeoutError) as e:
            print(f"Network error ({e}); retrying in {_POLL_INTERVAL_S}s...")
            time.sleep(_POLL_INTERVAL_S)
    else:
        print(f"Gave up after {_MAX_POLLS} status checks for {data_label}.\n")

    if result_url:
        print(f"Downloading from result URL: {result_url}")
        print(f"Saving to {output_path}...")

        file_req = urllib.request.Request(result_url, headers={'User-Agent': 'Mozilla/5.0'})
        with urllib.request.urlopen(file_req, timeout=_TIMEOUT_S) as file_response, open(output_path, 'wb') as out_file:
            # Read in chunks to handle large files properly.
            block_size = 8192
            downloaded = 0
            while True:
                buffer = file_response.read(block_size)
                if not buffer:
                    break
                downloaded += len(buffer)
                out_file.write(buffer)

        print(f"Download complete! Saved {downloaded / (1024*1024):.2f} MB.\n")
    else:
        print(f"Failed to get download URL for {data_label}.\n")
