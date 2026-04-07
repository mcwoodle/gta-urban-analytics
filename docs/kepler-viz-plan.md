# Kepler.gl Visualization Sub-Project for GTA Urban Analytics

## Context

The `gta-urban-analytics` repo already produces unified crime data and census polygons in `data/02_transformed/` via `uv run full-pipeline`. This plan adds a self-contained `vizualize-kepler-map/` sub-project that renders the same data as a curated, four-layer Kepler.gl map, driven from a single typed config file so layer choice and styling can be tweaked without touching React code. The map fits the GTA on first paint, supports a custom radius slider for the hexbin, and uses the central config to hold all knobs (datasets, layers, colors, opacity, sizes).

**Strict separation of concerns:** the visualization sub-project performs **zero data transformation**. Every file it loads is produced by `uv run full-pipeline`. The two derived datasets the viz needs (DA crime-rate enrichment, shooting arcs) are added as new steps inside the existing `src/gta_urban_analytics/transform/` tree — see §"Pipeline Transform Additions" below.

**Three deploy targets:** the same source must support (1) the live dev loop on `localhost:8080`, (2) a production build that outputs a self-contained static site to `dist/`, deployable to any static host (GitHub Pages, S3, Netlify, plain `python -m http.server`) with no Node runtime, and (3) a single `dist/standalone.html` file that **works when opened directly via `file://`** in a browser — i.e. all data and JS embedded inside the HTML, no `fetch()`, no sibling files required. See §"Static Build Output" for how this is made possible without producing a 200 MB HTML file.

---

## Source Data (already exists in WSL)

| Path | Size | Notes |
|---|---|---|
| `data/02_transformed/unified_data.csv` | 96 MB, **754,113 rows** | Columns: `source_file_name, source_identifier, region, mapped_crime_category, occurrence_date, lat, lon, municipality, original_crime_type`. Already WGS84 (no UTM conversion). All 5 GTA police services merged. |
| `data/02_transformed/gta_census_da.geojson` | 37 MB, **8,488 features** | Statistics Canada Dissemination Areas. Properties: `DAUID, Population, Median_Income, centroid_lat, centroid_lon`, plus `crime_count` and `crime_rate_per_1k` (added by the new enrichment step — see §"Pipeline Transform Additions"). Polygon geometry. |
| `data/02_transformed/shooting_arcs.csv` | derived | Produced by the new `build_shooting_arcs` transform step. Columns: `id, src_lat, src_lon, dst_lat, dst_lon, year, municipality, count_in_muni`. |
| `data/02_transformed/invalid_data.csv` | 8 KB | Not used by viz. |

The Kepler.gl reference is already cloned at `/home/mcwoodle/workspace/kepler.gl/examples/get-started/` with `node_modules` installed — copy `package.json`, `esbuild.config.mjs`, `tsconfig.json`, and `.yarnrc.yml` from there as the starting scaffold.

---

## Sub-Project Layout

```
/home/mcwoodle/workspace/crime-data/vizualize-kepler-map/
├── package.json                # esbuild + @kepler.gl/* + react 18 + redux; scripts: start, build, build:standalone
├── esbuild.config.mjs          # dual-mode: dev server :8080 OR production bundle → dist/
├── scripts/
│   └── build-standalone.mjs    # post-build: gzip+base64 the compact data, inline bundle, emit dist/standalone.html
├── tsconfig.json
├── .yarnrc.yml
├── .gitignore                  # node_modules/, dist/, .env, public/data
├── .env.example                # MapboxAccessToken=pk....
├── README.md                   # how to run + data prereqs + static deploy notes
├── public/
│   ├── index.html              # <div id="root"/> + <script src="bundle.js"> — copied verbatim into dist/
│   └── data/                   # symlink → ../../data/02_transformed (gitignored)
├── dist/                       # production build output (gitignored) — see §"Static Build Output"
│   ├── index.html              # multi-file static site entry
│   ├── bundle.js               # single, self-contained JS bundle (no code splitting)
│   ├── standalone.html         # single-file: JS bundle + gzipped data ALL embedded; works via file://
│   └── data/                   # copied from data/02_transformed at build time (NOT a symlink)
└── src/
    ├── index.tsx               # ReactDOM mount
    ├── app.tsx                 # <Provider><MapShell/></Provider>
    ├── store.ts                # Redux store (keplerGlReducer + taskMiddleware)
    ├── config/
    │   └── visualization.ts    # ★ SINGLE source of truth for datasets/layers/mapState
    ├── data/
    │   ├── loaders.ts          # fetch + processCsvData / processGeojson
    │   └── types.ts            # local TS types for the config
    ├── layers/
    │   ├── index.ts            # buildLayers() — dispatch by kind
    │   ├── hexbinLayer.ts      # Layer 1 builder
    │   ├── geojsonLayer.ts     # Shared builder for Layers 2 + 3
    │   └── arcLayer.ts         # Layer 4 builder
    ├── components/
    │   ├── MapShell.tsx        # AutoSizer + KeplerGl + overlay
    │   └── RadiusControl.tsx   # custom slider (top-left, abs positioned)
    └── hooks/
        └── useHexbinLayer.ts   # selector returning the hexbin layer instance
```

