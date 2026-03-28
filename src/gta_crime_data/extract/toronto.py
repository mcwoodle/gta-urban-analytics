import os
from gta_crime_data.extract.arcgis.hub import download_arcgis_hub_csv

CENSUS_DIVISION_ID = 3520

def download_toronto_data():
    output_dir = os.path.join(os.path.dirname(__file__), '..', '..', '..', 'data', '01_raw')
    output_dir = os.path.normpath(output_dir)
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)

    filename = "Toronto_Major_Crime_Indicators.csv"
    output_path = os.path.join(output_dir, filename)
    api_url = "https://hub.arcgis.com/api/download/v1/items/0a239a5563a344a3bbf8452504ed8d68/csv?redirect=false&layers=0"
    
    download_arcgis_hub_csv(api_url, output_path, "Toronto Major Crime Indicators")

if __name__ == "__main__":
    download_toronto_data()
