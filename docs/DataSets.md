# Data Sources

> **How to download (current):** all sources are fetched by `uv run download` (or `uv run
> full-pipeline`), which writes raw CSVs to `data/01_raw/` — *not* `dataSetDownloads/`. There are no
> per-region `download_*_data.py` scripts; the `uv run download_*_data.py` entries below are
> historical. Peel and Halton are pulled from ArcGIS **FeatureServer query** endpoints (see
> `extract/peel.py` / `extract/halton.py`), not Hub CSV exports, so their "GIS Identifier" may not map
> to a Hub item id. York and Toronto YTD feeds are written with a date stamp (`*_to_<date>.csv`); only
> the newest snapshot per source is loaded (audit F-05).

Region | Crime Type | Time Period | Web Link | Direct Download URL | GIS Idenfitier
------|------------|------|---------|------|------
Durham | Drug Violations | 2020-* | https://open-data-drps.hub.arcgis.com/datasets/e0f56f8938c04215895b4c99d86e335f_0/explore?location=44.128198%2C-78.859448%2C10&showTable=true | `uv run download_durham_data.py` (https://hub.arcgis.com/api/download/v1/items/e0f56f8938c04215895b4c99d86e335f/csv?layers=0) | e0f56f8938c04215895b4c99d86e335f
Durham | Robbery | 2020-* | https://open-data-drps.hub.arcgis.com/datasets/b33ed02277c24547888da0499870642a_0/explore?location=44.119018%2C-78.885618%2C10&showTable=true | `uv run download_durham_data.py` (https://hub.arcgis.com/api/download/v1/items/b33ed02277c24547888da0499870642a/csv?layers=0) | b33ed02277c24547888da0499870642a
Durham | Break and Enter | 2020-* | https://open-data-drps.hub.arcgis.com/datasets/6c6af417d0464c868a1453f98261d617_0/explore?location=44.149998%2C-78.878899%2C10 | `uv run download_durham_data.py` (https://hub.arcgis.com/api/download/v1/items/6c6af417d0464c868a1453f98261d617/csv?layers=0) | 6c6af417d0464c868a1453f98261d617
Durham | Theft Over 5000 | 2020-* | https://open-data-drps.hub.arcgis.com/datasets/58bbaf779764480494b40a2b8574e950_0/explore?location=44.153574%2C-78.866883%2C10&showTable=true | `uv run download_durham_data.py` (https://hub.arcgis.com/api/download/v1/items/58bbaf779764480494b40a2b8574e950/csv?layers=0) | 58bbaf779764480494b40a2b8574e950
Durham | Assaults | 2020-* | https://open-data-drps.hub.arcgis.com/datasets/9f58177248f84afaa61b328b2b876f2e_0/explore?location=44.152384%2C-78.868798%2C10&showTable=true | `uv run download_durham_data.py` (https://hub.arcgis.com/api/download/v1/items/9f58177248f84afaa61b328b2b876f2e/csv?layers=0) | 9f58177248f84afaa61b328b2b876f2e
Durham | Auto Theft | 2020-* | https://open-data-drps.hub.arcgis.com/datasets/b01c5558122943b090ef4b3916f6f60c_0/explore?location=44.144231%2C-78.905355%2C10&showTable=true | `uv run download_durham_data.py` (https://hub.arcgis.com/api/download/v1/items/b01c5558122943b090ef4b3916f6f60c/csv?layers=0) | b01c5558122943b090ef4b3916f6f60c
Durham | Shootings and Firearm Discharge | 2020-* | https://open-data-drps.hub.arcgis.com/datasets/1f7e2a19732740f29e26dc7a7395080c_0/explore?location=44.122158%2C-78.845606%2C10&showTable=true | `uv run download_durham_data.py` (https://hub.arcgis.com/api/download/v1/items/1f7e2a19732740f29e26dc7a7395080c/csv?layers=0) | 1f7e2a19732740f29e26dc7a7395080c


Peel | All Open Incidents | https://open.peelregion.ca/datasets/peel-police-service-incidents/explore?location=43.6532%2C-79.3832%2C10.25&showTable=true | `uv run download_peel_data.py` (Outputs to `dataSetDownloads/Peel_Crime_Map_Data.csv`) | 


