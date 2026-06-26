# GTA Urban Analytics — Kepler.gl Visualization

A five-layer Kepler.gl map of GTA crime + census data, driven from a single
typed config file (`src/config/visualization.ts`) so layer choice and styling
can be tweaked without touching React code.

The five layers: (1) crime hexbin, (2) median-income choropleth, (3) crime-rate
choropleth, (4) shooting → centroid arcs, and (5) a coordinate-anomaly overlay
that marks placeholder/snapped points (> 200 incidents at one exact lat/lon) —
coloured by class so anomalies near a known high-traffic venue (mall/hospital)
read apart from unexplained ones (audit F-19). Hovering an anomaly dot shows a
plain-English `description` of its classification (plus `anomaly_type`,
`nearest_location`, and `incident_count`), configured via `tooltips` in
`src/config/visualization.ts`.

## Data prerequisite

All data is produced by the Python pipeline in the repo root. The viz package
itself performs **zero** data transformation.

```bash
cd ..                   # repo root
uv sync
uv run full-pipeline    # or: uv run transform
```

After this completes, `data/02_transformed/` contains every file the viz
needs, including the enriched census GeoJSON (with `crime_count` and
`crime_rate_per_1k`), `shooting_arcs.csv`, and the compact variants under
`standalone/` that the single-file HTML build embeds.

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

The produced `dist/standalone.html` contains the JS bundle **and** all four
datasets (gzip-compressed, base64-encoded) embedded inline. Open it directly
from a file browser or drag it onto a browser tab — no server required.

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
│   ├── geojsonLayer.ts       # Layers 2 + 3
│   ├── arcLayer.ts           # Layer 4
│   └── pointLayer.ts         # Layer 5 (coordinate anomalies)
├── components/
│   ├── MapShell.tsx          # load + dispatch wiring
│   └── RadiusControl.tsx     # custom debounced slider
├── hooks/useHexbinLayer.ts
├── store.ts                  # Redux + taskMiddleware
└── app.tsx                   # ReactDOM mount
```

## Editing layers

Open `src/config/visualization.ts`. Everything — dataset URLs, layer types,
colors, opacities, sizes, initial viewport — is one edit away. Changes
trigger an esbuild rebuild in dev mode.
