// ========================================================================
// Central Visualization Config
// ========================================================================
// This is the ONLY file to touch for adding/removing datasets, swapping
// layer types, changing colors, opacities, sizes, or tuning the initial
// viewport. A discriminated union on `kind` (see types.ts) dispatches to
// the right layer builder in src/layers/index.ts.
// ========================================================================

import type { VisualizationConfig, ColorRangeSpec } from '../data/types';

// --- Reusable color ramps -------------------------------------------------

const GLOBAL_WARMING: ColorRangeSpec = {
  name: 'Global Warming',
  type: 'sequential',
  category: 'Uber',
  colors: ['#5A1846', '#900C3F', '#C70039', '#E3611C', '#F1920E', '#FFC300']
};

const YL_GN_BU: ColorRangeSpec = {
  name: 'ColorBrewer YlGnBu-6',
  type: 'sequential',
  category: 'ColorBrewer',
  colors: ['#ffffcc', '#c7e9b4', '#7fcdbb', '#41b6c4', '#2c7fb8', '#253494']
};

const TEAL_TO_NAVY: ColorRangeSpec = {
  name: 'Teal to Navy',
  type: 'sequential',
  category: 'Custom',
  colors: ['#e0f7fa', '#80deea', '#26c6da', '#00acc1', '#00838f', '#006064']
};

const VIRIDIS: ColorRangeSpec = {
  name: 'Viridis',
  type: 'sequential',
  category: 'Uber',
  colors: ['#440154', '#443983', '#31688e', '#21918c', '#35b779', '#90d743', '#fde725']
};

// --- The config -----------------------------------------------------------

export const VIZ_CONFIG: VisualizationConfig = {
  datasets: [
    {
      id: 'crime_points',
      label: 'Unified GTA Crime',
      // RELATIVE URL (no leading slash) so the static build deploys cleanly
      // under any path prefix and standalone.html works from a sibling dir.
      url: 'data/2025/unified_data.csv',
      visible: true
    },
    {
      id: 'census_da',
      label: 'Census Dissemination Areas',
      // Layers 2 and 3 both consume this single file — Median_Income and
      // crime_rate_per_1k are both properties on the same GeoJSON.
      url: 'data/2025/gta_census_da.geojson',
      visible: true
    },
    {
      id: 'shooting_arcs',
      label: 'Shooting → Centroid Arcs',
      url: 'data/2025/shooting_arcs.csv',
      visible: true
    }
  ],

  layers: [
    // -------------------------------------------------------------------
    // Layer 1 — Unified Crime Hexbin
    // -------------------------------------------------------------------
    {
      kind: 'hexbin',
      id: 'crime_hex',
      label: 'Crime Hexbin',
      dataId: 'crime_points',
      isVisible: true,
      columns: { lat: 'lat', lng: 'lon' },
      visConfig: {
        worldUnitSize: 0.2, // km, per spec; adjustable via the radius slider
        elevationScale: 50,
        enable3d: true,
        coverage: 0.95,
        opacity: 0.85,
        colorRange: GLOBAL_WARMING
      }
    },

    // -------------------------------------------------------------------
    // Layer 2 — Median Income Choropleth
    // -------------------------------------------------------------------
    {
      kind: 'geojson',
      id: 'income_choropleth',
      label: 'Median Income by DA',
      dataId: 'census_da',
      isVisible: false, // start hidden; user can toggle on
      visConfig: {
        opacity: 0.4,
        filled: true,
        stroked: false,
        colorRange: YL_GN_BU
      },
      colorField: { name: 'Median_Income', type: 'real' },
      colorScale: 'quantile' // incomes are heavily right-skewed
    },

    // -------------------------------------------------------------------
    // Layer 3 — Crime Rate per 1,000 People (same dataset as Layer 2)
    // -------------------------------------------------------------------
    {
      kind: 'geojson',
      id: 'crime_rate_choropleth',
      label: 'Crime Rate per 1,000 by DA',
      dataId: 'census_da',
      isVisible: false,
      visConfig: {
        opacity: 0.55,
        filled: true,
        stroked: true,
        strokeColor: [255, 255, 255],
        strokeOpacity: 0.6,
        colorRange: TEAL_TO_NAVY
      },
      colorField: { name: 'crime_rate_per_1k', type: 'real' },
      colorScale: 'quantize'
    },

    // -------------------------------------------------------------------
    // Layer 4 — Shootings → Municipality Centroid Arcs
    // -------------------------------------------------------------------
    {
      kind: 'arc',
      id: 'shooting_arcs',
      label: 'Shootings → Municipality Centroids',
      dataId: 'shooting_arcs',
      isVisible: false,
      columns: { lat0: 'src_lat', lng0: 'src_lon', lat1: 'dst_lat', lng1: 'dst_lon' },
      visConfig: {
        opacity: 0.85,
        thickness: 2,
        targetColor: [255, 80, 80],
        colorRange: VIRIDIS
      },
      colorField: { name: 'year', type: 'integer' },
      sizeField: { name: 'count_in_muni', type: 'integer' }
    }
  ],

  // GTA-fitting viewport: covers Toronto + Halton + Peel + York + Durham.
  mapState: {
    longitude: -79.4,
    latitude: 43.85,
    zoom: 8.6,
    pitch: 35,
    bearing: 0
  },

  mapStyle: 'dark'
};

/**
 * Standalone-mode map style override.
 *
 * Mapbox tile fetches can be rejected from `null`-origin pages (`file://`).
 * Kepler's built-in 'dark' style ships a Carto dark-matter variant that
 * works from any origin — use it when running standalone.
 */
export const STANDALONE_MAP_STYLE: VisualizationConfig['mapStyle'] = 'dark';
