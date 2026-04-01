# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

GTA Urban Analytics: an ETL pipeline that downloads, unifies, validates, and analyzes crime data from 5 Greater Toronto Area police services (Toronto, York, Peel, Halton, Durham) plus Statistics Canada census data.

## Commands

**Install dependencies:**
```bash
uv sync
```

**Run pipeline stages:**
```bash
uv run download        # Download all raw CSVs into data/01_raw/
uv run transform       # Unify → filter → deduplicate → data/02_transformed/unified_data.csv
uv run analyze -i data/01_raw/<file>.csv [--encoding cp1252]

uv run full-pipeline   # Run download + transform + analyze end-to-end
```

**Run tests:**
```bash
uv run pytest
uv run pytest tests/test_foo.py::test_bar   # single test
```

## Authoring

### Commit Messages
- Use conventional commits format: `type(scope): description`
- Types: feat, fix, refactor, docs, test, chore
- Keep the subject line under 72 characters
- Add 0-3 sentences to the commit message body to describe the changes.
- Use imperative mood ("Add feature" not "Added feature")
- NEVER use "Co-Authored-By" in commit messages.

## Architecture

The pipeline is organized into four phases:

### Extract (`src/gta_urban_analytics/extract/`)
Each police service has its own module (`toronto.py`, `york.py`, `peel.py`, `halton.py`, `durham.py`). All sources use the ArcGIS Hub export API via `arcgis/hub.py`, which polls for export completion (status: Pending → Processing/ExportingData → Completed). `all.py` orchestrates all downloads. Census data comes from Statistics Canada via `statcan/census_data.py`.

### Transform (`src/gta_urban_analytics/transform/`)
Three sequential stages in `pipeline.py`:
1. **Unify** (`crime/unify_datasets.py`) — loads each region's raw CSV with its regional Pandera schema, standardizes columns, and merges into one DataFrame. York data arrives in UTM Zone 17N (EPSG:26917) and is reprojected to WGS84 (EPSG:4326) using `pyproj`.
2. **Filter** (`crime/filter_invalid_incidents.py`) — validates rows against `unified_schema`; invalid rows are written to `invalid_data.csv` with a `validation_errors` column.
3. **Deduplicate** (`crime/deduplicate_incidents.py`) — groups by `source_identifier`; incidents with multiple distinct crime types get them concatenated (`"Assault && Robbery"`) and `mapped_crime_category` set to `"MULTIPLE"`.

### Schemas (`src/gta_urban_analytics/schemas.py`)
Pandera schemas for each region's raw format (`toronto_schema`, `york_schema`, etc.) and the final `unified_schema`. All use `coerce=True`. Key unified columns: `source_file_name`, `source_identifier`, `region`, `original_crime_type`, `mapped_crime_category`, `occurrence_date` (YYYY-MM-DD), `lat`/`lon`, `municipality`.

### Analyze (`src/gta_urban_analytics/analyze/analyze.py`)
Per-municipality statistics including crime rate per 1,000 residents (from 2021 census populations). Produces both unfiltered and anomaly-filtered results. Anomaly filtering excludes incidents within 500 m (in UTM Zone 17N) of known high-traffic locations: shopping malls (Vaughan Mills, Pacific Mall, etc.), Canada's Wonderland, hospitals, and GO Transit stations.

### Crime Category Mapping
`transform/crime/crime_category_mappings.json` contains ~357 entries mapping raw police descriptions to standardized categories (Assault, Auto Theft, Break & Enter, Drug Violations, Robbery, Theft, Sexual Assault, Homicide, Mischief, Weapons, Fraud, Other, MULTIPLE, etc.).

## Data Directories

| Path | Contents |
|------|----------|
| `data/01_raw/` | Downloaded CSVs (gitignored) |
| `data/02_transformed/` | `unified_data.csv`, `invalid_data.csv`, yearly partitions |


## Notebooks

`notebooks/` contains exploratory Jupyter notebooks (`01_extract.ipynb`, `02_transform.ipynb`, `02_transform_census.ipynb`). Run with `uv run jupyter notebook`. Notebooks import `gta_urban_analytics` (the current package name; any older `gta_crime_data` imports need updating).
