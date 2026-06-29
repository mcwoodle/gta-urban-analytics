"""City of Markham fire-station extract (City of Markham Open Data).

Station locations only. This is the dataset ArcGIS item
``02532059bb684e40baa15313b8ab3bb3`` points at — owned by the City of Markham
(``maps.markham.ca``), so it is Markham's 9 stations, not York Region as a whole
(York fire is municipal; no region-wide open station feed exists yet).

The direct ``maps.markham.ca`` service requires a token, so we go through the
public ArcGIS proxy for the item. Source CRS is UTM 17N; ``f=geojson`` returns
WGS84.
"""

from gta_urban_analytics.extract.fire.common import download_feature_layer

STATIONS_URL = (
    "https://utility.arcgis.com/usrsvcs/servers/"
    "02532059bb684e40baa15313b8ab3bb3/rest/services/OpenData/"
    "OD_FIRE_STN/FeatureServer/0/query"
)
STATIONS_FILENAME = "Markham_Fire_Stations.csv"


def download_markham_fire_data():
    """Download Markham fire-station locations into data/01_raw/."""
    download_feature_layer(STATIONS_URL, STATIONS_FILENAME, "Markham Fire Stations")


if __name__ == "__main__":
    download_markham_fire_data()
