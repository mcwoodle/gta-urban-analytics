import os
from gta_urban_analytics.extract.arcgis.hub import download_arcgis_hub_csv

CENSUS_DIVISION_ID = 3518

DURHAM_DATASETS = [
    {"category": "Drug Violations",                "raw_csv_file": "Durham_Drug_Violations.csv",                "arcgis_id": "e0f56f8938c04215895b4c99d86e335f"},
    {"category": "Robbery",                        "raw_csv_file": "Durham_Robbery.csv",                        "arcgis_id": "b33ed02277c24547888da0499870642a"},
    {"category": "Break and Enter",                "raw_csv_file": "Durham_Break_and_Enter.csv",                "arcgis_id": "6c6af417d0464c868a1453f98261d617"},
    {"category": "Theft Over 5000",                "raw_csv_file": "Durham_Theft_Over_5000.csv",                "arcgis_id": "58bbaf779764480494b40a2b8574e950"},
    {"category": "Assaults",                       "raw_csv_file": "Durham_Assaults.csv",                       "arcgis_id": "9f58177248f84afaa61b328b2b876f2e"},
    {"category": "Auto Theft",                     "raw_csv_file": "Durham_Auto_Theft.csv",                     "arcgis_id": "b01c5558122943b090ef4b3916f6f60c"},
    {"category": "Shootings and Firearm Discharge", "raw_csv_file": "Durham_Shootings_and_Firearm_Discharge.csv", "arcgis_id": "1f7e2a19732740f29e26dc7a7395080c"},
]

def download_durham_data():
    output_dir = os.path.join(os.path.dirname(__file__), '..', '..', '..', 'data', '01_raw')
    output_dir = os.path.normpath(output_dir)
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)

    print("Starting download of Durham Region Crime Data...\n")
    for entry in DURHAM_DATASETS:
        filename = entry["raw_csv_file"]
        item_id = entry["arcgis_id"]
        category = entry["category"]
        
        output_path = os.path.join(output_dir, filename)
        api_url = f"https://hub.arcgis.com/api/download/v1/items/{item_id}/csv?redirect=false&layers=0"
        download_arcgis_hub_csv(api_url, output_path, category)
        
    print("All Durham data successfully downloaded into data/01_raw/!")

if __name__ == "__main__":
    download_durham_data()
