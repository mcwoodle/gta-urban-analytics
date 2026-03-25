import os
from datetime import date
from download_arcgis_hub_data import download_arcgis_hub_csv

def download_york_data():
    output_dir = "dataSetDownloads"
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)
        
    # Historical data (2021-2025)
    hist_filename = "York_Historical_2021_to_2025.csv"
    hist_path = os.path.join(output_dir, hist_filename)
    if not os.path.exists(hist_path):
        hist_api = "https://hub.arcgis.com/api/download/v1/items/6ba41e1f3bfb4cd9bd0d89843a7d80f5/csv?redirect=false&layers=0"
        download_arcgis_hub_csv(hist_api, hist_path, "York Region Historical Data (2021-2025)")
    else:
        print(f"Historical data already exists at {hist_path}. Skipping.\n")

    # Present data (2025-Present)
    current_date = date.today().strftime("%Y-%m-%d")
    present_filename = f"York_2025_to_{current_date}.csv"
    present_path = os.path.join(output_dir, present_filename)
    present_api = "https://hub.arcgis.com/api/download/v1/items/d89408f3c044424d91ada07cee849d55/csv?redirect=false&layers=0"
    download_arcgis_hub_csv(present_api, present_path, "York Region Crime Data (2025-Present)")

if __name__ == "__main__":
    download_york_data()
