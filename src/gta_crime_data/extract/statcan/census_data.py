import requests
import zipfile
import io
from pathlib import Path
from tqdm.auto import tqdm

def download_statcan_census_data():
    # URL for the 2021 Census Profile at the DA level from https://www12.statcan.gc.ca/census-recensement/2021/geo/sip-pis/boundary-limites/index2021-eng.cfm?year=21
    # Get the exact URL by right-clicking the "Continue" button on StatCan's site and selecting "Copy Link Address".
    da_shapefile_url = "https://www12.statcan.gc.ca/census-recensement/2021/geo/sip-pis/boundary-limites/files-fichiers/lda_000b21a_e.zip"

    ontario_census_url = "https://www12.statcan.gc.ca/census-recensement/2021/dp-pd/prof/details/download-telecharger/comp/GetFile.cfm?Lang=E&FILETYPE=CSV&GEONO=006_Ontario"
    
    # Walk up from src/gta_crime_data/extract/statcan/ to the project root
    project_root = Path(__file__).resolve().parents[4]
    raw_data_path = project_root / "data" / "01_raw" / "statcan_census"
    
    # Check if the primary shapefile already exists to skip download
    expected_shp = raw_data_path / "lda_000b21a_e.shp"
    if not expected_shp.exists():
        raw_data_path.mkdir(parents=True, exist_ok=True)
        _download_statcan_zip(da_shapefile_url, raw_data_path, desc="Downloading Census Shapefiles")
    else:
        print(f"Census shapefiles already exist at {expected_shp}. Skipping download.")
        
    expected_ontario_csv = raw_data_path / "98-401-X2021006_English_CSV_data_Ontario.csv"
    if not expected_ontario_csv.exists():
        raw_data_path.mkdir(parents=True, exist_ok=True)
        _download_statcan_zip(ontario_census_url, raw_data_path, desc="Downloading Ontario Census Data")
    else:
        print(f"Ontario census data already exists at {expected_ontario_csv}. Skipping download.")

def _download_statcan_zip(census_url: str, output_dir: Path, desc: str = "Downloading Census"):
    """
    Streams a massive StatCan bulk ZIP file into memory, displays a 
    dynamic progress bar, and extracts the CSVs directly to the raw data folder.
    """
    print(f"Connecting to Statistics Canada for {desc}...")
    
    # stream=True forces requests to leave the connection open and download in pieces
    response = requests.get(census_url, stream=True)
    response.raise_for_status()
    
    # Ask the server exactly how large the file is (in bytes)
    total_size = int(response.headers.get('content-length', 0))
    
    buffer = io.BytesIO()
    
    # Setup the progress bar
    # unit='iB' and unit_scale=True automatically formats bytes into KB/MB/GB
    with tqdm(total=total_size, unit='iB', unit_scale=True, desc=desc) as progress_bar:
        # Download the file in 1 Megabyte chunks
        for chunk in response.iter_content(chunk_size=1024 * 1024):
            if chunk:  # Filter out keep-alive new chunks
                buffer.write(chunk)
                progress_bar.update(len(chunk))
                
    print("\nDownload complete. Extracting CSV files from ZIP...")
    
    # Extract all files within the zip directly to your data folder
    buffer.seek(0)
    with zipfile.ZipFile(buffer) as z:
        z.extractall(output_dir)
        
    print(f"Extraction complete! Files are ready in {output_dir}")

if __name__ == "__main__":
    download_statcan_census_data()
