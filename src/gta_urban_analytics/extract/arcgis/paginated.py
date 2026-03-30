import urllib.request
import urllib.parse
import json
import os
import csv

def download_paginated_geojson(base_url, output_path, data_label):
    print(f"Starting download of {data_label} from Experience Builder map...")
    
    offset = 0
    record_count = 2000
    all_features = []
    
    while True:
        # Use end='\r' to keep output on the same line
        print(f"Fetching {record_count} records of {len(all_features)}", end="\r", flush=True)
        
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
            
            # Check if there's more data to fetch
            if data.get("properties", {}).get("exceededTransferLimit") is True:
                offset += record_count
            else:
                print(f"\nFinal count: {len(all_features)} records retrieved.")
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
        
    print(f"Download complete for {data_label}!\n")
