import os
from gta_crime_data.extract.arcgis.paginated import download_paginated_geojson

CENSUS_DIVISION_ID = 3524

def download_halton_crime_data():
    output_dir = os.path.join(os.path.dirname(__file__), '..', '..', '..', 'data', '01_raw')
    output_dir = os.path.normpath(output_dir)
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)
        
    output_filename = "Halton_Crime_Map_Data.csv"
    output_path = os.path.join(output_dir, output_filename)
    
    base_url = "https://services2.arcgis.com/o1LYr96CpFkfsDJS/arcgis/rest/services/Crime_Map/FeatureServer/0/query"
    
    download_paginated_geojson(base_url, output_path, "Halton Region Crime Data")

if __name__ == "__main__":
    download_halton_crime_data()
