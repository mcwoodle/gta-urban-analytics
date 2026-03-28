import requests
import zipfile
import io
import os
from pathlib import Path

def download_statcan_census_data():
    # URL for the 2021 Census Profile at the DA level from https://www12.statcan.gc.ca/census-recensement/2021/geo/sip-pis/boundary-limites/index2021-eng.cfm?year=21
    # Get the exact URL by right-clicking the "Continue" button on StatCan's site and selecting "Copy Link Address".
    da_census_url = "https://www12.statcan.gc.ca/census-recensement/2021/geo/sip-pis/boundary-limites/files-fichiers/lda_000b21a_e.zip"
    
    # Walk up from src/gta_crime_data/extract/statcan/ to the project root
    project_root = Path(__file__).resolve().parents[4]
    raw_data_path = project_root / "data" / "01_raw" / "statcan_census"
    raw_data_path.mkdir(parents=True, exist_ok=True)
    
    _download_statcan_bulk_census(da_census_url, raw_data_path)

def _download_statcan_bulk_census(census_url: str, output_dir: Path):
    """
    Downloads a massive StatCan bulk ZIP file into memory and 
    extracts the CSVs directly into your raw data folder.
    """
    print(f"Downloading from Statistics Canada: {census_url}")
    
    # Send the GET request to the static ZIP URL
    response = requests.get(census_url)
    response.raise_for_status()  # Stop the pipeline if the download fails
    
    print("Download complete. Extracting CSV files from ZIP...")
    
    # Read the downloaded bytes in memory (so we don't save a useless .zip file)
    with zipfile.ZipFile(io.BytesIO(response.content)) as z:
        # Extract all files within the zip directly to your data folder
        z.extractall(output_dir)
        
    print(f"Extraction complete! Census CSVs are ready in {output_dir}")

if __name__ == "__main__":
    download_statcan_census_data()
