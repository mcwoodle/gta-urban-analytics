# Toronto YTD (2026) Data — Work Handoff

## Goal

Toronto crime rows in `unified_data.csv` stopped at 2025. The existing `toronto.py` extractor only downloads the **Major Crime Indicators Open Data** ArcGIS item (`0a239a5563a344a3bbf8452504ed8d68`), which Toronto Police publishes as a historical file covering 2014 through end of the *previous* year. Current-year (2026) incidents live in a separate, daily-refreshed feature service (TPS Crime App YTD).

End state: after `uv run download && uv run transform`, `unified_data.csv` must contain Toronto rows through the current date (today is 2026-04-08).

## Root cause

- Historical MCI Open Data item: `0a239a5563a344a3bbf8452504ed8d68` — contents only updated annually, no 2026 rows.
- YTD feature service: `YTD_CRIME_WM/FeatureServer/0` at host `services.arcgis.com/S9th0jAJ7bqgIRjw`, serviceItemId `cd594c082591479887f54eef41394b36`. Snippet: *"This dataset displays the anonymized locations where crime has occurred in the City of Toronto for the current year. Data is accurate as of the previous day."* Public, Open Government Licence – Ontario, `maxRecordCount` 2000, paginated query required.

YTD layer has a **different schema** from the historical dump — no `OFFENCE` / `OCC_DATE`; fields are: `OBJECTID, OCC_DATE_AGOL, REPORT_DATE_AGOL, EVENT_UNIQUE_ID, DIVISION, PREMISES_TYPE, HOUR, CRIME_TYPE, HOOD_158, NEIGHBOURHOOD_158, HOOD_140, NEIGHBOURHOOD_140, COUNT_, LONG_WGS84, LAT_WGS84, LOCATION_CATEGORY`. After pagination helper adds geometry-derived `lat`/`lon`, those two extra columns are also present.

## Completed tasks

### 1. `src/gta_urban_analytics/extract/toronto.py` — DONE
Rewritten to download **two** files:
- Historical: `Toronto_Major_Crime_Indicators.csv` via `download_arcgis_hub_csv` (skip-if-exists idiom, same as `york.py`).
- YTD: `Toronto_YTD_to_<YYYY-MM-DD>.csv` via `download_paginated_geojson` against `https://services.arcgis.com/S9th0jAJ7bqgIRjw/ArcGIS/rest/services/YTD_CRIME_WM/FeatureServer/0/query`.

**Verified working in WSL:** `uv run python -m gta_urban_analytics.extract.toronto` successfully downloaded `Toronto_YTD_to_2026-04-08.csv` with **12,475 records**. Historical file was skipped because it already existed.

### 2. `src/gta_urban_analytics/schemas.py` — DONE
Added `toronto_ytd_schema` matching the YTD layer 0 fields. Initially used `pa.Int` for `HOUR` and `COUNT_`; **corrected to `pa.Float`** after the first transform run revealed NaN values in `HOUR` that couldn't coerce to int64. Both fields are now `pa.Float, nullable=True, required=False, coerce=True` — this mirrors the pattern used in `toronto_schema` for nullable numerics like `OCC_DAY`.

### 3. `src/gta_urban_analytics/transform/crime/unify_datasets.py` — DONE
- Added `toronto_ytd_schema` to the import block.
- Replaced the single-file hard-coded Toronto block with a `glob.glob('Toronto_*.csv')` loop (mirroring the York pattern).
- Inside the loop, branches on column presence:
  - `OFFENCE` in columns → historical path (`toronto_schema`, parse `OCC_DATE`, use `OFFENCE`).
  - `CRIME_TYPE` in columns → YTD path (`toronto_ytd_schema`, parse `OCC_DATE_AGOL`, use `CRIME_TYPE`).
  - Else: warn + skip.
- Both branches share the same output DataFrame construction using `EVENT_UNIQUE_ID` for `source_identifier`, `LAT_WGS84`/`LONG_WGS84` for coordinates, `municipality='Toronto'`.

Because both branches emit `Toronto_<EVENT_UNIQUE_ID>` as `source_identifier`, the existing `deduplicate_incidents.py` will naturally reconcile any overlap between the two feeds.

### 4. `src/gta_urban_analytics/transform/crime/crime_category_mappings.json` — DONE
The YTD feed emits MCI short category names in `CRIME_TYPE`. Verified existing keys:
- `"Assault"` ✅ (line 14)
- `"Robbery"` ✅ (line 257)
- `"Theft Over"` ✅ (line 298)
- `"Auto Theft"` ❌ → **added**, maps to `"Auto Theft"`
- `"Break and Enter"` ❌ → **added**, maps to `"Break & Enter"`

