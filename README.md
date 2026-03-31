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

## 2. Getting the Data

Run the full pipeline to download, transform, and analyze all regional crime datasets:
```bash
uv run full-pipeline
```

Then process the census data notebook:
```bash
uv run jupyter nbconvert --to notebook --execute notebooks/02_transform_census.ipynb
```

This will populate `data/01_raw/` with downloaded CSVs and `data/02_transformed/` with unified, validated output.

## 3. Visualization

Open `src/gta_urban_analytics/visualize/kepler_standalone_map.html` in a browser and load a dataset from `data/02_transformed/`.

## 4. Individual Pipeline Stages

You can also run each stage separately:

```bash
uv run download        # Download all raw CSVs into data/01_raw/
uv run transform       # Unify → filter → deduplicate → data/02_transformed/unified_data.csv
uv run analyze -i data/01_raw/<your_downloaded_file>.csv
uv run kepler          # Generate Kepler.gl map from transformed data
```
*(Note: If you encounter Windows file encoding errors, append `--encoding cp1252` to the analyze command.)*

### Generated Analysis Results
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
