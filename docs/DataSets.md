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
is fragmented: only Toronto publishes rich point-level **incident** data with
dollar loss + responding station; Brampton publishes a closed 2012–2016
residential incident set; the other municipalities publish **station-location**
data only. The extractor lives in `extract/fire/` (one module per municipality)
and is structured to add more over time.

**Integration summary (all now wired into `uv run download` + the transform pipeline):**

| Municipality | Region | Dataset | Type | Feeds |
|---|---|---|---|---|
| Toronto | Toronto | Fire Incidents (~37k) + 85 stations | incidents + stations w/ volume | `fire_incidents`, `fire_stations` (volume), `fire_da` |
| Brampton | Peel | Residential Fire Incidents 2012–2016 (758) | incidents | `fire_incidents`, `fire_da` |
| Mississauga | Peel | City Fire Stations (22) | stations (no volume) | `fire_stations` (location-only) |
| Brampton | Peel | Fire Stations (14) | stations (no volume) | `fire_stations` (location-only) |
| Markham | York | Fire Stations (9) | stations (no volume) | `fire_stations` (location-only) |

Station points without an incident feed are written with `has_volume = false` and
null `fires_handled`/`total_dollar_loss`, so the map can show their coverage
without implying they handled zero fires. The per-station "fires handled" volume
metric remains Toronto-only.

### Integrated — Toronto (City of Toronto Open Data, CKAN)

Pulled via the CKAN datastore-dump endpoint
(`extract/ckan.py`; `https://ckan0.cf.opendata.inter.prod-toronto.ca/datastore/dump/<resource_id>`).

Source | Dataset | Web Link | CKAN Resource ID
-------|---------|----------|-----------------
Toronto Fire | Fire Incidents (incident type, time, location, dollar loss, responding station) | https://open.toronto.ca/dataset/fire-incidents/ | fa5c7de5-10f8-41cf-883a-9b30a67c7b56
Toronto Fire | Fire Station / Facility Locations (85 stations) | https://open.toronto.ca/dataset/fire-station-locations/ | 9d1b7352-32ce-4af2-8681-595ce9e47b6e

### Integrated — other municipalities (ArcGIS FeatureServer)

Each is an ArcGIS FeatureServer **query** endpoint downloaded with
`extract/arcgis/paginated.py` via the helper in `extract/fire/common.py`
(`extract/fire/{mississauga,brampton,markham}.py`). Requesting `f=geojson` makes
ArcGIS reproject every source CRS (Web Mercator, UTM 17N) to **WGS84**, so the
lat/lon the downloader derives from the geometry are always 4326 — no manual
reprojection needed. Field lists below were captured from the live services
(June 2026). Items are also reachable via metadata at
`https://www.arcgis.com/sharing/rest/content/items/<itemid>?f=json`.

#### Peel — Mississauga, "City Fire Stations" *(station locations)*
- **Item** `e84a2af2c2c6489cbd42086769df9b5e` · service
  `services6.arcgis.com/hM5ymMLbxIyWTjn2/arcgis/rest/services/City_Fire_Stations/FeatureServer`,
  **layer id 5** (not 0). Web link: https://data.mississauga.ca/datasets/city-fire-stations
- **22 points**, `esriGeometryPoint`, Web Mercator (EPSG:3857). It is a filtered
  slice of Mississauga's "City Landmarks" service, so the schema is wide (37 fields).
- **Useful fields:** `LANDMARKNAME` (e.g. `"Airport Fire Station #119"`),
  `UNITID` (e.g. `"FS19"`), address parts `STNO`/`STNAME`/`SUFFIX`, `CITY`,
  `WARD` (e.g. `"W5"`), `OWNERSHIP`, `SERVSTAT` (service status, e.g. `"OCC"`),
  `LANDMARKWEBSITE`, `LANDMARKPHONE`, `CENT_X`/`CENT_Y` (UTM 17N) and
  `CENT_X_3857`/`CENT_Y_3857`. No call/fire volumes.

