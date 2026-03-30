# GTA Urban Analytics

A package to fetch and analyze open-source crime data from police services across the Greater Toronto Area (GTA).

## 1. Setup

**Install `uv` (if not already):**
```bash
# MacOS / Linux:
curl -LsSf https://astral.sh/uv/install.sh | sh

# Windows (Command Prompt):
powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 | iex"
```

**Install dependencies:**
```bash
uv sync
```

## 2. Data Retrieval

Download all regional crime datasets into `data/01_raw/`:
```bash
uv run download
```

## 3. Data Unification

Unify all downloaded CSVs into a single `data/02_transformed/unified_crime_data.csv`:
```bash
uv run unify
```

## 4. Analysis

```bash
uv run analyze -i data/01_raw/<your_downloaded_file>.csv

# Example (York Region)
uv run analyze -i data/01_raw/York_2025_to_YYYY-MM-DD.csv
```
*(Note: If you encounter Windows file encoding errors, append `--encoding cp1252` to the command.)*

### Generated Results
Results are saved to `data/03_analysis/results_<filename>/`, including:
* **Crime Rates**: Incidents per 1,000 residents and Violent Crime Rates
* **Breakdowns**: Property vs. Person Crime and clear location distributions (Business vs Outdoor vs Residence)
* **Demographics**: Shootings, Firearm Discharges, and Hate Crime tracking
* **Clearance**: Solved vs. Open case performance numbers

---

## 5. Methodology: Anomaly Filtering
To provide balanced perspectives in the generated reports, you will notice both **`all_`** (unfiltered) and **`filtered_`** CSVs output during the analysis.

The **filtered** datasets automatically identify and remove incidents occurring within 500 meters of massive regional anomalies that skew per-capita data, such as:
- **Major Retail**: Vaughan Mills, Pacific Mall, Upper Canada Mall, etc.
- **Transit Hubs**: Regional GO Stations (Newmarket, Aurora, Mount Joy, etc.)
- **Hospitals**: Mackenzie Health, Markham Stouffville
- **Attractions**: Canada's Wonderland
