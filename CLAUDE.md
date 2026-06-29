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
- ALWAYS use "Co-Authored-By" in commit messages (For Claude, use your default, for Antigravity IDE only use "[model] <antigravity.git@gmail.com>" - replacing [model] with the actual model name and version)

## Architecture

The pipeline is organized into four phases:

### Extract (`src/gta_urban_analytics/extract/`)
Each police service has its own module (`toronto.py`, `york.py`, `peel.py`, `halton.py`, `durham.py`). All sources use the ArcGIS Hub export API via `arcgis/hub.py`, which polls for export completion (status: Pending → Processing/ExportingData → Completed). `all.py` orchestrates all downloads. Census data comes from Statistics Canada via `statcan/census_data.py`.

**Fire (`extract/fire/`)** — one module per municipality. Toronto (`fire/toronto.py`) comes from the City of Toronto Open Data CKAN portal (a different mechanism than the police ArcGIS feeds, so it has its own `extract/ckan.py` datastore-dump helper): the **Fire Incidents** feed (~36k OFM-reportable incidents to 2023, with lat/lon, `Final_Incident_Type`, `TFS_Alarm_Time`, `Estimated_Dollar_Loss`, responding apparatus/personnel, and `Incident_Station_Area`) plus **Fire Station Locations** (85 points). The other municipalities are ArcGIS **FeatureServer query** feeds, downloaded via `extract/arcgis/paginated.py` through the shared `fire/common.py` helper (`f=geojson` makes ArcGIS reproject every source CRS to WGS84): `fire/mississauga.py` (22 stations), `fire/brampton.py` (14 stations **+** the 758-row 2012–2016 *Residential Fire Incidents* — the only non-Toronto incident feed), and `fire/markham.py` (9 stations; note ArcGIS item `0253…` is owned by City of Markham, not York Region, and is reached via the public utility proxy). `fire/all.py::download_fire()` orchestrates all of them and is called from `extract/all.py`. Fire is municipal, not regional — only Toronto carries per-station volume; station-only municipalities extend coverage but not the "fires handled" metric. `docs/DataSets.md` records per-source fields and the not-yet-integrated leads (Central York ward-aggregate causes; Vaughan's NDA-gated incidents).

### Transform (`src/gta_urban_analytics/transform/`)
Three sequential stages in `pipeline.py`:
1. **Unify** (`crime/unify_datasets.py`) — loads each region's raw CSV with its regional Pandera schema, standardizes columns, and merges into one DataFrame. York data arrives in Web Mercator (EPSG:3857) and is reprojected to WGS84 (EPSG:4326) using `pyproj`.
2. **Filter** (`crime/filter_invalid_incidents.py`) — validates rows against `unified_schema`; invalid rows are written to `invalid_data.csv` with a `validation_errors` column.
3. **Deduplicate** (`crime/deduplicate_incidents.py`) — groups by `source_identifier`; incidents with multiple distinct crime types get them concatenated (`"Assault && Robbery"`) and `mapped_crime_category` set to `"MULTIPLE"`.

### Schemas (`src/gta_urban_analytics/schemas.py`)
Pandera schemas for each region's raw format (`toronto_schema`, `york_schema`, etc.) and the final `unified_schema`. All use `coerce=True`. Key unified columns: `source_file_name`, `source_identifier`, `region`, `original_crime_type`, `mapped_crime_category`, `occurrence_date` (YYYY-MM-DD), `lat`/`lon`, `municipality`. Fire has its own raw schemas (`toronto_fire_schema`, `brampton_fire_incident_schema`) and the `fire_unified_schema` (unified fire columns: `incident_type`, `station_area`, `estimated_dollar_loss`, `responding_personnel`, plus the shared `region`/`municipality`/`occurrence_date`/`lat`/`lon`).

### Fire Transform (`src/gta_urban_analytics/transform/fire/`)
A parallel track to crime, run as Phase-2 derived steps in `pipeline.py`. All three are **top-level only** (not year-partitioned, like `coordinate_anomalies`):
1. `unify_fire.py` — standardizes each raw fire-incident source into `fire_unified_schema` → `fire_incidents.csv`. Toronto and Brampton (residential 2012–2016, `incident_type="Residential Fire"`) are appended; Brampton's `DATE_` is `YY/MM/DD`. Reuses the crime unifier's `_null_out_of_bounds_coords` (GTA box) and `_normalize_municipality`. Disk reads of each source are gated so injected test frames stay deterministic.
2. `build_fire_stations.py` — the headline "fires handled per station": groups Toronto incidents by `station_area` and joins to the 85 Toronto station points (point per station with `fires_handled` + `total_dollar_loss`). The Mississauga/Brampton/Markham station feeds are then appended as points with `has_volume=False` and null volume (location-only coverage) → `fire_stations.geojson` (130 points total). Station-number keys are normalized (`"115.0"` → `"115"`) so the join holds across CSV round-trips.
3. `build_fire_choropleth.py` — per-DA per-capita fire rate (mirrors `enrich_with_crime_rate`'s sjoin + small-population nulling) → `fire_da.geojson` (`fire_count`, `fire_rate_per_1k`).

### Analyze (`src/gta_urban_analytics/analyze/analyze.py`)
**York-Region-only exploratory tool** — reads the RAW York CSV (York columns/municipalities/populations), not the unified dataset. Produces per-municipality statistics including crime rate per 1,000 residents (2021 census). Anomaly filtering excludes incidents within 500 m of known high-traffic locations (shopping malls, Canada's Wonderland, hospitals, GO stations); incident coordinates are reprojected from EPSG:3857 to UTM 17N before the distance test (audit F-02). Cross-region quantitative output comes from the census enrichment (`transform/census/enrich_with_crime_rate.py`), whose headline `crime_rate_per_1k` is computed over a single reference year (2025) for comparability (audit F-04). The same step also pre-bins each Dissemination Area into a bivariate income × crime-rate class (`bivariate_class` A–I = income tercile × crime-rate tercile, plus a human-readable `bivariate_label`) that drives the Kepler map's income-vs-crime choropleth — all binning lives here in the pipeline, never in the viz.

### Crime Category Mapping
`transform/crime/crime_category_mappings.json` contains 364 entries mapping raw police descriptions to one of **15 canonical categories**: Assault, Auto Theft, Break & Enter, Theft, Robbery, Drug Offences, Weapons Offences, Sexual Offences, Homicide, Property Damage, Public Order, Fraud, Impaired Driving & Traffic, Threats & Harassment, Missing Person. (Plus runtime-only `Other` for unmapped values and `MULTIPLE` for multi-offence incidents.) All five regions map via this file — including Durham, which maps its offence text here rather than using filename labels (audit F-01).

## Data Directories

| Path | Contents |
|------|----------|
| `data/01_raw/` | Downloaded CSVs (gitignored). Fire: `Toronto_Fire_Incidents.csv` + `Toronto_Fire_Stations.csv`; `Mississauga_Fire_Stations.csv`; `Brampton_Fire_Stations.csv` + `Brampton_Fire_Incidents.csv`; `Markham_Fire_Stations.csv` |
| `data/02_transformed/` | `unified_data.csv`, `invalid_data.csv`, yearly partitions; fire products `fire_incidents.csv`, `fire_stations.geojson`, `fire_da.geojson` (top-level); `standalone/` compact variants (incl. fire) embedded by the single-file build |


## Notebooks

`notebooks/` contains exploratory Jupyter notebooks (`01_extract.ipynb`, `02_transform.ipynb`, `02_transform_census.ipynb`). Run with `uv run jupyter notebook`. Notebooks import `gta_urban_analytics` (the current package name; any older `gta_crime_data` imports need updating).
