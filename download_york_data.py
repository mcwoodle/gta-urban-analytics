import urllib.request
import json
import time
import os
from urllib.error import HTTPError
from datetime import date

def download_arcgis_hub_csv(api_url, output_path, data_label):
    print(f"Starting download of {data_label} to {output_path}...")
    req = urllib.request.Request(api_url, headers={'User-Agent': 'Mozilla/5.0'})
    
    result_url = None
    while not result_url:
        print(f"Checking download generation status for {data_label}...")
        try:
            with urllib.request.urlopen(req) as response:
                data = json.loads(response.read().decode('utf-8'))
                
                status = data.get("status")
                if status == "Completed":
                    result_url = data.get("resultUrl")
                    print(f"Download is ready for {data_label}!")
                elif status in ["Pending", "Processing", "Generating"]:
                    print(f"Status is {status}, waiting 5 seconds...")
                    time.sleep(5)
                else:
                    print(f"Unexpected status: {status}")
                    break
        except HTTPError as e:
            if e.code == 202:
                # 202 Accepted often means it's generating
                print("Generation in progress (202 Accepted). Waiting 5 seconds...")
                time.sleep(5)
            else:
                print(f"HTTP Error {e.code}: {e.reason}")
                break

    if result_url:
        print(f"Downloading from result URL: {result_url}")
        print(f"Saving to {output_path}...")
        
        # Download the actual file
        file_req = urllib.request.Request(result_url, headers={'User-Agent': 'Mozilla/5.0'})
        with urllib.request.urlopen(file_req) as file_response, open(output_path, 'wb') as out_file:
            # Read in chunks to handle large files properly
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
