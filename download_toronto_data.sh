#!/bin/bash

# Create output directory
mkdir -p dataSetDownloads

echo "Starting download of Toronto Region Crime Data..."

echo "Downloading Major Crime Indicators..."
wget -q --show-progress "https://hub.arcgis.com/api/download/v1/items/0a239a5563a344a3bbf8452504ed8d68/csv?layers=0" -O "dataSetDownloads/Toronto_Major_Crime_Indicators.csv"

echo "Toronto data successfully downloaded into dataSetDownloads/!"
