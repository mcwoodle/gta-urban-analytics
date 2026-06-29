# GTA Urban Analytics — Kepler.gl Visualization

A ten-layer Kepler.gl map of GTA crime + census + fire data, driven from a single
typed config file (`src/config/visualization.ts`) so layer choice and styling
can be tweaked without touching React code.

The crime/census layers: (1) crime hexbin, (2) median-income choropleth,
(3) crime-rate choropleth, (4) shooting → centroid arcs, (5) a coordinate-anomaly
overlay that marks placeholder/snapped points (> 500 incidents at one exact
lat/lon) — coloured by class so anomalies near a known high-traffic venue
(mall/hospital) read apart from unexplained ones (audit F-19), **(6) an income ×
crime-rate bivariate choropleth**, and **(7) a 3D crime-rate-by-population
extrusion**.

The fire layers (Toronto Fire Services, all hidden by default — toggle on):
**(8) a fire-incident hexbin** (density of fires), **(9) fire stations sized +
coloured by "fires handled"** (incidents grouped on the responding
`Incident_Station_Area`; hover shows the count + total dollar loss — the headline
fire view), and **(10) a per-DA fire-rate-per-1,000 choropleth**. All fire data
is produced by the Python `transform/fire/` pipeline; the viz only renders it.

**Layers 6 and 7 show how crime rate relates to census data.** Layer 6 is the
default view: each Dissemination Area is coloured from a 3×3 bivariate palette
(income tercile × crime-rate tercile), so the relationship between income and
crime reads directly off the map — strong red marks lower-income/higher-crime
areas, blue marks affluent/safer ones. A 3×3 key (`BivariateLegend.tsx`) appears
bottom-right while the layer is on. Layer 7 (toggle on) colours each DA by
per-capita crime rate and extrudes it in 3D by population, so a tall warm bar =
many residents *and* high per-capita crime. Both read from the pipeline-computed
`bivariate_class` / `bivariate_label` and `crime_rate_per_1k` / `Population`
properties — the viz does no binning of its own. Hovering any DA shows its
`bivariate_label` plus the underlying income, rate, count, and population.

The 3D density hexbin (Layer 1) starts hidden so first paint leads with the
bivariate relationship; one toggle in Kepler's panel brings it back. Hovering an
anomaly dot shows a plain-English `description` of its classification; all hover
fields are configured via `tooltips` in `src/config/visualization.ts`.

## Data prerequisite

All data is produced by the Python pipeline in the repo root. The viz package
itself performs **zero** data transformation.

```bash
cd ..                   # repo root
uv sync
uv run full-pipeline    # or: uv run transform
```

After this completes, `data/02_transformed/` contains every file the viz
needs, including the enriched census GeoJSON (with `crime_count`,
`crime_rate_per_1k`, and the bivariate `bivariate_class` / `bivariate_label`),
`shooting_arcs.csv`, and the compact variants under `standalone/` that the
single-file HTML build embeds.

## Setup

```bash
cd visualize-kepler-map
# Symlink should already exist; create if not.
[ -L public/data ] || ln -s ../../data/02_transformed public/data
yarn install
cp .env.example .env     # then set MapboxAccessToken=pk.... (for dev + multi-file build)
```

## Running

### Dev server

```bash
yarn start               # http://localhost:8080
```

Hot reload via esbuild's watch mode. Reads data directly from
`public/data -> ../../data/02_transformed`.

### Production build — multi-file static site

```bash
yarn build               # → dist/index.html + dist/bundle.js + dist/data/
cd dist && python -m http.server 8000
# open http://localhost:8000/
```

Deployable to GitHub Pages, S3, Netlify, or any other static host. All URLs
are relative, so the site works under any path prefix.

### Production build — single-file standalone HTML (works via `file://`)

```bash
yarn build:standalone    # → dist/standalone.html (plus the multi-file site)
```

The produced `dist/standalone.html` contains the JS bundle **and** every
dataset (crime, census, arcs, anomalies, and the three fire products —
gzip-compressed, base64-encoded) embedded inline. Open it directly from a file
browser or drag it onto a browser tab — no server required.

The standalone build uses a Carto dark-matter basemap so it does not depend
on Mapbox tile servers (which can reject requests from `null`-origin
`file://` pages). Mapbox token is not required for this variant.

**Browser support** for standalone HTML: Chrome 80+, Firefox 113+, Safari
16.4+, Edge 80+ (requires the native `DecompressionStream` API).

## Architecture

```
src/
├── config/visualization.ts   # ★ SINGLE source of truth for datasets/layers
├── data/
│   ├── types.ts              # discriminated union of layer specs
│   ├── loaders.ts            # fetch-based loader; forks to standalone
│   └── standaloneLoader.ts   # base64 + gzip decoder for embedded data
├── layers/
│   ├── index.ts              # buildLayers() dispatcher
│   ├── hexbinLayer.ts        # Layer 1
│   ├── geojsonLayer.ts       # Layers 2, 3, 6 (flat) + 7 (3D extrusion) + 10 (fire rate)
│   ├── arcLayer.ts           # Layer 4
│   ├── hexbinLayer.ts        # Layers 1 + 8 (fire)
│   └── pointLayer.ts         # Layer 5 (anomalies) + 9 (fire stations)
├── components/
│   ├── MapShell.tsx          # load + dispatch wiring
│   ├── RadiusControl.tsx     # custom debounced slider
│   ├── YearControl.tsx       # data-year selector
│   └── BivariateLegend.tsx   # 3×3 income × crime-rate key (Layer 6)
├── hooks/useHexbinLayer.ts
├── store.ts                  # Redux + taskMiddleware
└── app.tsx                   # ReactDOM mount
```

## Editing layers

Open `src/config/visualization.ts`. Everything — dataset URLs, layer types,
colors, opacities, sizes, initial viewport — is one edit away. Changes
trigger an esbuild rebuild in dev mode.
