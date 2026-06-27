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

### Transform (`src/gta_urban_analytics/transform/`)
Three sequential stages in `pipeline.py`:
1. **Unify** (`crime/unify_datasets.py`) — loads each region's raw CSV with its regional Pandera schema, standardizes columns, and merges into one DataFrame. York data arrives in Web Mercator (EPSG:3857) and is reprojected to WGS84 (EPSG:4326) using `pyproj`.
2. **Filter** (`crime/filter_invalid_incidents.py`) — validates rows against `unified_schema`; invalid rows are written to `invalid_data.csv` with a `validation_errors` column.
3. **Deduplicate** (`crime/deduplicate_incidents.py`) — groups by `source_identifier`; incidents with multiple distinct crime types get them concatenated (`"Assault && Robbery"`) and `mapped_crime_category` set to `"MULTIPLE"`.

### Schemas (`src/gta_urban_analytics/schemas.py`)
Pandera schemas for each region's raw format (`toronto_schema`, `york_schema`, etc.) and the final `unified_schema`. All use `coerce=True`. Key unified columns: `source_file_name`, `source_identifier`, `region`, `original_crime_type`, `mapped_crime_category`, `occurrence_date` (YYYY-MM-DD), `lat`/`lon`, `municipality`.

### Analyze (`src/gta_urban_analytics/analyze/analyze.py`)
**York-Region-only exploratory tool** — reads the RAW York CSV (York columns/municipalities/populations), not the unified dataset. Produces per-municipality statistics including crime rate per 1,000 residents (2021 census). Anomaly filtering excludes incidents within 500 m of known high-traffic locations (shopping malls, Canada's Wonderland, hospitals, GO stations); incident coordinates are reprojected from EPSG:3857 to UTM 17N before the distance test (audit F-02). Cross-region quantitative output comes from the census enrichment (`transform/census/enrich_with_crime_rate.py`), whose headline `crime_rate_per_1k` is computed over a single reference year (2025) for comparability (audit F-04). The same step also pre-bins each Dissemination Area into a bivariate income × crime-rate class (`bivariate_class` A–I = income tercile × crime-rate tercile, plus a human-readable `bivariate_label`) that drives the Kepler map's income-vs-crime choropleth — all binning lives here in the pipeline, never in the viz. It also emits a per-bucket breakdown: for each of the 4 crime groups (see Crime Category Mapping) it writes `crime_count_<slug>` and `crime_rate_<slug>_per_1k` (slug ∈ violent/property/nuisance/other), under the same reference-year window and small-population (`<50`) nulling as the total. `transform/census/build_municipality_choropleth.py` additionally produces `gta_municipalities.geojson` — a municipality-level (city/town) view built by **dissolving the census DAs**: each DA is assigned the modal `municipality` of the crime points it contains (nearest-assigned fill for empty DAs), DAs are dissolved per municipality with summed population, and total + per-bucket per-capita rates are computed over that shared denominator. It also emits parallel `*_excl_anomaly` counts that drop incidents within 500 m of a known high-traffic venue (malls/hospitals/etc. from `high_traffic_locations.py`), so the viz can toggle out likely venue-snapped over-counts. It drives the viz's headline 3D crime-rate-by-municipality layer. `transform/build_coverage_metadata.py` then writes `coverage.json` (top-level all-years + one per year folder) recording each region's date window, the categories/groups it reports, a `category_x_region` presence matrix that makes subset gaps explicit (e.g. Durham never reports Fraud/Sexual Offences), per-region `MULTIPLE` counts, and — for a given year — `is_partial` / `fraction_elapsed` / same-period-prior-year (no annualized projection; current year is honestly YTD).

### Crime Category Mapping
`transform/crime/crime_category_mappings.json` contains 364 entries mapping raw police descriptions to one of **15 canonical categories**: Assault, Auto Theft, Break & Enter, Theft, Robbery, Drug Offences, Weapons Offences, Sexual Offences, Homicide, Property Damage, Public Order, Fraud, Impaired Driving & Traffic, Threats & Harassment, Missing Person. (Plus runtime-only `Other` for unmapped values and `MULTIPLE` for multi-offence incidents.) All five regions map via this file — including Durham, which maps its offence text here rather than using filename labels (audit F-01).

`transform/crime/crime_groups.py` then collapses those 15 categories into **4 high-level buckets** (`crime_group`): **Violent** (Assault, Sexual Offences, Robbery, Homicide, Threats & Harassment, Weapons Offences), **Property** (Break & Enter, Theft, Auto Theft, Fraud, Property Damage), **Nuisance** (Public Order, Drug Offences, Impaired Driving & Traffic), **Other** (Missing Person, plus runtime `MULTIPLE` and any unmapped `Other`). This runs as a Phase-1 step **after** deduplication (dedup overwrites `mapped_crime_category` to `MULTIPLE`, so the bucket must derive from the final category), and `crime_group` persists into `unified_data.csv`. Judgment calls (Weapons → Violent, Impaired Driving → Nuisance, MULTIPLE → Other) are documented in the module and `docs/normalization-strategy.md`.

## Data Directories

| Path | Contents |
|------|----------|
| `data/01_raw/` | Downloaded CSVs (gitignored) |
| `data/02_transformed/` | `unified_data.csv` (incl. `crime_group`), `invalid_data.csv`, `coverage.json`, yearly partitions (each with its own `coverage.json`) |


## Notebooks

`notebooks/` contains exploratory Jupyter notebooks (`01_extract.ipynb`, `02_transform.ipynb`, `02_transform_census.ipynb`). Run with `uv run jupyter notebook`. Notebooks import `gta_urban_analytics` (the current package name; any older `gta_crime_data` imports need updating).