#### Peel — Brampton, "Fire Stations" (BFES) *(station locations)*
- **Item** `903786a0b2a24e52b146856864d029ad` · service
  `services3.arcgis.com/rl7ACuZkiFsmDA2g/arcgis/rest/services/BFES_Fire_Stations/FeatureServer/0`.
  Portal: https://geohub.brampton.ca/
- **14 points**, `esriGeometryPoint`, Web Mercator (EPSG:3857).
- **Fields (all of them):** `FIRE_STATION_NUMBER` (e.g. `"203"`),
  `FIRE_STN_ADDRESS`, `ACCESS_FROM`. Minimal; station-location only.

#### Peel — Brampton, "BFES Residential Fire Incidents 2012 to 2016" *(INCIDENT feed)*
- **Item** `c0becda03ea944cca84bcff7d42f61b2` · service
  `services3.arcgis.com/rl7ACuZkiFsmDA2g/arcgis/rest/services/BFES Residential Fire Incidents 2012 to 2016/FeatureServer/0`
  (note spaces in path — URL-encode as `%20`).
- **758 points**, `esriGeometryPoint`. Coordinates are **WGS84 lat/lon in the
  attributes** (`XCOORD` ≈ −79.75 lon, `YCOORD` ≈ 43.74 lat); the geometry itself
  is projected.
- **Fields:** `FIRE` (incident id, e.g. `"1200362-00"`), `DATE_` (**`YY/MM/DD`** —
  e.g. `"12/01/03"` = 2012‑01‑03, confirmed against the `FIRE` year prefix),
  `ALARM` (time of day), `XCOORD`/`YCOORD`, `PROPERTY_CLASS_DESC`,
  `AREA_OF_ORIGIN_DESC`, `CAUSE_DESC`, `IGNITION_SOURCE_DESC`,
  `LEVEL_OF_ORIGIN_DESC`, `OBJECT_IGNITED_DESC`.
- **Integrated** as a second incident source in `unify_fire` (`region=Peel`,
  `municipality=Brampton`). It is **residential fires only**, a closed **2012–2016**
  window, with **no dollar loss / responding station / personnel** — so it
  contributes points + the constant `incident_type="Residential Fire"` to
  `fire_incidents`/`fire_da`, but NOT the per-station "fires handled" volume
  (which stays Toronto-only).

#### York — Markham, "Fire Stations" *(station locations; listed as "York Region" — incorrect)*
- **Item** `02532059bb684e40baa15313b8ab3bb3`. **Correction:** this item is owned
  by **City of Markham** (`maps.markham.ca`, service `OpenData/OD_FIRE_STN`), not
  York Region as a whole — it is **Markham only (9 stations)**, not region-wide.
- The direct `maps.markham.ca` service requires a token (`error 499`); use the
  **public proxy** instead:
  `https://utility.arcgis.com/usrsvcs/servers/02532059bb684e40baa15313b8ab3bb3/rest/services/OpenData/OD_FIRE_STN/FeatureServer/0`.
- **9 points**, `esriGeometryPoint`; `X_COORD`/`Y_COORD` are **UTM 17N
  (EPSG:26917)**.
- **Fields:** `NAME` (e.g. `"Fire Station 93"`), `NAME_CAP`, `ADDRESS`,
  `X_COORD`, `Y_COORD`, `TYPE` (`"Fire Station"`), `LABEL` (e.g. `"93"`),
  `GLOBALID`. Station-location only.
- **No single York-Region-wide fire-station open dataset surfaced** — coverage is
  per-municipality (Markham here; Vaughan/Richmond Hill etc. would each need their
  own source). Full York coverage means stitching several municipal feeds.

### Not integrated (aggregate-only / no usable open data)

