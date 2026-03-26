import os
from lib.download_arcgis_paginated_experience_data import download_paginated_geojson

def download_halton_crime_data():
    output_dir = "dataSetDownloads"
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)
        
    output_filename = "Halton_Crime_Map_Data.csv"
    output_path = os.path.join(output_dir, output_filename)
    
    base_url = "https://services2.arcgis.com/o1LYr96CpFkfsDJS/arcgis/rest/services/Crime_Map/FeatureServer/0/query"
    
    download_paginated_geojson(base_url, output_path, "Halton Region Crime Data")

if __name__ == "__main__":
    download_halton_crime_data()
