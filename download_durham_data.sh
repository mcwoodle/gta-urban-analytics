#!/bin/bash

# Create output directory
mkdir -p dataSetDownloads

echo "Starting download of Durham Region Crime Data..."

echo "Downloading Drug Violations..."
wget -q --show-progress "https://hub.arcgis.com/api/download/v1/items/e0f56f8938c04215895b4c99d86e335f/csv?layers=0" -O "dataSetDownloads/Durham_Drug_Violations.csv"

echo "Downloading Robbery..."
wget -q --show-progress "https://hub.arcgis.com/api/download/v1/items/b33ed02277c24547888da0499870642a/csv?layers=0" -O "dataSetDownloads/Durham_Robbery.csv"

echo "Downloading Break and Enter..."
wget -q --show-progress "https://hub.arcgis.com/api/download/v1/items/6c6af417d0464c868a1453f98261d617/csv?layers=0" -O "dataSetDownloads/Durham_Break_and_Enter.csv"

echo "Downloading Theft Over 5000..."
wget -q --show-progress "https://hub.arcgis.com/api/download/v1/items/58bbaf779764480494b40a2b8574e950/csv?layers=0" -O "dataSetDownloads/Durham_Theft_Over_5000.csv"

echo "Downloading Assaults..."
wget -q --show-progress "https://hub.arcgis.com/api/download/v1/items/9f58177248f84afaa61b328b2b876f2e/csv?layers=0" -O "dataSetDownloads/Durham_Assaults.csv"

echo "Downloading Auto Theft..."
wget -q --show-progress "https://hub.arcgis.com/api/download/v1/items/b01c5558122943b090ef4b3916f6f60c/csv?layers=0" -O "dataSetDownloads/Durham_Auto_Theft.csv"

echo "Downloading Shootings and Firearm Discharge..."
wget -q --show-progress "https://hub.arcgis.com/api/download/v1/items/1f7e2a19732740f29e26dc7a7395080c/csv?layers=0" -O "dataSetDownloads/Durham_Shootings_and_Firearm_Discharge.csv"

echo "All Durham data successfully downloaded into dataSetDownloads/!"
