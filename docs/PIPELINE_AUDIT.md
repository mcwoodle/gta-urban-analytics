# GTA Urban Analytics — Pipeline Deep-Dive Audit & Remediation Log

**Status:** Complete — 19/19 findings resolved (incl. the F-19 Kepler anomaly layer), T1–T15 done ·
**Started:** 2026-06-23 · **Branches:** `chore/data-pipeline-audit` (audit, merged), `feat/anomaly-viz-layer` (viz)
**Author:** automated deep-dive (Claude) · **Scope:** data acquisition, parsing, transformation, validation, analysis, and the data feeding the Kepler visualization.

---

## 0. How to use this document

This is both a **findings register** and a **handoff worklog**. Any agent (or human) should be able
to resume the remediation using *only* this file plus the repo.

- **Section 2** — as-built pipeline map (orient here first).
- **Section 3** — severity-ranked findings register (`F-01 …`): stable ID, location (`file:line`),
  evidence, impact, recommended fix, status.
- **Section 4** — empirical measurements (profiled against the real CSVs, 2026-06-23).
- **Section 5** — remediation backlog: discrete checkbox tasks (`T1 …`) grouped by priority. This is
  the "pick up where we left off" list; each task references the finding(s) it closes.
- **Section 6** — running work log.

**Status legend:** ✅ done · 🟡 in progress · ⬜ not started · 🔎 needs owner decision

---

## 1. Executive summary

The pipeline runs end-to-end but carries several **data-correctness defects that silently distort
cross-region aggregates** — the class of issue to fix before a production release. Quantified against
the current `unified_data.csv` (**808,671 rows**: Toronto 427,157 · York 243,062 · Peel 82,367 ·
Durham 35,825 · Halton 20,260):

1. **Durham uses an incompatible category taxonomy** (`F-01`). Durham's `mapped_crime_category` comes
   from the *source filename*, producing **27,387 rows (3.39%)** with labels that don't exist in the
   15-category canonical set the other four regions map into (`Assaults`≠`Assault`,
   `Break and Enter`≠`Break & Enter`, `Theft Over 5000`≠`Theft`, `Drug Violations`≠`Drug Offences`,
   `Shootings and Firearm Discharge`≠`Weapons Offences`). Only 2 of Durham's 8 labels are canonical.
2. **Null-island `(0,0)` coordinates survive validation** (`F-03`): **7,560 Toronto rows (1.77%)**
   (redacted/`NSA` locations) carry `(0,0)`, a valid non-null float. They create a phantom map cluster
   off Africa and drag the Toronto municipality centroid (used for shooting arcs) toward `(0,0)`.
3. **The `analyze.py` anomaly filter is a no-op** (`F-02`): it compares UTM-17N anomaly coordinates
   against York's raw `x`/`y`, which are **EPSG:3857**. Nothing is ever within 500 m, so every
   "filtered" output equals the "unfiltered" one.
4. **The headline per-DA crime rate is not comparable across regions** (`F-04`): the all-years census
   enrichment divides multi-year incident counts by single-year (2021) population, and the regions'
   time windows differ wildly — Toronto reaches back to 1964 (volume from 2014), **Halton covers only
   2025–2026**, Peel from 2023, York from 2021, Durham from 2020. Longer-history DAs look "higher
   crime" purely from the window.
5. **Shooting-arc weapons detection is dead code** (`F-11`): it tests `mapped == "Weapons"`, but the
   canonical label is `"Weapons Offences"` — that branch is always false.
6. **Snapshot files invite duplication** (`F-05`): `unify` globs `Toronto_*.csv`/`York_*.csv`, but the
   downloaders mint date-stamped filenames and never delete old ones. *Currently* deduplication
   absorbs the existing feed overlaps (verified — see `F-06`/§4.3), but the design is fragile.

Plus medium/low robustness, normalization, test-coverage, and documentation-drift issues below.

**Good news confirmed by profiling:** dedup is clean (0 repeated `source_identifier`); 0 NaN and 0
out-of-bounds coordinates; the crime-mapping JSON has **100% coverage** of post-filter offence text
(0 `"Other"` rows); no large data/build artifacts are tracked in git.

**Owner decisions (2026-06-23):** F-04 → **Option C** (headline rate over reference year 2025; per-year
folders keep trends). F-18 → **Option B** (`analyze.py` relabeled York-only + CRS fixed; the census
enrichment is the cross-region analytic). F-19 → **keep data intact + a separate anomaly layer**
(`coordinate_anomalies.csv`). All three implemented this session — see §3 statuses and §6.

---

## 2. As-built pipeline map

```
extract/                      download → data/01_raw/
  all.py                      orchestrates all downloads
  toronto.py                  MCI historical (ArcGIS Hub CSV export) + YTD (paginated FeatureServer→CSV)
  york.py                     Historical 2021-2025 + present 2025-→ (Hub CSV export), DATE-STAMPED filename
  peel.py / halton.py         paginated FeatureServer → GeoJSON → CSV
  durham.py                   7 per-crime-type Hub CSV exports; registry holds (category, file, arcgis_id)
  statcan/census_data.py      DA boundary shapefile + Ontario census CSV (zip stream)
  arcgis/hub.py               polls Hub export job (Pending→Processing→Completed), downloads resultUrl
  arcgis/paginated.py         loops FeatureServer query (f=geojson, 2000/page) until !exceededTransferLimit

transform/pipeline.py  →  data/02_transformed/
  PIPELINE_STEPS (in-memory df threaded through, CSV written after step 4):
   1 unify_datasets()         load each region's raw CSV, standardise cols, map crime types, reproject York
   2 verify_mappings(df)      RAISES if any original_crime_type missing from crime_category_mappings.json
   3 filter_invalid_incidents validate vs unified_schema; reject rows → invalid_data.csv
   4 deduplicate_incidents    group by source_identifier; multi-offence → "A && B", category="MULTIPLE"
     → writes data/02_transformed/unified_data.csv
   5 build_gta_census_geojson StatCan DA polygons ∩ GTA CDs, + Population/Median_Income → gta_census_da.geojson
   6 enrich_census_with_crime point-in-polygon join crimes→DAs; crime_count + crime_rate_per_1k (ALL years)
   7 build_shooting_arcs      shooting incidents → arcs to municipality centroid → shooting_arcs.csv
   8 build_standalone_compact slim CSV/GeoJSON for single-file Kepler build (standalone/)
   9 partition_all_years      per-year (2020-→) re-emission of csv + re-enriched census + arcs + compact

analyze/analyze.py            STANDALONE, York-raw-only; per-municipality stats + (broken) anomaly filter
schemas.py                    per-region raw Pandera schemas + unified_schema (all coerce=True)
transform/crime/crime_category_mappings.json   364 keys → 15 canonical categories
```

