import os
from datetime import date
from gta_urban_analytics.extract.arcgis.hub import download_arcgis_hub_csv
from gta_urban_analytics.extract.arcgis.paginated import download_paginated_geojson

CENSUS_DIVISION_ID = 3520

def download_toronto_data():
    output_dir = os.path.join(os.path.dirname(__file__), '..', '..', '..', 'data', '01_raw')
    output_dir = os.path.normpath(output_dir)
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)

    # Historical data (2014 - end of previous year), ~160 MB, skip if already present
    hist_filename = "Toronto_Major_Crime_Indicators.csv"
    hist_path = os.path.join(output_dir, hist_filename)
    if not os.path.exists(hist_path):
        hist_api = "https://hub.arcgis.com/api/download/v1/items/0a239a5563a344a3bbf8452504ed8d68/csv?redirect=false&layers=0"
        download_arcgis_hub_csv(hist_api, hist_path, "Toronto Major Crime Indicators")
    else:
        print(f"Historical data already exists at {hist_path}. Skipping.\n")

    # Year-to-date data (current year, refreshed daily). Published as a plain
    # FeatureServer (TPS Crime App YTD) with no Hub export, so use the
    # paginated query helper.
    current_date = date.today().strftime("%Y-%m-%d")
    ytd_filename = f"Toronto_YTD_to_{current_date}.csv"
    ytd_path = os.path.join(output_dir, ytd_filename)
    ytd_api = "https://services.arcgis.com/S9th0jAJ7bqgIRjw/ArcGIS/rest/services/YTD_CRIME_WM/FeatureServer/0/query"
    download_paginated_geojson(ytd_api, ytd_path, "Toronto Crime Data (Year-to-Date)")

if __name__ == "__main__":
    download_toronto_data()
