"""Brampton Fire & Emergency Services extract (Brampton GeoHub).

Two feeds:
  - Fire Stations (BFES)                  — 14 station points (number + address).
  - Residential Fire Incidents 2012-2016  — 758 per-incident points with cause,
    area of origin, ignition source and object ignited. This is the first
    non-Toronto incident feed; it is residential-only and a closed historical
    window (no dollar loss / no responding-station field), so it feeds the fire
    hexbin / per-DA rate but NOT the per-station "fires handled" volume metric.

Both are ArcGIS FeatureServer query endpoints; ``f=geojson`` returns WGS84. The
incident service name contains spaces, so the path is percent-encoded.
"""

from gta_urban_analytics.extract.fire.common import download_feature_layer

STATIONS_URL = (
    "https://services3.arcgis.com/rl7ACuZkiFsmDA2g/arcgis/rest/services/"
    "BFES_Fire_Stations/FeatureServer/0/query"
)
INCIDENTS_URL = (
    "https://services3.arcgis.com/rl7ACuZkiFsmDA2g/arcgis/rest/services/"
    "BFES%20Residential%20Fire%20Incidents%202012%20to%202016/FeatureServer/0/query"
)
STATIONS_FILENAME = "Brampton_Fire_Stations.csv"
INCIDENTS_FILENAME = "Brampton_Fire_Incidents.csv"


def download_brampton_fire_data():
    """Download Brampton fire stations + residential incidents into data/01_raw/."""
    download_feature_layer(STATIONS_URL, STATIONS_FILENAME, "Brampton Fire Stations")
    # The 2012-2016 incident set is closed/historical, so skip if already present.
    download_feature_layer(
        INCIDENTS_URL, INCIDENTS_FILENAME, "Brampton Residential Fire Incidents (2012-2016)"
    )


if __name__ == "__main__":
    download_brampton_fire_data()
