import urllib.request
import urllib.parse
import json
import os
import csv
from datetime import date

def download_peel_crime_data(output_prefix="Peel_Police_Service_Incidents"):
    output_dir = "dataSetDownloads"
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)
        
    current_date = date.today().strftime("%Y-%m-%d")
    output_filename = f"{output_prefix}_{current_date}.csv"
    output_path = os.path.join(output_dir, output_filename)
    print(f"Starting download of Peel Region Crime Data...")
    
    # This URL and layer was reverse-engineered from the ArcGIS Experience Builder map.
    # The map queries services.arcgis.com under the org 'w0dAT1ctgtKwxvde'.
    # Specifically, the 'Experience_gdb' FeatureServer layer 0 contains the 'Ecrimes' data.
    base_url = "https://services.arcgis.com/w0dAT1ctgtKwxvde/ArcGIS/rest/services/Experience_gdb/FeatureServer/0/query"
    
    offset = 0
    record_count = 2000 # Max typical for ArcGIS REST
    all_features = []
    
    while True:
        print(f"Fetching records {offset} to {offset + record_count - 1}...")
        
        params = {
            "where": "1=1",
            "outFields": "*",
            "f": "geojson",
            "resultOffset": offset,
            "resultRecordCount": record_count
        }
        
        url = f"{base_url}?{urllib.parse.urlencode(params)}"
        
        req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
        with urllib.request.urlopen(req) as response:
            data = json.loads(response.read().decode('utf-8'))
            
            features = data.get("features", [])
            all_features.extend(features)
            print(f"Retrieved {len(features)} records. Total: {len(all_features)}")
            
            # Check if there's more data to fetch
            if data.get("properties", {}).get("exceededTransferLimit") is True:
                offset += record_count
            else:
                break

    # Build the CSV
    print(f"Saving {len(all_features)} records to {output_path}...")
    
    if all_features:
        # Extract headers from the first feature's properties, and add lat/lon
        headers = list(all_features[0].get("properties", {}).keys())
        headers.extend(["lat", "lon"])
        
        with open(output_path, "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=headers)
            writer.writeheader()
            
            for feature in all_features:
                row = feature.get("properties", {}).copy()
                geom = feature.get("geometry")
                if geom and geom.get("type") == "Point" and geom.get("coordinates"):
                    coords = geom.get("coordinates")
                    if len(coords) >= 2:
                        row["lon"] = coords[0]
                        row["lat"] = coords[1]
                
                # Make sure all fields match headers (in case some properties are missing)
                clean_row = {k: row.get(k) for k in headers}
                writer.writerow(clean_row)
        
    print("Download complete!")

if __name__ == "__main__":
    download_peel_crime_data()
