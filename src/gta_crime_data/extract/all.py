from gta_crime_data.extract.durham import download_durham_data
from gta_crime_data.extract.halton import download_halton_crime_data
from gta_crime_data.extract.peel import download_peel_crime_data
from gta_crime_data.extract.toronto import download_toronto_data
from gta_crime_data.extract.york import download_york_data


def download():
    """Download all regional crime datasets into data/01_raw/."""
    print("Starting all regional downloads...")
    download_toronto_data()
    download_york_data()
    download_peel_crime_data()
    download_halton_crime_data()
    download_durham_data()
    print("All downloads complete.")


if __name__ == "__main__":
    download()
