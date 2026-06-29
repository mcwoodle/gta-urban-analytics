"""Mississauga Fire & Emergency Services extract (City of Mississauga Open Data).

Station locations only — Mississauga does not publish open incident-level fire
data. The "City Fire Stations" feed is a fire-only slice of the city's landmark
service, so it carries a wide attribute set (name, unit id, ward, address); the
unifier keeps just the station-point columns. Source CRS is Web Mercator, but the
GeoJSON request returns WGS84 (see ``common.py``).

ArcGIS item ``e84a2af2c2c6489cbd42086769df9b5e`` — note the layer id is **5**.
"""

from gta_urban_analytics.extract.fire.common import download_feature_layer

STATIONS_URL = (
    "https://services6.arcgis.com/hM5ymMLbxIyWTjn2/arcgis/rest/services/"
    "City_Fire_Stations/FeatureServer/5/query"
)
STATIONS_FILENAME = "Mississauga_Fire_Stations.csv"


def download_mississauga_fire_data():
    """Download Mississauga fire-station locations into data/01_raw/."""
    download_feature_layer(STATIONS_URL, STATIONS_FILENAME, "Mississauga Fire Stations")


if __name__ == "__main__":
    download_mississauga_fire_data()