#### York — Central York Fire Services (Newmarket & Aurora) *(ward-aggregated causes only)*
- Community Risk Public Portal (top-3 fire causes per ward; launched Apr 2026):
  https://www.centralyorkfire.ca/. **Update:** the portal's data layer *is* an
  open feature service — **item `344aa99a76da416c81673b3ddfd568f5`** (owner
  `TownOfNewmarket`), service
  `services3.arcgis.com/tSwsWwbYRimLwcCZ/arcgis/rest/services/Community_Risk_Portal_Top_Fire_Causes_Public_View/FeatureServer/0`.
- **13 polygons** (Newmarket + Aurora wards), `esriGeometryPolygon`. Fields:
  `MUNICIPALITY`, `WARD_NAME`/`WARD_NUMBER`/`WARD_ID`, and
  `TopFireCause{1,2,3}` + `..._Count` + `..._URL` (links to cyfs.ca safety tips,
  e.g. cause `"Cooking/BBQ"` count `2`).
- **This is ward-aggregated top-3 causes, not incident-level** — counts are tiny
  (1–2) and there is no location/time/dollar-loss per fire. Useful as a
  ward-level cause overlay, not a volume metric.
- Do **not** use the `AuroraData` org: its "Fire Stations"
  (`ad1e9aeeb26649158f018a3056115dce`) and `FireMain_*`/`AFD_*` stats are
  **Aurora, *Illinois*** (a 4.8M-row Esri "FireMain" demo; `STATE` = `"IL"`,
  sibling "Aurora IL Police Calls" layers), not Aurora, Ontario.

### Deep search for incident-level fire data (June 2026)

A wider sweep of municipal/regional ArcGIS orgs (Mississauga, Brampton, Markham,
Vaughan, Richmond Hill, Newmarket, Aurora, Region of Peel, York Region, plus
Halton/Durham municipalities) for **incident-level** fire data (per-fire points
with time/cause/loss, comparable to Toronto's feed) returned **almost nothing new**:

- **Only two open incident feeds exist in the GTA:** Toronto Fire Incidents
  (integrated) and **Brampton's "BFES Residential Fire Incidents 2012–2016"**
  (recorded above — residential-only, closed historical window). No other GTA
  municipality publishes open per-incident fire points.
- **Vaughan** keeps the richest non-Toronto incident database (VFRS, since 2009)
  but it is **released only under NDA for research** — there is no open portal
  dataset. The City publishes call totals in PDF **annual reports** only
  (https://www.vaughan.ca/.../annual-reports). The ArcGIS layers named
  "Vaughan Fire Incidents" (owner `tis607_spatialsk`, item
  `efa2488d2aed41d99902a6ce8e7fbd8f`; and York-U researcher
  `tayyab.shah_yorku`) are **non-authoritative re-publications** and, despite the
  name, hold **per-station call counts** (9 stations × `Fires`/`SuddenMedEm`/
  `TechRescues`/`Hazardous`), not raw incidents.
- **Mississauga / Brampton / Markham / Region of Peel / York Region** expose only
  station points, fire **response-zone polygons**, or non-fire layers (Mississauga
  publishes 311 call data, not fire). Peel/York are regional bodies; fire is
  municipal, so neither regional portal carries fire incidents.
- **Search distractors to skip next time** (these look like GTA hits but are not):
  `AuroraData` = Aurora, **IL**; `ToCHadmin` "Fire Incidents by Location" = Town of
  **Chapel Hill, NC** (addresses end "Chapel Hill NC", lat ≈ 35.9); and broad
  "fire incident" queries surface mostly US NFIRS / wildfire (NIFC, CAL FIRE)
  layers and `Open.Data_DurhamNC` (Durham, North Carolina — not Durham Region, ON).

**Bottom line:** outside Toronto, open *incident-level* fire data in the GTA is
limited to Brampton's 2012–2016 residential feed. Everything else is station
locations, response-zone polygons, or ward-aggregated cause counts; richer
incident data (e.g. Vaughan) exists but is gated behind NDAs or PDF reports.
