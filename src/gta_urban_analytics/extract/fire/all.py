"""Orchestrate all fire-service downloads.

Toronto publishes rich incident-level data (CKAN); the other municipalities are
station-location feeds (ArcGIS), except Brampton, which also publishes a closed
2012-2016 residential incident set. Add more municipalities here as their feeds
are integrated.
"""

from gta_urban_analytics.extract.fire.toronto import download_toronto_fire_data
from gta_urban_analytics.extract.fire.mississauga import download_mississauga_fire_data
from gta_urban_analytics.extract.fire.brampton import download_brampton_fire_data
from gta_urban_analytics.extract.fire.markham import download_markham_fire_data


def download_fire():
    """Download all fire-service datasets into data/01_raw/."""
    print("Starting fire-service downloads...")
    download_toronto_fire_data()
    download_mississauga_fire_data()
    download_brampton_fire_data()
    download_markham_fire_data()
    print("Fire-service downloads complete.")


if __name__ == "__main__":
    download_fire()
