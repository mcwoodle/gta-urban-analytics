# York Region Crime Data Analysis

Analysis of York Regional Police (YRP) occurrence data from 2021–2025, covering all nine municipalities in York Region.

## Data

**Source:** `Occurrence_2021-2025.csv` — ~177,000 crime occurrence records published by YRP.

**Fields:** Unique ID, occurrence detail, location code, district, municipality, special grouping (violent crime), shooting flag, hate crime flag, status (Solved/Closed/Open), occurrence type, dates, time, and UTM coordinates (Zone 17N).

**Municipalities:** Aurora, East Gwillimbury, Georgina, King, Markham, Newmarket, Richmond Hill, Vaughan, Whitchurch-Stouffville.

## Analyses

The script produces **10 analyses**, each in both **unfiltered** and **filtered** (anomaly locations removed) versions:

| # | Analysis | Description |
|---|---|---|
| 1 | Incidents by Municipality | Total counts per municipality per year |
| 2 | Incidents by Municipality × Crime Type | Breakdown by `Occurrence Type` |
| 3 | Per-Capita Rate | Incidents per 1,000 residents (2021 Census) |
| 4 | Violent Crime Rate | Violent crime per 1,000 residents |
| 5 | Property vs Person Crime | Category breakdown (property / person / other) |
| 6 | Year-over-Year Change | % change between consecutive years |
| 7 | Status / Clearance Rate | Solved / Closed / Open breakdown + solve rate |
| 8 | Location Type Distribution | Residence / Business / Outdoor split |
| 9 | Shootings & Hate Crimes | Counts per municipality per year |
| 10 | Anomaly-Adjacent Summary | How many incidents were near filtered locations |

### Anomaly Location Filtering

To provide a balanced view, incidents within **500 m** of high-traffic community locations are removed. Filtered locations include:

- **Malls:** Upper Canada Mall, Hillcrest Mall, Markville, Pacific Mall, Vaughan Mills, Promenade Mall, CF Markham
- **Hospitals:** Mackenzie Health (Richmond Hill), Cortellucci Vaughan Hospital, Markham Stouffville Hospital, Southlake Regional Health Centre
- **Transit:** Newmarket GO, Aurora GO, Richmond Hill GO, Markham GO, Unionville GO, Mount Joy GO
- **Attractions:** Canada's Wonderland

### Population Data (2021 Census)

| Municipality | Population |
|---|---|
| Markham | 338,503 |
| Vaughan | 323,103 |
| Richmond Hill | 202,022 |
| Newmarket | 87,942 |
| Aurora | 62,057 |
| Whitchurch-Stouffville | 49,864 |
| Georgina | 47,642 |
| East Gwillimbury | 34,637 |
| King | 27,333 |

## Data Acquisition

While the primary analysis focuses on York Region, this repository also contains tools for retrieving open data from other municipalities:

### York Region
The `download_york_data.py` script connects to the York Regional Police ArcGIS Hub API to request the CSV export of their datasets. It downloads both the historical data (2021-2025) to `dataSetDownloads/York_Historical_2021_to_2025.csv` (skipping if it already exists) and the current data (2025-Present) to a date-suffixed filename (e.g., `York_2025_to_2026-03-25.csv`). It cleanly handles dynamic export wait states (`202 Accepted` or `Pending` status) by checking the status API before cleanly saving the final datasets.

### Peel Region
The `download_peel_data.py` script automatically downloads all open incident records (Ecrimes) directly from the Peel Police ArcGIS REST API. Because the ArcGIS FeatureServer limits queries to a maximum number of records (e.g., 2,000), the script sequentially paginates through the data using `resultOffset` and `resultRecordCount` parameters until all records are retrieved, saving the full dataset to the `dataSetDownloads/` folder with a date-suffixed filename (e.g., `Peel_Police_Service_Incidents_2026-03-25.csv`).

## Usage

### Prerequisites

- Python 3.10+
- pandas (`pip install pandas`)

### Run

```bash
python analyze_crime_data.py -i <csv_file>

# Example:
python analyze_crime_data.py -i Occurrence_2021-2025.csv

# Override console encoding if needed:
python analyze_crime_data.py -i Occurrence_2021-2025.csv --encoding cp1252
```

Results are saved as CSVs to a `results_<input-filename>/` directory (e.g. `results_Occurrence_2021-2025/`). Files prefixed with `all_` are unfiltered; `filtered_` have anomaly locations removed.

## Output

See `results/` for all CSV outputs. The `results_v01-walkthrough.md` file contains a summary of key findings.