`public/data/` will be a **symlink** to `../../data/02_transformed/` so the dev server serves the existing files in-place — no copying, no duplication. Create with `ln -s ../../data/02_transformed public/data` from inside `vizualize-kepler-map/`. Symlink target is gitignored.

---

## The Central Config — `src/config/visualization.ts`

This is the **only** file the user touches to add/remove datasets, swap layer types, change colors, opacities, sizes, or tune the initial viewport. Discriminated union (`kind`) on each layer; `layers/index.ts` does a `switch` to route to the right builder.

```ts
// src/config/visualization.ts — SHAPE SKETCH
export interface VisualizationConfig {
  datasets: DatasetSpec[];
  layers: LayerSpec[];
  mapState: { longitude: number; latitude: number; zoom: number; pitch: number; bearing: number };
  mapStyle: 'dark' | 'light' | 'satellite' | 'muted';
}

export type DatasetSpec = { id: string; label: string; url: string; visible: boolean };

export type LayerSpec = HexbinLayerSpec | GeoJsonLayerSpec | ArcLayerSpec;

export const VIZ_CONFIG: VisualizationConfig = {
  datasets: [
    { id: 'crime_points',  label: 'Unified GTA Crime',          url: 'data/unified_data.csv',     visible: true },
    { id: 'census_da',     label: 'Census Dissemination Areas', url: 'data/gta_census_da.geojson', visible: true },
    { id: 'shooting_arcs', label: 'Shooting → Centroid Arcs',   url: 'data/shooting_arcs.csv',    visible: false },
  ],
  // URLs are RELATIVE (no leading slash) so the static build deploys cleanly under any path
  // prefix (e.g. https://example.com/gta-viz/) and standalone.html works when opened from a
  // sibling directory. Note: Layers 2 and 3 share the single 'census_da' dataset — both
  // Median_Income and crime_rate_per_1k live as properties on the same GeoJSON, populated
  // by the pipeline.
  layers: [
    { kind: 'hexbin',  /* Layer 1 — see §"Layer 1" */ },
    { kind: 'geojson', /* Layer 2 — see §"Layer 2" */ },
    { kind: 'geojson', /* Layer 3 — see §"Layer 3" */ },
    { kind: 'arc',     /* Layer 4 — see §"Layer 4" */ },
  ],
  // GTA-fitting viewport: covers Toronto + Halton + Peel + York + Durham
  mapState: { longitude: -79.40, latitude: 43.85, zoom: 8.6, pitch: 35, bearing: 0 },
  mapStyle: 'dark',
};
```

Rationale: discriminated union catches typos at compile time, single boolean toggles a layer, and every styling knob (colorRange, opacity, worldUnitSize, elevationScale, colorField name) is one edit away — no React/Redux churn for tweaks.

---

## Layer Specifications

### Layer 1 — Unified Crime Hexbin

- Kepler type: `'hexagon'`
- `dataId: 'crime_points'`, `columns: { lat: 'lat', lng: 'lon' }`
- `visConfig`: `worldUnitSize: 0.2` (km, per spec), `elevationScale: 50` (per spec), `enable3d: true`, `coverage: 0.95`, `opacity: 0.85`
- `colorRange`: sequential warm palette (e.g., Uber "Global Warming")
- 754K points → Kepler's GPU aggregation handles this fine; if dev-load is sluggish add a year filter (Kepler exposes the filter panel automatically since `occurrence_date` is a string the user can convert to a date column inside Kepler).

### Layer 2 — Median Income Choropleth

- Kepler type: `'geojson'`
- `dataId: 'census_da'`
- `visConfig`: `opacity: 0.4` (per spec), `filled: true`, `stroked: false`
- `colorField: { name: 'Median_Income', type: 'real' }`, `colorScale: 'quantile'` (quantile is essential — DA incomes are heavily right-skewed)
- `colorRange`: sequential blue/green (e.g., ColorBrewer YlGnBu-6)

### Layer 3 — Crime Rate per 1,000 People

- Kepler type: `'geojson'`
- `dataId: 'census_da'` — same dataset as Layer 2; the pipeline's enrichment step adds `crime_count` and `crime_rate_per_1k` as properties on the existing DA features (see §"Pipeline Transform Additions")
- `visConfig`: `opacity: 0.55`, `filled: true`, `stroked: true`, `strokeColor: [255,255,255]`, `strokeOpacity: 0.6`
- `colorField: { name: 'crime_rate_per_1k', type: 'real' }`, `colorScale: 'quantize'`
- `colorRange`: sequential teal-to-navy

### Layer 4 — Shootings → Municipality Centroid Arcs (creative)

- Kepler type: `'arc'`
- `dataId: 'shooting_arcs'`
- Source data is a **CSV** with columns: `id, src_lat, src_lon, dst_lat, dst_lon, year, municipality, count_in_muni`
- `columns: { lat0: 'src_lat', lng0: 'src_lon', lat1: 'dst_lat', lng1: 'dst_lon' }`
- `visConfig`: `opacity: 0.85`, `thickness: 2`, `targetColor: [255, 80, 80]`
- `colorField: { name: 'year', type: 'integer' }` (color by year)
- `sizeField: { name: 'count_in_muni', type: 'integer' }` (height varies by municipality density)
- Why this layer: visually distinct from the three flat/extruded blob layers (arcs read as flows), and it tells a story about how shootings cluster relative to municipal centers — a dimension the hexbin and choropleths can't show.