Both new entries inserted right after the `"Assault"` line.

## Outstanding tasks

### 5. Re-run `uv run transform` to verify no further schema errors — NOT YET DONE
The first attempt failed on `HOUR` coercion. After the `pa.Int → pa.Float` fix was written to `schemas.py`, the transform has **not been re-run**. Next agent must execute (from inside WSL, repo `/home/mcwoodle/workspace/crime-data`):

```bash
uv run transform
```

Expected log lines: both `Processing Toronto: .../Toronto_Major_Crime_Indicators.csv` and `Processing Toronto: .../Toronto_YTD_to_2026-04-08.csv`. Exit cleanly with no Pandera errors. If another column fails coercion, apply the same `pa.Int → pa.Float` fix.

### 6. Sanity-check that 2026 rows land in `unified_data.csv` — NOT YET DONE
After transform succeeds, run:

```bash
uv run python -c "
import pandas as pd
df = pd.read_csv('data/02_transformed/unified_data.csv')
tor = df[df.region == 'Toronto'].copy()
tor['year'] = pd.to_datetime(tor.occurrence_date, errors='coerce').dt.year
print(tor.year.value_counts().sort_index().tail(5))
"
```

Expect a non-zero `2026` bucket (roughly 12k rows given the YTD download size, minus any dedup overlap with the historical file). If 2026 is still zero, check:
- Did the YTD branch of `unify_datasets` actually fire? (grep the log for `Toronto_YTD_to_`.)
- Is `OCC_DATE_AGOL` parsing correctly? It should be an ISO-8601 string from the GeoJSON export.

### 7. Run the test suite — NOT YET DONE

```bash
uv run pytest
```

Particularly watch `tests/` for anything asserting Toronto unify behavior — the glob-based loop replaces a single-file path so a test that mocked only `Toronto_Major_Crime_Indicators.csv` should still pass, but a test that asserted exact file count or hard-coded a single Toronto file read could break.

### 8. (Optional) Commit — NOT YET DONE
Suggested conventional-commit message once everything is green:

```
feat(extract): add Toronto YTD feed to capture current-year crime data
```

Body should explain: historical MCI Open Data item only covers through previous year end; YTD_CRIME_WM feature service fills the current-year gap; unify_datasets now branches on column shape to ingest both.

## Key files touched

| File | Status |
|---|---|
| `src/gta_urban_analytics/extract/toronto.py` | ✅ Rewritten, download verified |
| `src/gta_urban_analytics/schemas.py` | ✅ `toronto_ytd_schema` added, `HOUR`/`COUNT_` are `pa.Float` |
| `src/gta_urban_analytics/transform/crime/unify_datasets.py` | ✅ Toronto block replaced with glob loop + schema branch |
| `src/gta_urban_analytics/transform/crime/crime_category_mappings.json` | ✅ `Auto Theft` + `Break and Enter` entries added |
| `docs/toronto-ytd-work.md` | ✅ This handoff |

## Environment notes for the resuming agent

- The repo lives at `/home/mcwoodle/workspace/crime-data` inside WSL distro `Ubuntu-24.04`. From Windows host, invoke with: `wsl.exe -d Ubuntu-24.04 -- bash -lc "cd /home/mcwoodle/workspace/crime-data && <cmd>"`.
- Package manager is `uv`. Entry points: `uv run download`, `uv run transform`, `uv run pytest`.
- The historical Toronto file is ~160 MB. `toronto.py` has a skip-if-exists check so re-running `uv run download` won't re-fetch it.
- Today's date in-conversation is **2026-04-08**, so the YTD filename is `Toronto_YTD_to_2026-04-08.csv`. If resumed on a later day, a new dated file will be created alongside the old one — the glob loop ingests all matching files, and dedup by `source_identifier` handles the overlap.
- Branch: `feature/kepler-map`. Base for PR: `main`.

## How the root cause was diagnosed

1. Read `toronto.py`, `york.py`, `peel.py` to understand extraction patterns.
2. Confirmed via ArcGIS REST metadata (`items/0a239a5563a344a3bbf8452504ed8d68?f=json`) that the current Toronto item is "Community Safety Indicators Open Data" — historical only.
3. Discovered `YTD_CRIME_WM` by listing `services.arcgis.com/S9th0jAJ7bqgIRjw/ArcGIS/rest/services`.
4. Pulled field list via `services.arcgis.com/.../YTD_CRIME_WM/FeatureServer/0?f=json` — confirmed field names and `maxRecordCount=2000`.
5. Verified the item is public (`access: public`, tags include `Open Data`, `TPS`, `Major Crime Indicator`).
