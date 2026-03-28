import urllib.request
import json
import time
from urllib.error import HTTPError

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
                elif status in ["Pending", "Processing", "Generating", "ExportingData"]:
                    progress = data.get("progressInPercent")
                    progress_msg = f" ({progress}%)" if progress is not None else ""
                    print(f"Status is {status}{progress_msg}, waiting 5 seconds...")
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