---

## Pipeline Transform Additions

The visualization sub-project performs **no data transformation** of its own. The two derived datasets it consumes (DA crime-rate enrichment, shooting arcs) are produced by new modules added to the existing `src/gta_urban_analytics/transform/` tree and wired into `transform/pipeline.py`. After running `uv run full-pipeline` (or just `uv run transform`), every file the viz needs is already on disk under `data/02_transformed/` and the viz can load them as-is.

Both new modules reuse the project's existing `pandas`/`geopandas`/`pyproj` dependencies — no new packages required. Each is independently callable (useful when iterating on filter logic) and idempotent: re-running `uv run transform` rebuilds everything from scratch.

### New module: `src/gta_urban_analytics/transform/census/enrich_with_crime_rate.py`

Adds `crime_count` and `crime_rate_per_1k` properties to each Dissemination Area in `data/02_transformed/gta_census_da.geojson`. Lives in the `census/` subpackage because it mutates the census output, even though its input includes crime data.

Public function: `enrich_census_with_crime_rate(verbose: bool = True) -> gpd.GeoDataFrame`

1. Read `data/02_transformed/unified_data.csv` (lat/lon points produced by Step 3 of the pipeline)
2. Read `data/02_transformed/gta_census_da.geojson` (DA polygons + Population produced by Step 4)
3. Build a `GeoDataFrame` of crime points in `EPSG:4326`, then `geopandas.sjoin` to the DAs (point-in-polygon, `how='left', predicate='within'`)
4. Group by `DAUID` → `crime_count`
5. Compute `crime_rate_per_1k = crime_count / Population * 1000`. Where `Population < 50` set both `crime_count` and `crime_rate_per_1k` to `NaN` (Kepler renders nulls as transparent) to avoid noisy small-DA spikes
6. Merge the two new columns onto the existing DA GeoDataFrame and **overwrite** `data/02_transformed/gta_census_da.geojson` in place — same file path, additional properties, no second GeoJSON to manage

### New module: `src/gta_urban_analytics/transform/crime/build_shooting_arcs.py`

Produces `data/02_transformed/shooting_arcs.csv`. Lives in the `crime/` subpackage because it derives entirely from the unified crime CSV.

Public function: `build_shooting_arcs(verbose: bool = True) -> pd.DataFrame`

1. Read `data/02_transformed/unified_data.csv`
2. Filter to rows where `original_crime_type` matches `r'(?i)shoot|firearm'` **OR** `mapped_crime_category == 'Weapons'`
3. Group the **full** unified DataFrame (not just shootings) by `municipality` → compute centroid as `mean(lat)`, `mean(lon)` of all crime points in that municipality, plus the total `count_in_muni`
4. For each filtered shooting row, emit one output row: `(src_lat, src_lon) = shooting location`, `(dst_lat, dst_lon) = its municipality's centroid`, `year = occurrence_date[:4]` parsed to int, plus `municipality` and `count_in_muni` (joined from the centroid table)
5. Drop rows whose municipality lacks a centroid (e.g. blank/unknown municipality strings)
6. Write columns `id, src_lat, src_lon, dst_lat, dst_lon, year, municipality, count_in_muni` to `data/02_transformed/shooting_arcs.csv` (`id` is a stable row index over the shooting rows)

### New module: `src/gta_urban_analytics/transform/build_standalone_compact.py`

Produces compact variants of the three viz datasets, written to `data/02_transformed/standalone/`. These exist purely so the standalone HTML build can embed them at a manageable size — the dev server and the multi-file static build still use the full datasets. This module is the **only** place where viz-driven downsizing happens; the viz code itself never simplifies, samples, or drops columns.

Public function: `build_standalone_compact(verbose: bool = True) -> None`

1. **Compact crime points** — read `unified_data.csv`, keep only `lat`, `lon`, `mapped_crime_category`, `occurrence_date`, `region` (the columns the four layers actually consume), round `lat`/`lon` to 5 decimal places (≈1 m precision, more than enough for hexbin aggregation), and write `data/02_transformed/standalone/unified_data_compact.csv`. All 754K rows are preserved so the hexbin and radius slider remain fully interactive — only column count and float precision shrink.
2. **Compact census GeoJSON** — read `gta_census_da.geojson`, reproject to `EPSG:26917`, run `geometry.simplify(tolerance=20, preserve_topology=True)` (20 m is invisible at the GTA-wide zoom we render), reproject back to `EPSG:4326`, keep only the properties Layers 2 and 3 use (`DAUID`, `Population`, `Median_Income`, `crime_count`, `crime_rate_per_1k`), and write `data/02_transformed/standalone/gta_census_da_compact.geojson`.
3. **Shooting arcs** — already small; copy `shooting_arcs.csv` to `data/02_transformed/standalone/shooting_arcs.csv` unchanged.

