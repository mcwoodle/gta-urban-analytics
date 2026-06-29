"""Orchestrate all fire-service downloads. Toronto only for now; add more
municipalities here as their feeds are integrated."""

from gta_urban_analytics.extract.fire.toronto import download_toronto_fire_data


def download_fire():
    """Download all fire-service datasets into data/01_raw/."""
    print("Starting fire-service downloads...")
    download_toronto_fire_data()
    print("Fire-service downloads complete.")


if __name__ == "__main__":
    download_fire()
