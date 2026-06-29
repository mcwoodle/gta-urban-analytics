"""
Toronto Fire Services extract (City of Toronto Open Data, CKAN).

Two resources:
  - Fire Incidents          — OFM-reportable fire incidents (~36k rows to 2023)
    with lat/lon, incident type, alarm time, dollar loss, responding apparatus/
    personnel, and the responding `Incident_Station_Area` (drives "fires handled
    per station").
  - Fire Station Locations  — 85 active station/facility points used to place the
    per-station rollup on the map.

This is the first fire source; the module mirrors the per-region crime extractors
so other municipalities can be added later under extract/fire/.
"""

import os

from gta_urban_analytics.extract.ckan import download_ckan_resource

# CKAN datastore-active resource ids (City of Toronto Open Data).
INCIDENTS_RESOURCE_ID = "fa5c7de5-10f8-41cf-883a-9b30a67c7b56"
STATIONS_RESOURCE_ID = "9d1b7352-32ce-4af2-8681-595ce9e47b6e"

# The station resource's datastore dump only supports tabular formats; the CSV
# carries a `geometry` column (a JSON Point string) plus the `STATION` number that
# joins to each incident's `Incident_Station_Area`.
INCIDENTS_FILENAME = "Toronto_Fire_Incidents.csv"
STATIONS_FILENAME = "Toronto_Fire_Stations.csv"


def _raw_dir() -> str:
    output_dir = os.path.normpath(
        os.path.join(os.path.dirname(__file__), "..", "..", "..", "..", "data", "01_raw")
    )
    os.makedirs(output_dir, exist_ok=True)
    return output_dir


def download_toronto_fire_data():
    """Download Toronto fire incidents + station locations into data/01_raw/."""
    output_dir = _raw_dir()

    incidents_path = os.path.join(output_dir, INCIDENTS_FILENAME)
    download_ckan_resource(
        INCIDENTS_RESOURCE_ID, incidents_path, "Toronto Fire Incidents", fmt="csv"
    )

    # Station locations rarely change; skip if already present.
    stations_path = os.path.join(output_dir, STATIONS_FILENAME)
    if not os.path.exists(stations_path):
        download_ckan_resource(
            STATIONS_RESOURCE_ID,
            stations_path,
            "Toronto Fire Station Locations",
            fmt="csv",
        )
    else:
        print(f"Fire station locations already exist at {stations_path}. Skipping.\n")


if __name__ == "__main__":
    download_toronto_fire_data()