Expected size reductions (rough estimates, validate during implementation): crime CSV ~96 MB → ~25 MB → ~6 MB gzipped; census GeoJSON ~37 MB → ~10 MB → ~2 MB gzipped. After base64 encoding the embedded payload should land around 10–12 MB — large but well within what browsers handle, and a fraction of what naïve embedding would produce.

### `transform/pipeline.py` updates

Extend `run()` from a 4-step to a 7-step pipeline. The new steps go at the end so they can read the on-disk outputs of the earlier steps:

1. Unify (existing)
2. Filter (existing)
3. Deduplicate → writes `unified_data.csv` (existing)
4. Build census GeoJSON → writes `gta_census_da.geojson` (existing — `build_gta_census_geojson`)
5. **NEW** — `enrich_census_with_crime_rate()` — depends on the unified crime CSV (Step 3) and the census GeoJSON (Step 4); overwrites `gta_census_da.geojson` with the two new properties
6. **NEW** — `build_shooting_arcs()` — depends on the unified crime CSV (Step 3); writes `shooting_arcs.csv`
7. **NEW** — `build_standalone_compact()` — depends on the outputs of Steps 3, 5, and 6; writes the three files under `data/02_transformed/standalone/`

Update the docstring at the top of `pipeline.py` to list the new outputs alongside `unified_data.csv` and `gta_census_da.geojson`. No changes to `pyproject.toml` scripts are required — `uv run transform` and `uv run full-pipeline` automatically pick up the new steps via the call to `run()`.

---

## Custom Radius Slider — `src/components/RadiusControl.tsx`

### Reading state — `src/hooks/useHexbinLayer.ts`

```ts
import { useSelector } from 'react-redux';
export function useHexbinLayer() {
  return useSelector((s: any) => {
    const layers = s.keplerGl?.map?.visState?.layers ?? [];
    return layers.find((l: any) => l.id === 'crime_hex');
  });
}
```

### Dispatching changes

Kepler actions need to be wrapped to forward to a specific map id. Use `wrapTo` from `@kepler.gl/actions`:

```ts
import { wrapTo, layerVisConfigChange } from '@kepler.gl/actions';
const forward = wrapTo('map'); // 'map' = the id passed to <KeplerGl id="map" />
dispatch(forward(layerVisConfigChange(layer, { worldUnitSize: kmValue })));
```

### Component sketch

```tsx
export function RadiusControl() {
  const dispatch = useDispatch();
  const layer = useHexbinLayer();
  if (!layer) return null;
  const value = layer.config.visConfig.worldUnitSize as number;
  const onChange = (e: ChangeEvent<HTMLInputElement>) => {
    const km = parseFloat(e.target.value);
    dispatch(wrapTo('map')(layerVisConfigChange(layer, { worldUnitSize: km })));
  };
  return (
    <div className="radius-control"> {/* abs positioned top:16, left:340, z-index:100 */}
      <label>Hexbin radius: {value.toFixed(2)} km</label>
      <input type="range" min={0.05} max={2.0} step={0.05} value={value} onChange={onChange} />
    </div>
  );
}
```

