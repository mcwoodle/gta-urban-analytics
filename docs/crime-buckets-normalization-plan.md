# Plan: Cross-Region Normalization + Crime-Type Buckets + Per-Year Honesty

> **Status:** Planned — not yet implemented. Authored 2026-06-26. This is a design
> document; the implementation steps below have not been built.

## Context

The GTA map currently shows crime as one undifferentiated mass. Three real gaps block honest interpretation:

1. **Reporting differences aren't normalized for comparison.** The pipeline already canonicalizes 15 crime categories, reprojects coordinates, and computes a per-capita `crime_rate_per_1k` windowed to `REFERENCE_YEAR=2025` (audit F-04). But the regions cover wildly different time spans (Toronto volume from 2014, Halton only ~2025-06→2026-06) and publish different *subsets* of crime — Durham ships only 7 single-crime-type files, so it literally never reports Fraud, Sexual Offences, Public Order, etc. Nothing records these coverage gaps, so any naive cross-region count misleads.
2. **No way to view crime by type.** All 15 categories are lumped together; there's no high-level bucketing (violent / property / nuisance) and no map control to select among types. The viz never colors by crime category at all.
3. **Partial-year (2026) isn't marked.** Per-year partitions (2020–2026) exist, but 2026 is year-to-date with no labeling, so it reads as a full year.