**Unified schema columns:** `source_file_name, source_identifier, region, original_crime_type,
mapped_crime_category, occurrence_date (YYYY-MM-DD str), lat, lon, municipality`.

**Canonical crime categories (15, the JSON's value set):** Drug Offences · Public Order ·
Break & Enter · Assault · Theft · Robbery · Weapons Offences · Fraud · Property Damage · Auto Theft ·
Impaired Driving & Traffic · Homicide · Sexual Offences · Threats & Harassment · Missing Person.
(Plus runtime-only `Other` = unmapped default — currently never emitted; and `MULTIPLE` = multi-offence
dedup.)

---

## 3. Findings register

### 🔴 High severity (data correctness)

#### F-01 — Durham category taxonomy is incompatible with every other region  ✅ FIXED
- **Where:** `transform/crime/unify_datasets.py` (Durham block — `mapped_crime_category` was
  `file_category`), `extract/durham.py:6-14` (registry), `crime_category_mappings.json`.
- **What:** Durham set `mapped_crime_category` from the **filename** via the registry. 5 of 7 registry
  labels are non-canonical. **27,387 rows (3.39%), 100% Durham**, carried bad labels: `Assaults`
  15,591 · `Break and Enter` 6,855 · `Drug Violations` 3,529 · `Theft Over 5000` 1,208 ·
  `Shootings and Firearm Discharge` 204.
- **Impact:** Any `mapped_crime_category` rollup split the same real category in two (e.g. `Assault`
  for 4 regions + `Assaults` for Durham), so Durham's crimes never aggregated with the rest.
- **Fix applied:** Map Durham's `offence` through the JSON like every other region, with a
  canonicalised file-category fallback for missing/unmapped offences. **Bonus:** the JSON also corrects
  mis-bucketing the filename caused — `Home Invasion` → `Break & Enter` and `Carjacking` →
  `Auto Theft` (both lived in Durham's *Robbery* file). ⚠️ These reclassifications change counts and
  should be sanity-checked by the owner. See work log §6 / T1.
- **Status:** ✅ (verified by `tests/test_durham_mapping.py`)

#### F-02 — `analyze.py` anomaly filter compares mismatched coordinate systems (no-op)
- **Where:** `analyze/analyze.py:50-74` (`ANOMALY_LOCATIONS` in UTM 17N), `:96-103`
  (`is_near_anomaly` euclidean on `x,y`), `:160` (`r["x"], r["y"]`).
- **What:** Anomalies are UTM-17N eastings/northings (e.g. `(625_755, 4_880_434)`); the raw York `x,y`
  are EPSG:3857 (e.g. `(-8_862_444, 5_457_728)`). Distance is always ≫ 500 m → `near_anomaly` always
  False. (Profiling confirmed York `x,y` are 3857: every reprojected point lands inside the GTA box.)
- **Impact:** Every "FILTERED (anomalies removed)" output is identical to the unfiltered one; the
  anomaly methodology advertised in README §5 does nothing.
- **Fix:** Reproject incident `x,y` 3857→26917 (UTM 17N) before the distance test (or store anomalies
  in 4326 and use geodesic distance). Regression-test a known near-mall point.
- **Note:** `analyze.py` is **not** in the main pipeline (`full_pipeline` runs download+transform;
  `analyze()` is commented out at `main.py:18`) and is York-raw-only — see F-18.
- **Status:** ✅ Fixed — reprojects raw 3857 `x,y` → UTM 17N before the 500 m test
  (`tests/test_analyze_anomaly_crs.py`).

#### F-03 — Null-island `(0,0)` coordinates pass validation and pollute outputs
- **Where:** `schemas.py:17-18` (lat/lon `nullable=False`, **no range check**); Toronto
  `unify_datasets.py` (`LAT_WGS84/LONG_WGS84` copied verbatim); `build_shooting_arcs.py:84-92`
  (centroid = mean of all points incl. `(0,0)`); `build_standalone_compact.py:67-68` (drops NaN, not
  `(0,0)`).
- **What:** `(0.0,0.0)` is a valid non-null float → `filter_invalid_incidents` keeps it. **7,560
  Toronto rows (1.77%)**.
- **Impact:** phantom point cluster at lat 0/lon 0 in the Kepler crime layer; Toronto's municipality
  centroid (shooting-arc destination) pulled toward `(0,0)`; inflated raw counts. (The census
  point-in-polygon join already excludes them — they fall outside all DAs — so per-DA rates are spared.)
- **Fix applied:** GTA-bbox + `(0,0)` rule (`_null_out_of_bounds_coords` in `unify_datasets.py`) nulls
  offending coords so the existing filter quarantines them to `invalid_data.csv`. Trade-off: those
  ~7,560 incidents (valid crime type/date/municipality, no location) leave the unified table —
  acceptable under the schema's existing "every incident must have a location" contract; they remain
  inspectable in `invalid_data.csv`. Real-data check: 8,534 pre-dedup Toronto rows nulled, 0 legit
  points affected.
- **Status:** ✅ (verified on real data; `tests/test_coordinate_validation.py`)

#### F-04 — All-years per-DA crime rate divides multi-year crime by single-year population 🔎
- **Where:** `transform/census/enrich_with_crime_rate.py:108-123`.
- **What:** Counts **all** incidents (Toronto back to 1964/volume-from-2014) ÷ 2021 `Population`.
  Region windows differ enormously (Toronto ~12 yr of volume vs **Halton 2025–2026 only**), so
  `crime_rate_per_1k` conflates "more years of data" with "more crime."
- **Impact:** The headline choropleth metric is not comparable across DAs/regions. (Per-year
  partitions in step 9 are correct — single year of crime each.)
- **Fix (owner decision):** (a) annualise (÷ distinct contributing years), (b) fixed common window
  (e.g. trailing 12 months or one reference year), or (c) surface per-year rates only. Document the
  definition in README + tooltip.
- **Status:** ✅ **Decision: Option C.** Headline rate now computed over reference year **2025**
  (`REFERENCE_YEAR` in `enrich_with_crime_rate.py`); per-year folders unchanged. 2025 has all 5 regions
  (127,017 pts). (`tests/test_reference_year_rate.py`)

#### F-05 — Date-stamped snapshot files are glob-concatenated → duplication risk
- **Where:** `extract/york.py:24`, `extract/toronto.py:27` (date-stamped names);
  `unify_datasets.py` globs `Toronto_*.csv` / `York_*.csv`.
- **What:** Present/YTD downloaders write a new filename per calendar day and never delete the old one
  (York present isn't even skip-guarded). Two runs on different days ⇒ two snapshots ⇒ `unify`
  concatenates both.
- **Impact:** Up to a full duplicate of the current-year feeds. Today only one snapshot of each exists,
  so it isn't firing — but it's a latent foot-gun.
- **Fix:** Stable filenames (overwrite) or select only the newest snapshot per pattern in `unify`;
  warn on multiples.
- **Status:** ✅ Fixed — `_drop_stale_snapshots` keeps only the newest `*_to_<date>.csv` per source in
  `unify` and warns on extras. (`tests/test_snapshot_selection.py`)

#### F-06 — Overlapping feeds rely on exact ID match for dedup (currently OK, fragile)
- **Where:** feeds in `extract/toronto.py`, `extract/york.py`; dedup `deduplicate_incidents.py:20`.
- **What & evidence (§4.3):** Toronto MCI and YTD date ranges overlap massively (MCI actually runs to
  **2026-03-31**, contradicting the "end of previous year" comment in `toronto.py:14`); **8,958
  `EVENT_UNIQUE_ID` appear in both files**. Dedup by `source_identifier` collapses them correctly —
  Toronto unified 427,157 = MCI-distinct 414,033 + YTD-only 13,124 (exact). York historical/present
  `UniqueIdentifier` sets are **fully disjoint** (intersection 0); York unified = 177,546 + 65,516.
- **Impact:** No active double-count today, **but** it depends entirely on IDs matching across feeds.
  If a feed ever re-issues IDs, duplicates would slip through. Also `keep='first'` keeps the MCI copy
  of the 8,958 shared events, so any YTD corrections to those are dropped (freshness nuance).
- **Fix:** Add a secondary near-duplicate guard (e.g. dedup on `(region, occurrence_date, lat, lon,
  original_crime_type)`), and correct the misleading `toronto.py` comment.
- **Status:** ✅ Addressed — stale-snapshot loading removed (F-05); the misleading `toronto.py`
  comment is corrected; the existing `source_identifier` dedup already collapses the MCI↔YTD overlap
  (§4.3), so no coordinate-based secondary key was added (F-19 showed that would delete real snapped
  incidents).

#### F-19 — Low-precision / placeholder coordinates pile many distinct incidents on one point
- **Where:** source geocoding; surfaces in `unified_data.csv` and every spatial output.
- **What (investigated 2026-06-23):** What first looked like duplicate tuples is **not** re-publish
  duplication — the rows are *distinct* incidents (distinct `source_identifier`) snapped to a shared
  coordinate. Geocoding is coarse: York has 14,740 distinct coords for 243,062 rows; **one York
  coordinate carries 4,981 incidents**; 2,149 York coords hold >20 each. Examples: 29 distinct Markham
  incidents at one identical lat/lon on one day/type; "ROADSIDE TEST" incidents pile onto checkpoint
  coordinates. Halton: 3,899 distinct coords for 20,260 rows (max 487 at one point); Peel is finer
  (36,069 coords for 82,367 rows).
- **Impact:** Counts are CORRECT (real distinct incidents) — do **not** dedup these or you delete real
  data. The damage is spatial: the Kepler point/hexbin layer shows artificial hotspots at placeholder
  points, and the per-DA crime rate piles incidents onto whatever DA holds the placeholder centroid
  (often not where the crime occurred). (F-03 already removed Toronto's biggest pile — the 7,560 at
  `(0,0)`.)
- **Fix (owner decision):** Detect placeholder/low-precision coords (e.g. >N incidents at one identical
  full-precision point, or coords matching municipal centroids) and flag them: keep in counts,
  exclude/down-weight in the per-DA rate and/or the point hotspot layer. Do NOT add a coordinate-based
  dedup key. Relates to F-02 (real vs artificial hotspots) and F-04.
- **Status:** ✅ **Decision: keep data intact + separate anomaly layer.** New
  `build_coordinate_anomalies.py` (pipeline step) writes `coordinate_anomalies.csv` — coordinates with
  **> 200** incidents at one identical point (tightened from the initial ≥50 cut; tunable threshold).
  Incidents stay in all counts/rates. Each flagged coordinate is classified against a curated list of
  high-foot-traffic GTA venues (`high_traffic_locations.py` — malls, hospitals, attractions, transit):
  `anomaly_type = "high_traffic_area"` when within 500 m of a venue (an at-least-partly organic hotspot)
  vs `"unexplained"` (a likely pure placeholder/geocoding artifact), with `nearest_location` /
  `location_category` for context. The Kepler viz renders it as **Layer 5** — a `point` overlay sized by
  `incident_count` and **coloured by `anomaly_type`** (amber = high-traffic, magenta = unexplained;
  full profile + embedded in the standalone build). Hovering a dot reveals the classification: the
  builder now emits a plain-English `description` column (leading the CSV column order), and the viz
  config pins the anomaly layer's tooltip fields (`tooltips.coordinate_anomalies`) so the hover box
  always shows it (Kepler otherwise defaults to a dataset's first 5 columns).
  (`tests/test_coordinate_anomalies.py`, `tests/test_high_traffic_locations.py`)

### 🟠 Medium severity

#### F-07 — Pandera `validate()` return discarded (`coerce=True` is a no-op) — careful, see caveat
- **Where:** `unify_datasets.py` (every `*_schema.validate(df)` result ignored);
  `filter_invalid_incidents.py:23,26` (success path returns original `df`).
- **What:** Schemas set `coerce=True`, but the coerced frame is thrown away; downstream uses raw-dtype
  `df`. Validation is check-only.
- **⚠️ Caveat (do not blind-fix):** simply capturing the return would **break Toronto YTD dates** —
  `OCC_DATE_AGOL` is schema-typed `String` but parsed with `pd.to_datetime(..., unit='ms')`. Coercing
  it to string makes `unit='ms'` produce `NaT`. Any fix must first reconcile schema dtypes with the
  epoch-ms parsing (parse before coercion, or type the epoch columns as Int).
- **Fix:** Align schema dtypes with parse logic, then capture the validated frame.
- **Status:** ✅ Resolved — fixed the real defect (`toronto_ytd_schema` epoch-ms columns were typed
  `String`; now `Float`). Coercion is intentionally **not** captured: the pipeline hands off via CSV
  (typeless), so capturing it has no downstream effect, and the per-region raw schemas are
  validation-only by design. Date-parsing guard tests added. (`tests/test_unify_dates.py`)

#### F-08 — Municipality names not normalised (case / abbreviations) + cross-region leakage
- **Where:** per-region `municipality` in `unify_datasets.py`; grouped in `analyze.py` and
  `build_shooting_arcs.py:84`.
- **What (§4.4):** Durham = 3-letter UPPER **codes** (`OSH`,`AJA`,`PIC`…, whitespace-padded in raw);
  Halton/Peel = full UPPER (Peel drops internal spaces: `MISSISSAUGA`, `HALTONHILLS`, `RICHMONDHILL`);
  Toronto/York = Title case. **5 municipalities appear under ≥2 spellings** (Toronto, Vaughan, Markham,
  Richmond Hill, Halton Hills). Also **cross-region leakage**: Durham/Peel feeds contain incidents in
  other regions' cities (Peel `TORONTO` 165, Durham `TOR` 112, `VAU`, `MAR`…) — i.e. police-service
  `region` ≠ incident `municipality`. (0 null/empty/whitespace municipalities — only casing/abbrev.)
- **Impact:** Per-municipality grouping treats `BURLINGTON`/`Burlington` as different and Durham's
  `AJA` as unjoinable to any name/population table; shooting-arc centroids split per label.
- **Fix:** Normalisation map (strip → title-case → expand Durham codes to full names). Decide whether
  to keep cross-region rows under their true municipality or scope to home region.
- **Status:** ✅ Fixed — `_normalize_municipality` (alias map for Durham codes + Peel no-space
  spellings, else Title-case) applied in `unify`. Real data: 30 clean municipalities, 0 codes/UPPER
  labels left, cross-region spellings merged. (`tests/test_municipality_normalization.py`)

#### F-09 — `verify_mappings` hard-couples Durham offence text to the JSON  ✅ resolved by T1
- **Where:** `transform/crime/verify_mappings.py:23-52` (pipeline step 2).
- **What:** Aborts the pipeline if *any* `original_crime_type` (incl. every Durham offence string) is
  absent from the JSON — even though Durham didn't use the JSON for its category. (This is also *why*
  there are 0 `"Other"` rows: an unmapped type aborts rather than defaulting.)
- **Resolution:** With T1, Durham now genuinely maps via the JSON, so the coupling is intentional and
  correct. No separate change needed; keep the guard.
- **Status:** ✅ (subsumed by T1)

#### F-10 — Epoch-millisecond dates parsed as naive UTC (no timezone handling)
- **Where:** `unify_datasets.py` Halton `DATE`, Peel `OccDate`, Toronto YTD `OCC_DATE_AGOL` — all
  `to_datetime(..., unit='ms')`.
- **What:** Parsed UTC-naive then truncated to a date. Spot checks suggest these encode local-time-as-
  UTC (so dates are usually right), but it's unverified/undocumented; near-midnight rows could shift a
  day and land in the wrong yearly partition.
- **Fix:** Cross-check epoch vs the human `OccurrenceDate`/`Time` columns, parse explicitly, document.
- **Status:** ✅ Verified-OK — investigated: the epoch-ms fields encode **local time stored as naive
  UTC**, so `to_datetime(unit='ms')` yields the correct local date. Peel: **0.00%** mismatch vs its
  human date column; Toronto YTD clusters at 04:00/05:00 UTC (= local midnight across the DST
  boundary). No shift; no parse change needed.

#### F-11 — Shooting-arc detection checks `mapped == "Weapons"` (a category that never exists)
- **Where:** `transform/crime/build_shooting_arcs.py:98-99`.
- **What:** Mask is `original.str.contains("shoot|firearm")` OR `mapped == "Weapons"`. Canonical label
  is `"Weapons Offences"`, so the second clause is **always False** — detection silently relies on the
  regex only.
- **Impact:** Weapon/firearm incidents categorised `Weapons Offences` but lacking the literal
  "shoot"/"firearm" in the text are omitted from the arc layer.
- **Fix applied:** `mapped == "Weapons Offences"`.
- **Status:** ✅ (verified by `tests/test_shooting_arcs.py`)

#### F-17 — Steps 5-9 re-read `unified_data.csv` instead of using the threaded in-memory `df`
- **Where:** `pipeline.py:43-53` threads `df`, but census/enrich/arcs/compact/partition read the CSV
  from disk anyway.
- **What:** The lambda threading is partly illusory; the real hand-off is the post-step-4 CSV. Also:
  enrichment counts **post-dedup incidents** (multi-offence collapsed) — a deliberate but undocumented
  "incidents not offences" choice.
- **Impact:** Maintainability; double I/O of a 100 MB+ CSV.
- **Fix:** Pass `df` through honestly or adopt an explicit "write-then-read" contract; document the
  incidents-vs-offences definition.
- **Status:** ✅ Fixed — `pipeline.py` split into `TRANSFORM_STEPS` (phase 1, threads the frame) and
  `DERIVED_STEPS` (phase 2, each reads from disk); removed the misleading `(func(), df)[1]` threading;
  documented the incidents-vs-offences definition. (`tests/test_pipeline.py`)

### 🟡 Low severity / robustness / docs

#### F-12 — Network downloads lack timeouts, retries, robust termination
- **Where:** `arcgis/hub.py` (no timeout; only `HTTPError` caught; unbounded polling),
  `arcgis/paginated.py` (no timeout/retry; **infinite-loop risk** if `exceededTransferLimit=True` with
  empty `features`; CSV headers from the *first* feature only → columns missing on feature 0 are
  dropped), `statcan/census_data.py` (no timeout; whole ZIP buffered in memory).
- **Fix:** timeouts, bounded retry/backoff, break-on-empty-page, union feature keys for headers.
- **Status:** ✅ Fixed — timeouts + bounded retries on all downloads; pagination stops on an empty page
  (no infinite loop) and unions feature-property headers. Pure helpers covered.
  (`tests/test_paginated.py`)

#### F-13 — Documentation drift
- **Where:** `README.md` §4/§5 (presents `analyze` as a multi-region engine — it's York-raw-only);
  `gta-urban-analytics/CLAUDE.md` (category list says `Drug Violations / Weapons / Sexual Assault /
  Mischief`; the JSON uses `Drug Offences / Weapons Offences / Sexual Offences / Property Damage`);
  `docs/DataSets.md` (non-existent scripts like `download_durham_data.py`, stale `dataSetDownloads/`
  paths, a Halton GIS id that no longer matches the FeatureServer URL the code uses).
- **Status:** ✅ README + CLAUDE.md (earlier this session) and `docs/DataSets.md` (intro note: real
  `uv run download` commands, `data/01_raw/` output, FeatureServer caveat) reconciled.

#### F-14 — Thin test coverage
- **Where:** `tests/test_unify_datasets.py` was the only test (source_identifier prefixing; its
  `Toronto_Major_Crime` mock branch is dead — glob mocked to `[]`). No tests for CRS reprojection,
  dates, dedup, mapping, filtering, census, analyze.
- **Status:** ✅ Every non-network module now has unit tests (39 tests; §7 matrix) — incl. census
  build, year partitioning, `verify_mappings`, standalone-compact, dedup, dates, pagination, and the
  pipeline orchestration. Only `hub.py`/`census_data.py` network I/O is intentionally not unit-tested.

#### F-15 — Minor correctness/cleanliness nits
- `partition_by_year.py:25` imports `shutil` (unused).
- `analyze.py:198-204` applies `per_1k` to the cumulative **Total** column (multi-year sum shown as a
  rate).
- `unify_datasets.py` Durham month map: unrecognised month silently `fillna('01')` → wrong month vs
  `NaT`.
- Halton `original_crime_type` keeps leading whitespace (`" MVC - HIT & RUN"`).
- **Status:** ✅ All nits done — removed unused `shutil`; Durham bad month → `NaT`;
  `original_crime_type` stripped globally; `analyze.py` per-capita "Total" relabeled "Total
  (cumulative)" via `_per_capita_table`. (`tests/test_analyze_percapita.py`)

#### F-16 — Generated-artifact tracking  ✅ verified OK
- **Checked:** `git ls-files data/` → 0 tracked; `visualize-kepler-map/dist/` is gitignored. No large
  data/build artifacts are committed. No action needed.
- **Status:** ✅

#### F-18 — `analyze.py` is York-only and disconnected from the unified dataset 🔎
- **Where:** reads raw York columns (`"Occurrence Date"`, `"Municipality"`, `"Occurrence Type"`,
  `"Special Grouping"`, `"Status"`, `"Location Code"`, `"Shooting"`, `"Hate Crime"`, `x`, `y`);
  `POPULATION` holds only York's 9 municipalities.
- **What:** Despite README framing, it only works on a raw York CSV; it can't consume
  `unified_data.csv` or analyse the other four regions.
- **Fix (decision):** retarget to the unified schema + full GTA population table, or relabel it as a
  York exploratory tool and build a unified analyzer.
- **Status:** ✅ **Decision: Option B.** `analyze.py` relabeled York-only (docstring + README +
  CLAUDE.md) and its CRS bug fixed (F-02). A unified cross-region analyzer remains an optional future
  module.

---

## 4. Empirical measurements

Profiled against `data/01_raw/*` and `data/02_transformed/unified_data.csv` on 2026-06-23
(pre-fix snapshot). Total unified rows: **808,671**.

### 4.1 Coordinate quality (`unified_data.csv`)

| region | total | NaN | null-island (0,0) | out-of-bounds | valid | % null-isl |
|--------|------:|----:|------------------:|--------------:|------:|-----------:|
| Durham | 35,825 | 0 | 0 | 0 | 35,825 | 0.00 |
| Halton | 20,260 | 0 | 0 | 0 | 20,260 | 0.00 |
| Peel | 82,367 | 0 | 0 | 0 | 82,367 | 0.00 |
| Toronto | 427,157 | 0 | **7,560** | 0 | 419,597 | **1.77** |
| York | 243,062 | 0 | 0 | 0 | 243,062 | 0.00 |
| **TOTAL** | **808,671** | 0 | **7,560** | 0 | 801,111 | 0.93 |

GTA box used: lat∈[43.0,44.6], lon∈[−80.6,−78.2]. Only defect = Toronto `(0,0)` (F-03). York's 3857→
4326 reprojection lands correctly (all non-null-island points in-box).

### 4.2 Crime-category taxonomy & mapping coverage

- **`"Other"` rows: 0 dataset-wide.** The JSON covers every post-filter `original_crime_type`
  (`verify_mappings` enforces this by aborting on a gap).
- **Non-canonical `mapped_crime_category`: 27,387 rows (3.39%), 100% Durham** — `Assaults` 15,591 ·
  `Break and Enter` 6,855 · `Drug Violations` 3,529 · `Theft Over 5000` 1,208 ·
  `Shootings and Firearm Discharge` 204.
- Distinct `original_crime_type` per region (post-dedup, so includes `" && "` MULTIPLE combos):
  Toronto 1,081 · Durham 124 · Peel 82 · York 25 · Halton 22.
- Overall top categories: Assault 248,834 (30.8%) · Auto Theft 110,746 · Break & Enter 98,130 ·
  Theft 83,566 · Fraud 47,721 · Public Order 44,743 · Property Damage 34,884 · Robbery 32,950 ·
  MULTIPLE 29,909 · Impaired Driving & Traffic 21,767 · (then the Durham non-canonical labels).
- Durham offence→JSON spot check (confirms T1 works **and** reclassifies): `Assault Level 2`→Assault,
  `B&E - Residential`→Break & Enter, `Theft from MV over $5,000`→Theft, `Home Invasion`→**Break &
  Enter** (was Robbery file), `Carjacking`→**Auto Theft** (was Robbery file),
  `Shootings and Firearm Discharge`→Weapons Offences.

### 4.3 Feed overlap / double-counting

| metric | Toronto MCI | Toronto YTD | York hist | York present |
|--------|------:|------:|------:|------:|
| rows | 474,819 | 22,895 | 177,546 | 65,516 |
| distinct id | 414,033 | 22,082 | 177,546 | 65,516 |
| rows÷id | 1.147 | 1.037 | 1.000 | 1.000 |
| min date | 1964-09-01 | 1969-07-13 | 2021-01-01 | 2025-01-02 |
| max date | 2026-03-31 | 2026-06-17 | 2025-01-01 | 2026-06-17 |

- MCI↔YTD shared `EVENT_UNIQUE_ID`: **8,958**; YTD-only: 13,124. Unified Toronto = 414,033 + 13,124 =
  427,157 ✅ (dedup absorbs the overlap). MCI is one-row-per-offence (ratio 1.147).
- York hist↔present `UniqueIdentifier` intersection: **0** (disjoint); unified York = 243,062 ✅.
- Within `unified_data.csv`: repeated `source_identifier` = **0** (dedup clean). Exact
  `(region,lat,lon,date,type)` duplicates ignoring id = **42,489 (5.25%)** — Halton 21.75% · York
  9.38% · Peel 5.25% · Durham 2.70% · Toronto 2.34% (F-19).

### 4.4 Municipality inventory (distinct values, top by rows)

- **Durham (19)** 3-letter UPPER codes (raw is whitespace-padded): `OSH` 14,388 · `WHI` 5,726 ·
  `AJA` 5,304 · `PIC` 4,661 · `CLA` 3,594 · `SCU` 732 · `BRO` 599 · `UXB` 598 · then cross-boundary
  `TOR` 112, `MAR` 17, `MIS` 11, `VAU` 4, `BRA` 4 … (Durham's 8 home municipalities = Ajax, Brock,
  Clarington, Oshawa, Pickering, Scugog, Uxbridge, Whitby).
- **Halton (6)** UPPER: `OAKVILLE` 10,592 · `BURLINGTON` 5,179 · `MILTON` 2,825 · `GEORGETOWN` 857 ·
  `HALTON HILLS` 639 · `ACTON` 168.
- **Peel (14)** UPPER no-internal-space: `MISSISSAUGA` 42,340 · `BRAMPTON` 39,691 · `TORONTO` 165 ·
  `CALEDON` 63 · `HALTONHILLS` 8 · `RICHMONDHILL` 3 …
- **Toronto (1):** `Toronto` 427,157 (Title).
- **York (9)** Title: `Vaughan` 79,869 · `Markham` 55,391 · `Richmond Hill` 40,625 · `Newmarket`
  22,841 · `Georgina` 12,716 · `Aurora` 12,127 · `East Gwillimbury` 7,180 · `Whitchurch-Stouffville`
  6,737 · `King` 5,576.
- Cross-spelling collisions (normalised): `TORONTO`, `VAUGHAN`, `MARKHAM`, `RICHMONDHILL`,
  `HALTONHILLS` each appear under ≥2 spellings/cases across regions.

### 4.5 Tracked-artifact inventory
`git ls-files data/` → **0**. `visualize-kepler-map/dist/` untracked (gitignored). Only Kepler source
is tracked. No large generated artifacts in git → F-16 resolved.

---

## 5. Remediation backlog (handoff tasks)

Each task names the finding(s) it closes. Check off as completed and add a §6 entry.

### P0 — data-correctness
- [x] **T1 · Route Durham through the canonical taxonomy** (F-01, F-09). Map Durham `offence` via the
      JSON; canonicalised file-category fallback. *Done — see §6.*
- [x] **T2 · Reject null-island / out-of-bounds coordinates** (F-03). GTA-bbox + `(0,0)` check; null
      offending coords in `unify` so the filter quarantines them. *Done — see §6.*
- [x] **T3 · Fix snapshot globbing / feed overlap** (F-05, F-06). Done — newest-snapshot-only + warn;
      `toronto.py` overlap comment fixed; no coordinate dedup key (F-19 showed it would delete data). *See §6.*
- [x] **T4 · Per-DA rate definition** (F-04). Done — **Option C**: headline rate over reference year
      2025 (`REFERENCE_YEAR`); per-year folders keep trends. *See §6.*

### P1 — secondary-output correctness
- [x] **T5 · Fix `analyze.py` anomaly CRS** (F-02). Done — reprojects 3857→26917 before the test. *See §6.*
- [x] **T6 · Fix shooting-arc weapons match** (F-11). `mapped == "Weapons Offences"`. *Done — see §6.*
- [x] **T7 · Normalise municipality names** (F-08). Done — alias map (Durham codes + Peel spellings) +
      Title-case in `unify`; aggregate by true municipality, `region` stays a separate dimension. *See §6.*
- [x] **T8 · Pandera coercion / schema dtypes** (F-07). Done — fixed `toronto_ytd` epoch-ms dtype;
      coercion-capture intentionally skipped (moot under CSV handoff). *See §6.*

### P2 — robustness, hygiene, docs
- [x] **T9 · Harden downloads** (F-12). Done — timeouts + retries; empty-page break; union headers. *See §6.*
- [x] **T10 · Epoch-ms timezone semantics** (F-10). Done — verified local-as-UTC; no date shift. *See §6.*
- [x] **T11 · Reconcile documentation** (F-13). Done — README + CLAUDE.md + DataSets.md. *See §6.*
- [x] **T12 · Expand tests + nits** (F-14, F-15). Done — all non-network modules tested (39); analyze
      "Total" relabeled. *See §6.*
- [x] **T13 · Pipeline data-flow clarity** (F-17). Done — two-phase TRANSFORM/DERIVED split;
      incidents-vs-offences documented. *See §6.*
- [x] **T14 · `analyze.py` future** (F-18). Done — **Option B**: relabel York-only + fix CRS. A unified
      cross-region analyzer is an optional future module. *See §6.*
- [x] **T15 · Placeholder-coordinate anomaly layer** (F-19). Done — **keep data intact** + new
      `coordinate_anomalies.csv` layer (coords ≥50 incidents). Remaining follow-up: wire the Kepler
      layer to render it (+ optional per-year/standalone copies, and a tuned threshold). *See §6.*

### Suggested order
Done: **T1–T15 + the F-19 Kepler anomaly layer (full + standalone profiles).** Audit fully complete —
nothing outstanding.

---

## 6. Work log

| Date | Change | Finding(s) | Verification |
|------|--------|------------|--------------|
| 2026-06-23 | Branch `chore/data-pipeline-audit`; full code read-through; 2 data-profiling sub-agents; wrote this audit. | all | profiling numbers in §4 |
| 2026-06-23 | **T1**: Durham now maps `offence` via the canonical JSON with a canonicalised file-category fallback (`unify_datasets.py`). Removes 27,387 non-canonical labels; also reclassifies Home Invasion→Break & Enter, Carjacking→Auto Theft. | F-01, F-09 | `tests/test_durham_mapping.py` |
| 2026-06-23 | **T6**: shooting-arc weapons match `"Weapons"`→`"Weapons Offences"` (`build_shooting_arcs.py`). | F-11 | `tests/test_shooting_arcs.py` |
| 2026-06-23 | **T2**: `_null_out_of_bounds_coords` nulls (0,0)/out-of-GTA coords in `unify` → quarantined by filter. | F-03 | `tests/test_coordinate_validation.py` |
| 2026-06-23 | Real-data verification of `unify` (880,241 pre-dedup rows): non-canonical labels = `[]`; 8,534 Toronto null coords nulled. | T1, T2 | `uv run python` on `unify_datasets()` |
| 2026-06-23 | Full suite green (`uv run pytest`): 5 passed. | T1, T2, T6 | CI/pytest |
| 2026-06-23 | **T5/F-02**: `analyze.py` anomaly filter reprojects raw 3857 `x,y`→UTM 17N (`webmercator_to_utm17n`); the "filtered" output is now real. | F-02 | `tests/test_analyze_anomaly_crs.py` |
| 2026-06-23 | **T14/F-18 (Option B)**: relabeled `analyze.py` York-only (docstring + README + CLAUDE.md). | F-18, F-13 | docs |
| 2026-06-23 | **T4/F-04 (Option C)**: headline census rate built over `REFERENCE_YEAR=2025`; per-year partitions unchanged. Real data: 127,017 pts in 2025, all 5 regions. | F-04 | `tests/test_reference_year_rate.py` |
| 2026-06-23 | **T15/F-19**: new `build_coordinate_anomalies.py` + pipeline step → `coordinate_anomalies.csv` (separate layer; data intact). Real data: 2,755 coords ≥50 (43.5%). | F-19 | `tests/test_coordinate_anomalies.py` |
| 2026-06-23 | Full suite green: 12 passed. | all | `uv run pytest` |
| 2026-06-23 | **Test-coverage pass**: cross-referenced every logic fix to a test; added 4 tests for previously untested branches (F-01b fallback, F-01c no-offence file, F-03 unify-integration + filter quarantine). Added §7 matrix. | F-01, F-03, F-14 | `uv run pytest` → 16 passed |
| 2026-06-23 | **T7/F-08**: `_normalize_municipality` (Durham code/Peel-spelling aliases + Title-case) in `unify`. Real data: 30 clean municipalities, 0 codes/UPPER, cross-region merged. | F-08 | `tests/test_municipality_normalization.py` |
| 2026-06-23 | **T3/F-05+F-06**: `_drop_stale_snapshots` (newest `*_to_<date>.csv` per source) in `unify`; fixed `toronto.py` overlap comment. | F-05, F-06 | `tests/test_snapshot_selection.py` |
| 2026-06-23 | **F-15 nits**: removed unused `shutil`; Durham bad month → NaT; stripped `original_crime_type` (real data: 0 left). | F-15 | `tests/test_durham_mapping.py`, `tests/test_municipality_normalization.py` |
| 2026-06-23 | Full suite green: 22 passed. | all | `uv run pytest` |
| 2026-06-23 | **T9/F-12**: download hardening — timeouts + bounded retries (`hub.py`, `paginated.py`, `census_data.py`); pagination breaks on empty page; CSV headers union all feature keys. | F-12 | `tests/test_paginated.py` |
| 2026-06-23 | **T11/F-13**: reconciled `docs/DataSets.md` (real commands, `data/01_raw/` output, FeatureServer note). | F-13 | docs |
| 2026-06-23 | Full suite green: 27 passed. | all | `uv run pytest` |
| 2026-06-23 | **T8/F-07**: typed `toronto_ytd` epoch-ms columns `Float` (were `String`); coercion-capture intentionally skipped (CSV handoff makes it moot). Added date-parsing guards. | F-07 | `tests/test_unify_dates.py` |
| 2026-06-23 | **T10/F-10**: investigated epoch-ms tz — local-time-as-UTC, so dates are correct (Peel 0.00% mismatch; Toronto YTD = local midnight). No change needed. | F-10 | real-data check |
| 2026-06-23 | Full suite green: 30 passed. | all | `uv run pytest` |
| 2026-06-23 | Added `deduplicate_incidents` test (multi-offence MULTIPLE/concatenation) — closes a core F-14 gap. | F-14 | `tests/test_deduplicate_incidents.py` (31 passed) |
| 2026-06-23 | **End-to-end run** (`uv run transform`): all 10 steps green (exit 0). Verified products: 801,183 rows · 0 non-canonical labels · 0 null-island · 30 municipalities; 8,593 quarantined to `invalid_data.csv` (Toronto 8,534 `(0,0)`); 2025 rate median 9.23/1k; `coordinate_anomalies.csv` = 2,754 coords. | all | transform log |
| 2026-06-24 | **T13/F-17**: refactored `pipeline.py` into `TRANSFORM_STEPS` (in-memory) + `DERIVED_STEPS` (from disk); removed the fake `df`-threading; documented incidents-not-offences. Behaviour-preserving. | F-17 | `tests/test_pipeline.py` (33 passed) |
| 2026-06-24 | **T12/F-15**: factored `_per_capita_table` (cumulative "Total" → "Total (cumulative)") into `analyze.py` sections 3 & 4. | F-15 | `tests/test_analyze_percapita.py` |
| 2026-06-24 | **T12/F-14**: tests for census build, year partition, `verify_mappings`, standalone-compact — every non-network module now covered. | F-14 | `uv run pytest` → 39 passed |
| 2026-06-24 | **F-19 viz**: wired `coordinate_anomalies.csv` into the Kepler map as Layer 5 (magenta `point`, sized/coloured by `incident_count`); extended `PointLayerSpec`/`buildPointLayer`; embedded in the standalone build (`standaloneLoader` + `build-standalone.mjs` + `build_standalone_compact` copy). | F-19 | `tsc --noEmit` + `yarn build:standalone` green |
| 2026-06-24 | **F-19 refine**: tightened the anomaly cut to **> 200** incidents/coord; added `high_traffic_locations.py` (curated GTA malls/hospitals/attractions/transit) + per-coord classification → new `anomaly_type` / `nearest_location` / `location_category` columns; Layer 5 now colours by `anomaly_type` (amber high-traffic vs magenta unexplained); refreshed viz README to 5 layers. | F-19 | `test_high_traffic_locations.py` + `test_coordinate_anomalies.py` (48 passed) · `tsc --noEmit` clean |
| 2026-06-26 | **F-19 hover legibility**: anomaly classification was invisible on hover (Kepler's tooltip defaults to a dataset's first 5 columns). Added a plain-English `description` column (now leading the CSV column order) + pinned the anomaly layer's tooltip fields via `tooltips.coordinate_anomalies` in `visualization.ts` (threaded through `MapShell`). Hovering a dot now explains its classification. | F-19 | `test_coordinate_anomalies.py` (48 passed) · `tsc --noEmit` + `yarn build:all` green |

**Note for whoever continues:** the data products under `data/02_transformed/` were **regenerated green
on 2026-06-23** with all fixes applied, so they are current. Re-run `uv run transform` after any future
fix (raw downloads must be present in `data/01_raw/`). Headline note: the all-DA `crime_rate_per_1k`
max (~4128/1k) is a placeholder-coordinate artifact (F-19) — trust the median and the anomaly layer;
this is the open viz-wiring follow-up.

_(append entries here as fixes land — include the test/command that proves each fix)_

---

## 7. Fix ↔ test coverage matrix

Every behaviour-changing fix shipped on this branch is locked by at least one unit test. Keep this
table in sync when changing the corrected logic. (`uv run pytest` → **39 passed**.)

| Fix | Behaviour locked | Test(s) |
|-----|------------------|---------|
| **F-01a** Durham offence → canonical via JSON | Durham `mapped_crime_category` is canonical | `test_durham_mapping.py::test_durham_offences_map_to_canonical_categories`, `::test_unify_durham_emits_canonical_category` |
| **F-01b** unmapped offence → canonical fallback | `.mask("Other" → file canonical)`, never `Other` | `test_durham_mapping.py::test_unify_durham_unmapped_offence_falls_back_to_canonical` |
| **F-01c** file with no `offence` column | file category (e.g. shootings) maps canonically | `test_durham_mapping.py::test_unify_durham_shootings_file_without_offence_column` |
| **F-03** helper nulls `(0,0)`/out-of-bounds | `_null_out_of_bounds_coords` | `test_coordinate_validation.py::test_null_island_and_out_of_bounds_coords_are_nulled` |
| **F-03** `unify` applies the nulling | `(0,0)` → NaN in `unify_datasets()` output | `test_coordinate_validation.py::test_unify_applies_coordinate_nulling` |
| **F-03** NaN coords quarantined | filter drops NaN-coord rows → `invalid_data.csv` | `test_filter_invalid_incidents.py::test_nan_coordinates_are_quarantined` |
| **F-11** weapons match | `mapped == "Weapons Offences"` detects weapon incidents | `test_shooting_arcs.py::test_weapons_offences_incident_is_detected` |
| **F-02** reproject 3857→UTM 17N | near-mall flagged; far + raw-3857 not flagged | `test_analyze_anomaly_crs.py` (3 tests) |
| **F-04** reference-year filter | rate counts only the reference year | `test_reference_year_rate.py` (2 tests) |
| **F-19** anomaly detection | coords `> threshold` flagged; empty case handled; classified high-traffic vs unexplained | `test_coordinate_anomalies.py` + `test_high_traffic_locations.py` |
| (pre-existing) source_identifier region prefix | no cross-region ID collision | `test_unify_datasets.py::test_unify_datasets_prevents_source_identifier_collisions` |
| **F-08** municipality normalization | codes/casing/no-space → one Title-case label; original stripped | `test_municipality_normalization.py` (2 tests) |
| **F-05/F-06** stale-snapshot dropping | newest `*_to_<date>.csv` per source kept | `test_snapshot_selection.py` (3 tests) |
| **F-15** Durham bad month → NaT | unrecognised month → NaT, not January | `test_durham_mapping.py::test_unify_durham_bad_month_yields_nat` |
| **F-12** paginated downloader | stops on empty page; CSV headers union all feature keys | `test_paginated.py` (5 tests) |
| **F-07** epoch-ms date parsing | YTD/MCI/Peel dates parse correctly (guards the schema-dtype trap) | `test_unify_dates.py` (3 tests) |
| (core) deduplication | multi-offence → `MULTIPLE` + concatenated; one row per id | `test_deduplicate_incidents.py` |
| **F-17** two-phase orchestration | phase 1 threads + writes CSV; phase 2 builds derived; empty-abort | `test_pipeline.py` (2 tests) |
| **F-15** per-capita "Total" | cumulative Total relabeled, not shown as annual | `test_analyze_percapita.py` |
| (module) census build | boundaries ⋈ demographics; drop pop=0; centroids | `test_build_gta_census.py` |
| (module) year partition | per-year folders; undated rows excluded | `test_partition_by_year.py` |
| (module) verify_mappings | passes when mapped; raises on unmapped | `test_verify_mappings.py` |
| (module) standalone compact | slim cols + rounded coords; arcs copied | `test_standalone_compact.py` |

**Not unit-tested (by design):** F-18 / doc relabels (no logic); the anomaly `threshold` default and the
disk-read branches of `enrich`/`build_coordinate_anomalies` (share logic with the tested in-memory
paths); and the `hub.py` / `census_data.py` network I/O wrappers (timeout/retry/`urlopen`/streaming) —
`paginated.py`'s pure helpers are unit-tested.