Halton | Crime Map Data | 2025-* | https://haltonpolice.ca/crime-statistics/crime-map/ | `uv run download_halton_data.py` (Outputs to `dataSetDownloads/Halton_Crime_Map_Data.csv`) | 2868b55253904626897f4bab56c490c8


York | ALL | 2021-2025 |https://www.yrp.ca/en/crime-statistics/crime-map.aspx | https://insights-york.opendata.arcgis.com/datasets/6ba41e1f3bfb4cd9bd0d89843a7d80f5_0/explore?location=44.071343%2C-79.466260%2C10&showTable=true | `uv run download_york_data.py` (Outputs to `dataSetDownloads/York_Historical_2021_to_2025.csv`) | 6ba41e1f3bfb4cd9bd0d89843a7d80f5

York | ALL | 2025-* | https://insights-york.opendata.arcgis.com/datasets/d89408f3c044424d91ada07cee849d55_0/explore?location=44.071343%2C-79.466260%2C10&showTable=true | `uv run download_york_data.py` (Outputs to `dataSetDownloads/York_2025_to_YYYY-MM-DD.csv`) | d89408f3c044424d91ada07cee849d55


Toronto | Major Crime Indicators | 2014-* | https://open.toronto.ca/dataset/toronto-police-service-major-crime-indicators/ | `uv run download_toronto_data.py` (https://hub.arcgis.com/api/download/v1/items/0a239a5563a344a3bbf8452504ed8d68/csv?layers=0) | 0a239a5563a344a3bbf8452504ed8d68


## Fire Service Data

Fire is a **municipal** service (not regional like the police feeds), so coverage
is fragmented: only Toronto publishes rich point-level **incident** data; other GTA
municipalities publish **station-location** data only (no per-station call/fire
volumes are openly available). The extractor lives in `extract/fire/` and is
structured to add more municipalities over time.

### Integrated (Toronto Fire Services — City of Toronto Open Data, CKAN)

These are pulled via the CKAN datastore-dump endpoint
(`extract/ckan.py`; `https://ckan0.cf.opendata.inter.prod-toronto.ca/datastore/dump/<resource_id>`).

Source | Dataset | Web Link | CKAN Resource ID
-------|---------|----------|-----------------
Toronto Fire | Fire Incidents (incident type, time, location, dollar loss, responding station) | https://open.toronto.ca/dataset/fire-incidents/ | fa5c7de5-10f8-41cf-883a-9b30a67c7b56
Toronto Fire | Fire Station / Facility Locations (85 stations) | https://open.toronto.ca/dataset/fire-station-locations/ | 9d1b7352-32ce-4af2-8681-595ce9e47b6e

### Future expansion (sources identified, not yet integrated)

Per the project sourcing brief. All are **station-location only** (points +
address/ward/station number); none carry "fires handled" volumes — so when
integrated they extend the `fire_stations` layer's coverage but the per-station
volume metric remains Toronto-only unless an incident feed surfaces.

Region | Source | Dataset | Web Link / Portal | Notes
-------|--------|---------|-------------------|------
Peel | Mississauga Fire & Emergency Services | City Fire Stations (22 stations, incl. ward + station id) | https://data.mississauga.ca/datasets/city-fire-stations | ArcGIS Hub; CSV/GeoJSON export available
Peel | Brampton Fire & Emergency Services | Fire Station locations | Brampton GeoHub — https://geohub.brampton.ca/ | Search "fire station"; ArcGIS Hub export
York | York Region | Fire Stations (emergency infrastructure coords) | https://insights-york.opendata.arcgis.com/datasets/02532059bb684e40baa15313b8ab3bb3 | ArcGIS Hub item `02532059bb684e40baa15313b8ab3bb3`
York | Central York Fire Services (Newmarket & Aurora) | Community Risk Public Portal (top-3 fire causes per ward; launched Apr 2026) | https://www.centralyorkfire.ca/ | Interactive portal; **no confirmed open API/bulk export** — needs investigation before integration
