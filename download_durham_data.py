import os
from download_arcgis_hub_data import download_arcgis_hub_csv

def download_durham_data():
    output_dir = "dataSetDownloads"
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)

    datasets = {
        "Durham_Drug_Violations.csv": "e0f56f8938c04215895b4c99d86e335f",
        "Durham_Robbery.csv": "b33ed02277c24547888da0499870642a",
        "Durham_Break_and_Enter.csv": "6c6af417d0464c868a1453f98261d617",
        "Durham_Theft_Over_5000.csv": "58bbaf779764480494b40a2b8574e950",
        "Durham_Assaults.csv": "9f58177248f84afaa61b328b2b876f2e",
        "Durham_Auto_Theft.csv": "b01c5558122943b090ef4b3916f6f60c",
        "Durham_Shootings_and_Firearm_Discharge.csv": "1f7e2a19732740f29e26dc7a7395080c"
    }

    print("Starting download of Durham Region Crime Data...\n")
    for filename, item_id in datasets.items():
        output_path = os.path.join(output_dir, filename)
        api_url = f"https://hub.arcgis.com/api/download/v1/items/{item_id}/csv?redirect=false&layers=0"
        download_arcgis_hub_csv(api_url, output_path, filename.replace(".csv", "").replace("_", " "))
    print("All Durham data successfully downloaded into dataSetDownloads/!")

if __name__ == "__main__":
    download_durham_data()