**Outcome:** a `crime_group` bucket dimension computed in the pipeline; per-bucket per-capita rates per Dissemination Area; explicit coverage metadata (which region reports what, and 2026's YTD status); and an interactive map control that recolors the per-capita rate choropleth by bucket *and* filters a crime-point layer to show where each bucket concentrates.

**Decisions locked with the user:**
- **4 buckets** — Violent / Property / Nuisance / Other.
- **Both views** — the bucket control drives the per-capita rate choropleth recolor (headline) AND a filtered crime-point layer (spatial detail).
- Per the repo's hard rule: **all binning/bucketing lives in the Python pipeline; the viz only renders and interacts.**

### Bucket taxonomy (15 → 4)

| Bucket (`crime_group`) | slug | Canonical categories |
|---|---|---|
| **Violent** | `violent` | Assault, Sexual Offences, Robbery, Homicide, Threats & Harassment, Weapons Offences |
| **Property** | `property` | Break & Enter, Theft, Auto Theft, Fraud, Property Damage |
| **Nuisance** | `nuisance` | Public Order, Drug Offences, Impaired Driving & Traffic |
| **Other** | `other` | Missing Person (+ runtime `MULTIPLE` and any unmapped `Other`) |

Judgment calls (documented in code + strategy doc): Weapons Offences → Violent; Impaired Driving & Traffic → Nuisance; `MULTIPLE` → Other (auditable via coverage metadata).

---

## Pipeline changes

### P1 — Bucket taxonomy module *(new)*
`src/gta_urban_analytics/transform/crime/crime_groups.py`
- `CRIME_GROUPS: dict[str, list[str]]` — the 4 buckets → canonical-category lists above (Python constant with judgment-call comments, mirroring the sibling `_DURHAM_CANONICAL_CATEGORY` / `_MUNICIPALITY_ALIASES` constants).
- `CATEGORY_TO_GROUP: dict[str, str]` — inverse, built at import.
- `GROUP_SLUGS: dict[str, str]` — display name → slug (`Violent`→`violent`, …) for column naming.
- `assign_crime_group(df) -> df` — adds `crime_group` via `df['mapped_crime_category'].map(CATEGORY_TO_GROUP).fillna('Other')`. Because it reads the **post-dedup** category, `MULTIPLE` and unmapped `Other` both fall to the `Other` bucket.

### P2 — Wire into Phase 1 (after dedup)
`src/gta_urban_analytics/transform/pipeline.py`
- Append to `TRANSFORM_STEPS`, **after** `"Deduplicating incidents"`: `("Assigning crime groups", assign_crime_group)`.
- **Critical:** must run after dedup — `deduplicate_incidents.py:40` overwrites `mapped_crime_category` to `MULTIPLE`, so deriving the group earlier would be inconsistent. `crime_group` then persists into `unified_data.csv` and flows to every downstream reader.

### P3 — Per-bucket per-DA counts + rates
`src/gta_urban_analytics/transform/census/enrich_with_crime_rate.py`
- Add `crime_group` to `load_cols` (line ~141), **guarded** so existing bare `lat/lon` test fixtures still work.
- New helper `_assign_bucket_rates(enriched, joined, pop, too_small)`: pivot `joined.groupby(['DAUID','crime_group']).size()` wide; for each of the 4 buckets write `crime_count_<slug>` and `crime_rate_<slug>_per_1k = count/pop*1000`, applying the same `too_small` / `_MIN_POPULATION_FOR_RATE=50` nulling as the total. Missing bucket in a DA → 0 count, rate via same rule.
- Call it after the existing total-count merge (line ~194); leave `crime_count` / `crime_rate_per_1k` totals and `_assign_bivariate()` **byte-identical**.
- Extend the idempotency drop-list (line ~136) to drop the 8 new columns on re-run.
- Per-bucket rates inherit the existing `reference_year` filter (2025 headline) and the per-year `reference_year=None` path automatically.

### P4 — Coverage metadata builder *(new)*
`src/gta_urban_analytics/transform/build_coverage_metadata.py`
- `build_coverage_metadata(crime_df=None, year=None, output_dir=None)` → writes `coverage.json`.
- Reads `unified_data.csv` when `crime_df` is None.
- Top-level payload: `regions` → `{min_date, max_date, n_incidents, categories_present:[...], groups_present:[...]}` plus a `category_x_region` boolean matrix (makes the Durham / Toronto-MCI subset gaps explicit), plus a `multiple_count` per region/year (audits the `MULTIPLE`→Other folding from R1).
- When `year` set: restrict to that year and add `{year, as_of_date, is_partial, days_elapsed, days_in_year, fraction_elapsed, same_period_prior_year_incidents}`. `is_partial = (year == datetime.now().year)`. SPPY = prior year's incidents within Jan 1 → same month/day as `as_of_date`, computed from the **all-years** frame.
- **2026 YTD:** raw YTD count + SPPY comparison, **no annualized projection** (×365/N ignores crime seasonality and would mislead — matches the user's explicit "2026 YTD" framing).

### P5 — Wire coverage into both scopes
- `pipeline.py`: add a `DERIVED_STEP` after enrichment — `("Building coverage metadata", lambda: build_coverage_metadata())` → top-level `data/02_transformed/coverage.json`.
- `src/gta_urban_analytics/transform/partition_by_year.py`: inside the per-year loop (after the standalone-compact step, ~line 114) call `build_coverage_metadata(crime_df=crime_df, year=year, output_dir=year_dir)` (pass the all-years frame so SPPY works). The existing `range(2020, current_year+1)` already emits the 2026 folder — no slicing change.

### P6 — Carry new columns into compacts
`src/gta_urban_analytics/transform/build_standalone_compact.py`
- `_COMPACT_CRIME_COLUMNS` += `"crime_group"`.
- `_COMPACT_CENSUS_PROPERTIES` += the 4 `crime_rate_<slug>_per_1k` (required) and 4 `crime_count_<slug>` (for honest tooltips). Existing `missing`-column warning surfaces any gap.

---

## Viz changes (`visualize-kepler-map`)

### V1 — Crime-group colors + point layer
`src/config/visualization.ts`
- `export const CRIME_GROUP_COLORS: ColorRangeSpec` — 4 qualitative colors, **ordered to Kepler's alphabetical ordinal sort of the domain**: `Nuisance, Other, Property, Violent` (same gotcha the `ANOMALY_CLASS` comment documents). Suggest: Violent=red, Property=amber, Nuisance=teal, Other=grey.
- New `kind:'point'` layer `crime_by_group` on `dataId:'crime_points'`, `isVisible:false`, `colorField:{name:'crime_group',type:'string'}`, `colorScale:'ordinal'`, `colorRange:CRIME_GROUP_COLORS`. Reuses existing `PointLayerSpec`/`buildPointLayer` — **no `types.ts` change**.
- Mechanism B reuses the existing hidden `crime_rate_choropleth` layer (no new layer).
- Add `crime_group` + the 4 bucket counts to the `crime_points` / `census_da` tooltip `fieldsToShow`.

### V2 — Crime-group control overlay *(new)*
`src/components/CrimeGroupControl.tsx` — modeled on `RadiusControl.tsx` (mutate-Kepler-state, NOT data reload; buckets are an already-loaded column).
- Segmented single-select: **Total · Violent · Property · Nuisance · Other**.
- Generalize `hooks/useHexbinLayer.ts` → `useLayerById(id)` reading `state.keplerGl.map.visState.layers`; a second selector reads `state.keplerGl.map.visState.datasets['census_da'].fields`.
- On select (`forward = wrapTo('map')`):
  - **B (rate choropleth):** resolve the real Kepler `Field` from `datasets.census_da.fields` (must be the Field object, not a bare `{name,type}` — R3), then `dispatch(forward(layerConfigChange(rateLayer,{isVisible:true})))` + `dispatch(forward(layerVisualChannelConfigChange(rateLayer,{colorField:<field>},'color')))`. `Total`→`crime_rate_per_1k`; bucket→`crime_rate_<slug>_per_1k`. Hide `income_crime_bivariate` while a bucket is active; restore on `Total` (R6 — avoid stacked census choropleths).
  - **A (point filter):** lazily `addFilter('crime_points')` once, cache idx from `visState.filters`, then `setFilter(idx,'name','crime_group')` + `setFilter(idx,'value',[group])`, and show the `crime_by_group` point layer (`layerConfigChange isVisible:true`). `Total` → `removeFilter(idx)` + hide the point layer (keeps first paint light; 126k points only render when a bucket is chosen).

### V3 — Crime-group legend *(new)*
`src/components/CrimeGroupLegend.tsx` — modeled on `BivariateLegend.tsx`; visible while `crime_rate_choropleth` is visible. Shows the active bucket, the sequential rate ramp, and a coverage caveat sourced from `coverage.json` (e.g. "Durham reports only Violent + Property · 2026 is YTD through <as_of_date>").

### V4 — Mount + coverage fetch
`src/components/MapShell.tsx`
- Inside the `loaded` block, add `{getProfile() !== 'lite' && <CrimeGroupControl />}` and `{getProfile() !== 'lite' && <CrimeGroupLegend />}` beside `RadiusControl`/`BivariateLegend`.
- Add a small `useCoverage(year)` hook (or extend `data/loaders.ts`) fetching `coverage.json` via the existing `urlForYear` rewrite so the legend warning is data-driven.
- **lite/standalone caveat (R4):** lite loads only `crime_heatmap_lite` (no `crime_points`/`census_da`) — control gated off there. Full `standalone.html` already embeds `crime_group` + bucket columns via compacts; `coverage.json` is not embedded by `build-standalone.mjs`, so the legend degrades to a static "data may be partial" note there (or add it as a 5th payload — optional follow-up).

---

## Docs
- `visualize-kepler-map/README.md` — bump layer count, document the bucket control + per-capita normalization story.
- `CLAUDE.md` — note the 15→4 `crime_group` step (`crime_groups.py`) in the Crime Category Mapping section; note per-bucket rate columns + `coverage.json` in the Analyze section.
- `docs/kepler-viz-plan.md` — dated addendum for the bucket control + per-bucket choropleth.
- `docs/normalization-strategy.md` *(new)* — the thread-1 deliverable: reference-year 2025 framing, the reporting-completeness matrix, 2026-YTD + same-period-prior-year handling, and the MULTIPLE / Weapons judgment calls with rationale.

## Tests (mirror `test_bivariate_class.py` / `test_reference_year_rate.py`)
- `tests/test_crime_groups.py` — all 15 categories map to the expected bucket; `MULTIPLE`/`Other`/unknown → Other; every canonical value covered exactly once; `assign_crime_group` idempotent.
- `tests/test_per_bucket_rate.py` — enrichment emits all 4 `crime_count_<slug>` / `crime_rate_<slug>_per_1k`; per-bucket counts sum to total `crime_count`; small-pop nulling per bucket; `reference_year` still narrows; `bivariate_class` unaffected.
- `tests/test_coverage_metadata.py` — per-region min/max dates; matrix flags a Durham-style subset; `is_partial`/`fraction_elapsed` for current year; SPPY restricts prior year to same window.
- Extend `tests/test_standalone_compact.py` — `crime_group` in compact crime cols; per-bucket rate cols in compact census props.
- Extend `tests/test_partition_by_year.py` — each populated year folder gets a `coverage.json`.

---

## Risks / edge-cases
- **R1 MULTIPLE→Other** undercounts Violent/Property for multi-offence incidents; coverage.json reports the per-region `MULTIPLE` count so it's auditable; strategy doc notes a precedence-mapping alternative.
- **R2 Durham/Toronto-MCI coverage gaps** make even per-capita bucket rates structurally low for missing categories — never present bucket rates without the legend/coverage caveat. (This is why raw-count-only was rejected.)
- **R3 Kepler colorField swap** needs the real dataset `Field` object, not `{name,type}`.
- **R4 lite/standalone degradation** — gate on `getProfile() !== 'lite'`; coverage.json not embedded in standalone (legend degrades).
- **R5 filter idx churn** — create the `crime_group` filter once, cache its id.
- **R6 stacked choropleths** — hide bivariate while a bucket rate is active.
- **R7 2026 sparsity** — Halton starts ~2025-06, so some 2026 buckets are tiny; small-pop nulling + `is_partial` flag guard it.

## Verification (end-to-end)
```bash
# Pipeline (repo root)
uv run transform
ls data/02_transformed/coverage.json data/02_transformed/2026/coverage.json
python -c "import pandas as pd; print(pd.read_csv('data/02_transformed/unified_data.csv', usecols=['crime_group'])['crime_group'].value_counts())"
python -c "import geopandas as gpd; g=gpd.read_file('data/02_transformed/gta_census_da.geojson'); print([c for c in g.columns if c.startswith('crime_rate_')])"
python -c "import json; print(json.load(open('data/02_transformed/2026/coverage.json'))['is_partial'])"

# Tests
uv run pytest

# Viz typecheck + build
cd visualize-kepler-map
node_modules/.bin/tsc --noEmit
yarn build && yarn build:standalone

# Dev smoke: toggle Total/Violent/Property/Nuisance/Other — choropleth recolors,
# points filter + recolor, legend surfaces the partial-year / coverage warning.
yarn start   # http://localhost:8080
```
Expected: `crime_group` with 4 values; 8 per-bucket columns on the GeoJSON; `coverage.json` top-level and per-year (`is_partial:true` for 2026); `tsc`/build clean; bucket control recolors + filters live.

## Delivery
Feature branch `feat/crime-type-buckets-normalization`; conventional commits; draft PR → monitor CI → mark ready-for-review when green (no CI is currently configured in this repo); leave merge to the owner. Data files are gitignored — only code/tests/docs are committed; data is regenerated via `uv run transform`.