Mounted inside `MapShell.tsx` as a sibling to `<KeplerGl/>`, absolutely positioned over the map (top-left, beside but not blocking Kepler's left panel). Dark semi-transparent background to match the dark map style.

---

## Module Responsibilities

| File | Responsibility |
|---|---|
| `src/store.ts` | Configure Redux store with `keplerGlReducer.initialState({ uiState: { currentModal: null }})` + `taskMiddleware` from `react-palm/tasks` |
| `src/app.tsx` | `<Provider store={store}><MapShell/></Provider>` |
| `src/components/MapShell.tsx` | `useEffect` → `await loadAllDatasets()` → `buildLayers()` → dispatch `addDataToMap({ datasets, options: { centerMap: false }, config: { visState: { layers }, mapState: VIZ_CONFIG.mapState }})`. Render `<AutoSizer>` wrapping `<KeplerGl id="map" mapboxApiAccessToken={...}/>` plus `<RadiusControl/>`. |
| `src/data/loaders.ts` | Top-level `loadAllDatasets()` checks `window.__STANDALONE_MODE__`: if set, delegates to `standaloneLoader.ts`; else fetches from relative URLs. CSV/GeoJSON parsing via `processCsvData`/`processGeojson`. Returns `ProtoDataset[]`. Includes a dev-only validator that asserts each layer's `colorField.name` exists in its dataset's columns/properties — fails fast on typos. |
| `src/data/standaloneLoader.ts` | NEW. Reads `window.__STANDALONE_DATA__`, base64-decodes each blob, decompresses via the native `DecompressionStream('gzip')`, parses CSV/GeoJSON, returns `ProtoDataset[]`. Used only by the `dist/standalone.html` build. |
| `src/layers/index.ts` | `buildLayers()` filters config by `enabled`, dispatches by `kind` to a builder. |
| `src/layers/hexbinLayer.ts` | Maps the hexbin spec → Kepler `{ id, type: 'hexagon', config: { dataId, label, columns, isVisible: true, visConfig }, visualChannels: {...} }` |
| `src/layers/geojsonLayer.ts` | Same shape for `type: 'geojson'`, plus `colorField`/`colorScale` plumbing |
| `src/layers/arcLayer.ts` | Same shape for `type: 'arc'` with paired src/dst columns |

All layer builders are **pure functions** of the config — easy to unit test, no React, no Redux.

---

## Static Build Output

The build pipeline produces two flavours of output, both static-deployable, and the standalone flavour is the **only** one that has to survive `file://`:

1. **Multi-file static site** — `dist/index.html` + `dist/bundle.js` + `dist/data/`. Optimal for real hosting (GitHub Pages, S3, Netlify, plain `python -m http.server`). Browser cache, gzip, range requests, CDN — all work as expected. Loads data via relative `fetch()`.
2. **Single-file standalone HTML** — `dist/standalone.html` with the JS bundle **and** all three datasets embedded directly inside the file. Opens correctly via `file://` (double-click in a file manager, drag onto a browser tab, attach to an email). Zero sibling files required.

The same `esbuild.config.mjs` handles both via a `--mode` flag; a single `package.json` controls everything.

### Why `file://` makes this hard, and how we beat it

A naïve "inline everything" approach fails three different ways:
1. **Size** — 96 MB CSV + 37 MB GeoJSON would produce a >150 MB HTML file. Most browsers stall, and the file exceeds GitHub's 100 MB single-file limit.
2. **`fetch()` is blocked under `file://`** — browsers treat each `file://` document as having a `null` origin and refuse cross-origin reads of sibling files. So embedded data must be reachable **synchronously from the document itself**, not loaded via `fetch('data/...')`.
3. **Mapbox tile fetches** — Mapbox's tile API may reject requests from `null`-origin pages depending on token configuration. Using a Carto basemap (which Kepler ships with) sidesteps this entirely. The standalone build uses `mapStyle: 'dark'` from Kepler's built-in Carto styles instead of a Mapbox custom style.

The solution combines four moves:

| Move | What it does | Where it lives |
|---|---|---|
| **Compact pipeline outputs** | Slim columns, round coordinates, simplify polygons (≈80 % size reduction) | `transform/build_standalone_compact.py` (Step 7 of the pipeline — see §"Pipeline Transform Additions") |
| **gzip + base64 embed** | Compress each compact file, base64-encode, embed inside `<script type="application/octet-stream">` tags | `scripts/build-standalone.mjs` |
| **Native `DecompressionStream`** | Browser-native gzip decompression — no `pako` dependency, no extra bundle weight | `src/data/standaloneLoader.ts` (new file, ~50 lines) |
| **Carto basemap fallback** | Avoid Mapbox tile fetches under `file://` | Standalone build branch sets `mapStyle` to a Kepler-bundled Carto style |

After all four optimizations: roughly **6 MB gzipped crime data + 2 MB gzipped census data + ~5 MB minified JS bundle ≈ a ~17 MB `standalone.html`**. Slow to first paint (~3–5 s on a modern laptop while the browser parses the embedded base64 and runs decompression), but it works, and it works offline.

### `package.json` scripts

```jsonc
{
  "scripts": {
    "start":            "node esbuild.config.mjs --mode=dev",    // dev server :8080 with watch + livereload
    "build":            "node esbuild.config.mjs --mode=prod",   // → dist/index.html, dist/bundle.js, dist/data/
    "build:standalone": "yarn build && node scripts/build-standalone.mjs",  // ALSO emits dist/standalone.html
    "build:all":        "yarn build:standalone"                  // alias for the full production output
  }
}
```

### `esbuild.config.mjs` — production mode behaviour

When `--mode=prod`:

- `bundle: true`, `minify: true`, `sourcemap: false`, `format: 'iife'`, `target: 'es2020'`
- `splitting: false` — produce a **single** `bundle.js`. Code splitting would emit chunked files the standalone builder can't fold into one HTML and that complicate static deploys.
- `define: { 'process.env.MapboxAccessToken': JSON.stringify(process.env.MapboxAccessToken ?? '') }` — bake the token in at build time. Document that the build must be run in an environment that has the env var set.
- `outdir: 'dist'`, copy `public/index.html` → `dist/index.html` (rewriting any asset paths to relative)
- After esbuild finishes, copy `data/02_transformed/{unified_data.csv, gta_census_da.geojson, shooting_arcs.csv}` → `dist/data/` for the multi-file site.

### `scripts/build-standalone.mjs` — embed everything

A ~80-line Node script (no extra dependencies — uses `node:fs`, `node:zlib`, `node:path`):

1. Read the three compact files from `data/02_transformed/standalone/`
2. For each: `gzipSync(buf, { level: 9 })` → `Buffer.toString('base64')`
3. Read `dist/index.html` and `dist/bundle.js`
4. Build a `<script>` block that defines `window.__STANDALONE_DATA__ = { crime_points: '<base64>', census_da: '<base64>', shooting_arcs: '<base64>' };` and a sibling marker `window.__STANDALONE_MODE__ = true;`
5. Build a second `<script>` block containing the inlined `bundle.js` (escape any `</script>` sequences inside it just in case — minifiers occasionally produce them)
6. Concatenate into a new HTML doc: `<!doctype html><html>…<body><div id="root"></div><script>__STANDALONE_DATA__…</script><script>bundle…</script></body></html>`
7. Write `dist/standalone.html`
8. Leave `dist/index.html`, `dist/bundle.js`, and `dist/data/` untouched — the multi-file site is unaffected

Base64 strings only contain `[A-Za-z0-9+/=]`, so they cannot accidentally contain a `</script>` sequence; only the bundle itself needs the escape pass.

### `src/data/standaloneLoader.ts` — runtime decompression fork

A new module the viz uses **only** when `window.__STANDALONE_MODE__` is set. `loaders.ts` checks for this marker before doing anything network-related:

```ts
// loaders.ts (sketch)
export async function loadAllDatasets(): Promise<ProtoDataset[]> {
  if ((window as any).__STANDALONE_MODE__) {
    return loadFromEmbedded();           // standaloneLoader.ts
  }
  return loadFromFetch();                // existing fetch path
}
```

`standaloneLoader.ts` does roughly:

```ts
async function decodeAndGunzip(b64: string): Promise<string> {
  const bytes = Uint8Array.from(atob(b64), c => c.charCodeAt(0));
  const stream = new Blob([bytes]).stream().pipeThrough(new DecompressionStream('gzip'));
  return await new Response(stream).text();
}

export async function loadFromEmbedded(): Promise<ProtoDataset[]> {
  const embedded = (window as any).__STANDALONE_DATA__;
  const [crimeCsv, censusGeo, arcsCsv] = await Promise.all([
    decodeAndGunzip(embedded.crime_points),
    decodeAndGunzip(embedded.census_da),
    decodeAndGunzip(embedded.shooting_arcs),
  ]);
  return [
    { info: { id: 'crime_points',  label: 'Unified GTA Crime' },          data: processCsvData(crimeCsv) },
    { info: { id: 'census_da',     label: 'Census Dissemination Areas' }, data: processGeojson(JSON.parse(censusGeo)) },
    { info: { id: 'shooting_arcs', label: 'Shooting → Centroid Arcs' },   data: processCsvData(arcsCsv) },
  ];
}
```

`DecompressionStream` is a native web API in Chrome 80+, Edge 80+, Firefox 113+, and Safari 16.4+ — every supported target has it. No `pako`, no extra bundle weight.

`MapShell.tsx` should also branch on `__STANDALONE_MODE__` to swap to a Carto `mapStyle` so the standalone HTML doesn't try to hit Mapbox tile servers.

### Deploy targets — what works where

| Target | Multi-file `dist/` | `standalone.html` |
|---|---|---|
| GitHub Pages / Netlify / S3 | ✅ Best — gzip, CDN, caching | ✅ Works — one file upload |
| `python -m http.server 8000` | ✅ | ✅ |
| Double-click `standalone.html` (`file://`) | ❌ `fetch()` blocked | **✅ This is the whole point** |
| Email attachment, Drive, USB stick | ❌ | ✅ ~17 MB, opens anywhere |

### Mapbox token in static builds

- The dev workflow and the multi-file static build read `MapboxAccessToken` from `.env` (baked in via `define` at build time)
- The standalone build does **not** require a Mapbox token — it forces a Carto basemap so it works fully offline. If `MapboxAccessToken` is set when `yarn build:standalone` runs, it's still embedded for the multi-file site, but the standalone variant ignores it.
- If the deployed multi-file site is public, use a Mapbox token with a URL allowlist (set in the Mapbox account dashboard) to prevent token theft.

---

## Build, Run, and Verify

### Pipeline prerequisite (run from repo root)

```bash
cd /home/mcwoodle/workspace/crime-data
uv sync
uv run full-pipeline   # download + transform (incl. new enrichment + arc steps) + analyze
```

After this completes, `data/02_transformed/` contains every file the viz needs:
`unified_data.csv`, `gta_census_da.geojson` (now enriched with `crime_count` + `crime_rate_per_1k`), and `shooting_arcs.csv`.

### One-time viz setup (in WSL, from `/home/mcwoodle/workspace/crime-data/vizualize-kepler-map/`)

```bash
ln -s ../../data/02_transformed public/data       # symlink data into the dev server
yarn install                                       # install kepler + react + esbuild
cp .env.example .env                               # then set MapboxAccessToken=pk....
```

### Dev loop

```bash
cd vizualize-kepler-map
yarn start                                          # http://localhost:8080
```

### Production build (static site output)

```bash
cd vizualize-kepler-map
yarn build:standalone                               # → dist/index.html, dist/bundle.js, dist/data/, dist/standalone.html
```

Smoke-test the static output locally:

```bash
cd vizualize-kepler-map/dist
python -m http.server 8000                          # open http://localhost:8000/ and http://localhost:8000/standalone.html
```

To deploy: copy the entire `dist/` folder to any static host. No Node runtime, no build step on the server.

### Verification

1. **Bootstrap** — Browser shows dark Kepler.gl map centered on the GTA at zoom ~8.6, pitch ~35°. Toronto, York, Peel, Halton, Durham all visible without panning.
2. **Layer 1 (Hexbin)** — Visible by default. Hex cells render across the GTA with 3D extrusion. Toggling Kepler's left layer panel hides/shows it.
3. **Radius slider** — Custom control top-left of the map. Dragging it visibly grows/shrinks the hex cells in real time. Redux DevTools shows `LAYER_VIS_CONFIG_CHANGE` actions firing with `worldUnitSize` deltas.
4. **Layer 2 (Median income)** — Toggle on. Census DA polygons render at 40% opacity, colored by `Median_Income` (low income = pale, high income = dark blue). Click a polygon: tooltip shows `Median_Income`, `Population`, `DAUID`.
5. **Layer 3 (Crime rate per 1k)** — Toggle on. Same DA polygons but colored by `crime_rate_per_1k`. Should clearly highlight high-incident urban cores (downtown Toronto, central Mississauga, central Markham). Tooltip shows `crime_count`, `crime_rate_per_1k`, `Population`.
6. **Layer 4 (Arcs)** — Toggle on. 3D arcs render from each shooting location to its municipality centroid. Color varies by year. Tilt the map to see the height encoding.
7. **Config edit cycle** — Set `enabled: false` on any layer in `visualization.ts`, save → esbuild rebuilds → browser reloads → layer disappears. Change a `colorRange` array → reload → colors update. No React/store edits needed.
8. **Mapbox token absent** — With no `.env`, Kepler shows a no-token error overlay rather than a white screen (document this in `vizualize-kepler-map/README.md`).
9. **Performance check** — Initial load with 754K points should take <10s on a modern laptop. The hexbin GPU pipeline keeps interaction fluid. If the radius slider feels janky, debounce it 150ms inside `RadiusControl.tsx`.
10. **Static build — multi-file** — `yarn build` produces `dist/index.html`, `dist/bundle.js`, and a populated `dist/data/` directory. `cd dist && python -m http.server 8000` then opening `http://localhost:8000/` renders the same map as the dev server with no Node process running. Verify the Network tab shows data fetched from relative `data/...` URLs (no leading slash, no `localhost:8080`).
11. **Standalone HTML — `file://` open (THE critical test)** — `yarn build:standalone` produces `dist/standalone.html`. **Open the file directly via the browser's file picker or by double-clicking** (URL bar shows `file:///…/dist/standalone.html`). The map must render fully: hexbin, choropleths, arcs all load. The Network tab should show **zero** `data/...` requests — only Carto basemap tiles (which are CORS-OK from `null` origin). DevTools console should log a single "loaded from embedded data" message from `standaloneLoader.ts`.
12. **Standalone HTML — portability** — Copy `dist/standalone.html` to a totally unrelated directory (`/tmp/elsewhere/standalone.html`) with no sibling `data/` folder. Open it via `file://`. It must still render — proves the data is genuinely embedded, not fetched from a relative neighbour. Also email it to yourself, download from the email, and confirm it opens.
13. **Standalone HTML — size sanity** — `ls -lh dist/standalone.html` should report something in the 12–25 MB range. Significantly smaller than that means the data didn't embed; significantly larger means the compaction step didn't run. `grep -c '__STANDALONE_DATA__' dist/standalone.html` should return ≥1.
14. **Standalone HTML — DecompressionStream availability** — Open `standalone.html` in a target browser; in DevTools console, `typeof DecompressionStream` should be `'function'`. If not, the target is too old (pre-Chrome 80 / Firefox 113 / Safari 16.4) and the README should call this out.
15. **Path-prefix robustness (multi-file)** — Move `dist/` under a subdirectory (`mkdir -p /tmp/prefix-test/sub && cp -r dist /tmp/prefix-test/sub/viz && cd /tmp/prefix-test && python -m http.server 8000`) and load `http://localhost:8000/sub/viz/`. The map must still render — proves no absolute `/data/...` paths leaked into the build.
16. **Token bake-in (multi-file only)** — Run `yarn build` once with `MapboxAccessToken` set and once unset. The first produces a working multi-file bundle; the second produces one that triggers Kepler's no-token overlay at runtime. The standalone HTML is unaffected either way because it uses a Carto basemap.

---

## Critical Files (paths the implementer will spend the most time in)

**Pipeline (Python — owns all data transformation):**
- `/home/mcwoodle/workspace/crime-data/src/gta_urban_analytics/transform/pipeline.py` — wire the three new steps into `run()`
- `/home/mcwoodle/workspace/crime-data/src/gta_urban_analytics/transform/census/enrich_with_crime_rate.py` — DA crime-rate enrichment (NEW)
- `/home/mcwoodle/workspace/crime-data/src/gta_urban_analytics/transform/crime/build_shooting_arcs.py` — shooting-arc data prep (NEW)
- `/home/mcwoodle/workspace/crime-data/src/gta_urban_analytics/transform/build_standalone_compact.py` — slim variants for HTML embedding (NEW)

**Visualization (TypeScript — pure rendering, no transformation):**
- `/home/mcwoodle/workspace/crime-data/vizualize-kepler-map/src/config/visualization.ts` — central knobs
- `/home/mcwoodle/workspace/crime-data/vizualize-kepler-map/src/components/MapShell.tsx` — load + dispatch wiring
- `/home/mcwoodle/workspace/crime-data/vizualize-kepler-map/src/components/RadiusControl.tsx` — custom slider
- `/home/mcwoodle/workspace/crime-data/vizualize-kepler-map/src/layers/hexbinLayer.ts` — Layer 1 builder
- `/home/mcwoodle/workspace/crime-data/vizualize-kepler-map/src/layers/geojsonLayer.ts` — Layers 2 & 3 builder
- `/home/mcwoodle/workspace/crime-data/vizualize-kepler-map/src/data/standaloneLoader.ts` — embedded-data bootstrap with native gzip decompression (NEW)
- `/home/mcwoodle/workspace/crime-data/vizualize-kepler-map/esbuild.config.mjs` — dev/prod dual-mode bundler (no code splitting in prod)
- `/home/mcwoodle/workspace/crime-data/vizualize-kepler-map/scripts/build-standalone.mjs` — gzips compact data, embeds in HTML, inlines bundle, emits `dist/standalone.html`

## Existing Code to Reuse

- **Kepler reference scaffold**: `/home/mcwoodle/workspace/kepler.gl/examples/get-started/{package.json, esbuild.config.mjs, tsconfig.json, .yarnrc.yml, src/index.html}` — copy as-is, then modify entry point and env defines
- **Pipeline deps**: Already in repo `pyproject.toml` — the new transform modules inherit `pandas`, `geopandas`, `pyproj` and need no additions
- **Census GeoJSON builder**: `src/gta_urban_analytics/transform/census/build_gta_census.py` — model the new `enrich_with_crime_rate.py` after it (same `_project_root` resolution, same `to_file(..., driver='GeoJSON')` write pattern)
- **Population dict**: `src/gta_urban_analytics/analyze/analyze.py` — for sanity-checking centroid computations against known values

## Implementation Order

The pipeline work lands first so the viz never has a reason to grow its own scripts directory.

1. **Pipeline Step 5**: Add `transform/census/enrich_with_crime_rate.py`, call it from `pipeline.py`, run `uv run transform`, and confirm `gta_census_da.geojson` now has `crime_count` and `crime_rate_per_1k` per feature (spot-check a downtown Toronto DA in QGIS or a Python REPL).
2. **Pipeline Step 6**: Add `transform/crime/build_shooting_arcs.py`, call it from `pipeline.py`, run `uv run transform`, and confirm `data/02_transformed/shooting_arcs.csv` exists with the expected schema and a sane row count.
3. **Pipeline Step 7**: Add `transform/build_standalone_compact.py`, call it from `pipeline.py`, run `uv run transform`, and confirm `data/02_transformed/standalone/` contains the three compact files. Sanity-check sizes (compact CSV roughly 25 % of full CSV; simplified GeoJSON roughly 30 % of original).
4. Scaffold `vizualize-kepler-map/` from kepler get-started, get a blank map at `localhost:8080`.
5. Symlink `public/data` → `../../data/02_transformed`. Add `loaders.ts` + minimal `visualization.ts` with just Layer 1 + the `mapState`. Verify hexbin renders.
6. Build `RadiusControl.tsx` + `useHexbinLayer.ts`. Verify slider mutates `worldUnitSize`.
7. Add Layer 2 (income choropleth from `census_da`). Verify.
8. Add Layer 3 (crime-rate-per-1k choropleth from the **same** `census_da` dataset, different `colorField`). Verify per-1k coloring highlights downtown cores.
9. Add Layer 4 (arcs from `shooting_arcs.csv`). Verify arcs render with year coloring.
10. **Production build (multi-file)**: extend `esbuild.config.mjs` with a `--mode=prod` branch that emits a single non-split bundle to `dist/`, copies `public/index.html`, and copies the full data files into `dist/data/`. Run `yarn build`, then `cd dist && python -m http.server 8000` and verify the static site renders identically to the dev server. Confirm verification steps 10, 15, and 16 pass.
11. **Standalone HTML build**: add `src/data/standaloneLoader.ts` and the `__STANDALONE_MODE__` branch in `loaders.ts`. Add the Carto basemap branch in `MapShell.tsx`. Add `scripts/build-standalone.mjs` that gzips the three files in `data/02_transformed/standalone/`, base64-encodes them, builds the `<script>window.__STANDALONE_DATA__ = {…}</script>` block, inlines the JS bundle, and writes `dist/standalone.html`. Wire up the `build:standalone` script. Run `yarn build:standalone`. **Open `dist/standalone.html` via `file://` directly (not through a server)** and confirm verification steps 11–14 all pass.
12. Polish: `vizualize-kepler-map/README.md` documents that `uv run full-pipeline` is the only data prereq, the dev/prod/standalone build commands, the browser version requirements for `DecompressionStream`, and the Mapbox-token-at-build-time requirement (multi-file only). Add `.env.example` and ensure `.gitignore` covers `dist/`, `node_modules/`, `.env`, and `public/data`.

Each step leaves a runnable app — every commit is testable.
