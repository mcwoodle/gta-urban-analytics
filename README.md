# GTA Crime Data Analysis

A package to fetch and analyze open-source crime  data from police services across the Greater Toronto Area (GTA).

## 1. Setup

**Install `uv` (if not already):**
```bash
# MacOS / Linux:
curl -LsSf https://astral.sh/uv/install.sh | sh

# Windows (Command Prompt):
powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 | iex"
```

## 2. Data Retrieval

Download the latest data locally.

```bash
uv run download_toronto_data.py
uv run download_york_data.py
uv run download_peel_data.py
uv run download_halton_data.py
uv run download_durham_data.py
```

## 3. Analysis

```bash
uv run analyze_crime_data.py -i dataSetDownloads/<your_downloaded_file>.csv

# Example (York Region)
uv run analyze_crime_data.py -i dataSetDownloads/York_2025_to_YYYY-MM-DD.csv
```
*(Note: If you encounter Windows file encoding errors, append `--encoding cp1252` to the command.)*

### Generated Results
The script will output 10+ analytical reports directly into a `dataSetDownloads/results_<filename>/` directory, including:
* **Crime Rates**: Incidents per 1,000 residents and Violent Crime Rates
* **Breakdowns**: Property vs. Person Crime and clear location distributions (Business vs Outdoor vs Residence)
* **Demographics**: Shootings, Firearm Discharges, and Hate Crime tracking
* **Clearance**: Solved vs. Open case performance numbers

---

## 4. Methodology: Anomaly Filtering
To provide balanced perspectives in the generated reports, you will notice both **`all_`** (unfiltered) and **`filtered_`** CSVs output during the analysis.

The **filtered** datasets automatically identify and remove incidents occurring within 500 meters of massive regional anomalies that skew per-capita data, such as:
- **Major Retail**: Vaughan Mills, Pacific Mall, Upper Canada Mall, etc.
- **Transit Hubs**: Regional GO Stations (Newmarket, Aurora, Mount Joy, etc.)
- **Hospitals**: Mackenzie Health, Markham Stouffville
- **Attractions**: Canada's Wonderland
