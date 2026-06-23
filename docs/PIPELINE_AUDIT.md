# GTA Urban Analytics — Pipeline Deep-Dive Audit & Remediation Log

**Status:** In progress · **Started:** 2026-06-23 · **Branch:** `chore/data-pipeline-audit`
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
- **Status:** ⬜ (task T5)

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
- **Status:** 🔎 (task T4)

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
- **Status:** ⬜ (task T3)

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
- **Status:** ⬜ (task T3, lower urgency)

#### F-19 — 42,489 exact-tuple duplicate incidents survive dedup (differ only by ID)
- **Where:** data characteristic surfaced via `unified_data.csv`; dedup keys only on
  `source_identifier`.
- **What:** **42,489 rows (5.25%)** share an identical `(region, lat, lon, occurrence_date,
  original_crime_type)` tuple with another row but have distinct `source_identifier`. Concentrated in
  **Halton 21.75%** and **York 9.38%** (Peel 5.25%, Durham 2.70%, Toronto 2.34%).
- **Impact:** Either genuine re-published duplicates (over-counting) or an artifact of
  coordinate-snapping (e.g. Halton geocoding many incidents to a block/centroid). Halton at ~22% is
  high enough to warrant investigation before trusting Halton counts/rates.
- **Fix:** Investigate (are duplicate tuples same incident re-published, or distinct events at a
  snapped coordinate?). If re-publish, add the secondary dedup key from F-06.
- **Status:** 🔎 (task T15)

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
- **Status:** ⬜ (task T8)

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
- **Status:** ⬜ (task T7)

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
- **Status:** ⬜ (task T10)

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
- **Status:** ⬜ (task T13)

### 🟡 Low severity / robustness / docs

#### F-12 — Network downloads lack timeouts, retries, robust termination
- **Where:** `arcgis/hub.py` (no timeout; only `HTTPError` caught; unbounded polling),
  `arcgis/paginated.py` (no timeout/retry; **infinite-loop risk** if `exceededTransferLimit=True` with
  empty `features`; CSV headers from the *first* feature only → columns missing on feature 0 are
  dropped), `statcan/census_data.py` (no timeout; whole ZIP buffered in memory).
- **Fix:** timeouts, bounded retry/backoff, break-on-empty-page, union feature keys for headers.
- **Status:** ⬜ (task T9)

#### F-13 — Documentation drift
- **Where:** `README.md` §4/§5 (presents `analyze` as a multi-region engine — it's York-raw-only);
  `gta-urban-analytics/CLAUDE.md` (category list says `Drug Violations / Weapons / Sexual Assault /
  Mischief`; the JSON uses `Drug Offences / Weapons Offences / Sexual Offences / Property Damage`);
  `docs/DataSets.md` (non-existent scripts like `download_durham_data.py`, stale `dataSetDownloads/`
  paths, a Halton GIS id that no longer matches the FeatureServer URL the code uses).
- **Status:** ⬜ (task T11)

#### F-14 — Thin test coverage
- **Where:** `tests/test_unify_datasets.py` was the only test (source_identifier prefixing; its
  `Toronto_Major_Crime` mock branch is dead — glob mocked to `[]`). No tests for CRS reprojection,
  dates, dedup, mapping, filtering, census, analyze.
- **Status:** 🟡 (added Durham-mapping, coord-validation, shooting-arc tests this session; more in T12)

#### F-15 — Minor correctness/cleanliness nits
- `partition_by_year.py:25` imports `shutil` (unused).
- `analyze.py:198-204` applies `per_1k` to the cumulative **Total** column (multi-year sum shown as a
  rate).
- `unify_datasets.py` Durham month map: unrecognised month silently `fillna('01')` → wrong month vs
  `NaT`.
- Halton `original_crime_type` keeps leading whitespace (`" MVC - HIT & RUN"`).
- **Status:** ⬜ (task T12)

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
- **Status:** 🔎 (task T14)

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
- [ ] **T3 · Fix snapshot globbing / feed overlap** (F-05, F-06). Newest-snapshot-only selection (or
      stable filenames) + warn on multiples; fix the wrong `toronto.py` "end of previous year" comment;
      consider a secondary dedup key.
- [ ] **T4 · Decide & implement the per-DA rate definition** (F-04) 🔎. annualised / fixed-window /
      per-year-only; implement; document.

### P1 — secondary-output correctness
- [ ] **T5 · Fix `analyze.py` anomaly CRS** (F-02). Reproject `x,y` 3857→26917 before the 500 m test;
      regression-test a near-mall point.
- [x] **T6 · Fix shooting-arc weapons match** (F-11). `mapped == "Weapons Offences"`. *Done — see §6.*
- [ ] **T7 · Normalise municipality names** (F-08). strip→title-case + Durham code expansion; decide
      cross-region handling; test `AJA`→`Ajax`, `BURLINGTON`→`Burlington`.
- [ ] **T8 · Capture Pandera coercion — carefully** (F-07). First align schema dtypes with epoch-ms
      parsing (else YTD dates → NaT), then capture the validated frame.

### P2 — robustness, hygiene, docs
- [ ] **T9 · Harden downloads** (F-12). timeouts, retries/backoff, break-on-empty-page, union headers.
- [ ] **T10 · Verify epoch-ms timezone semantics** (F-10). cross-check + document.
- [ ] **T11 · Reconcile documentation** (F-13). README analyze scope; CLAUDE.md category list;
      DataSets.md entry points/ids.
- [ ] **T12 · Expand tests + nits** (F-14, F-15). dedup/date/filter tests; remove unused `shutil`;
      `NaT` on bad Durham month; strip Halton original; relabel analyze "Total" rate column.
- [ ] **T13 · Pipeline data-flow clarity** (F-17). honest threading or explicit write-then-read;
      document incidents-vs-offences.
- [ ] **T14 · Decide `analyze.py` future** (F-18) 🔎. retarget to unified schema or relabel.
- [ ] **T15 · Investigate 42,489 exact-tuple duplicates** (F-19). re-publish vs coordinate-snapping;
      start with Halton (21.75%). If re-publish, add secondary dedup key (ties to T3).

### Suggested order
T1✅ → T6✅ → T2✅ → T5 → T7 → T8 → T3 → T15 → T4 → T9-T14.

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

**Note for whoever continues:** the data products under `data/02_transformed/` are stale w.r.t. these
fixes. Regenerate with `uv run transform` (downloads must already be present) so `unified_data.csv`,
the census GeoJSON, shooting arcs, and yearly partitions reflect the canonical Durham labels and the
dropped null-island points.

_(append entries here as fixes land — include the test/command that proves each fix)_
