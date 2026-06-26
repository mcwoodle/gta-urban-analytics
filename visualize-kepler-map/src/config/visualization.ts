// ========================================================================
// Central Visualization Config
// ========================================================================
// This is the ONLY file to touch for adding/removing datasets, swapping
// layer types, changing colors, opacities, sizes, or tuning the initial
// viewport. A discriminated union on `kind` (see types.ts) dispatches to
// the right layer builder in src/layers/index.ts.
// ========================================================================

import type { VisualizationConfig, ColorRangeSpec, LayerSpec } from '../data/types';

// --- Profile detection -------------------------------------------------------

export type VizProfile = 'full' | 'lite';

/** Read the build-time profile flag injected by build-standalone.mjs.
 *  Defaults to 'full' when not set. */
export function getProfile(): VizProfile {
  if (typeof window !== 'undefined' && (window as any).__VIZ_PROFILE__ === 'lite') {
    return 'lite';
  }
  return 'full';
}

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

// Qualitative ramp for the coordinate-anomaly overlay. Colours by anomaly_type
// (an ordinal field), so the two classes read distinctly. Domain is sorted
// alphabetically by Kepler's ordinal scale: index 0 = 'high_traffic_area'
// (amber — an organic hotspot near a mall/hospital), index 1 = 'unexplained'
// (magenta — a likely placeholder/geocoding artifact).
const ANOMALY_CLASS: ColorRangeSpec = {
  name: 'Anomaly Class',
  type: 'qualitative',
  category: 'Custom',
  colors: ['#FFB000', '#E5007A']
};

// --- The config -----------------------------------------------------------

export const VIZ_CONFIG: VisualizationConfig = {
  datasets: [
    {
      id: 'crime_points',
      label: 'Unified GTA Crime',
      url: '../../data/02_transformed/2025/unified_data.csv',
      visible: true
    },
    {
      id: 'census_da',
      label: 'Census Dissemination Areas',
      // Layers 2 and 3 both consume this single file — Median_Income and
      // crime_rate_per_1k are both properties on the same GeoJSON.
      url: '../../data/02_transformed/2025/gta_census_da.geojson',
      visible: true
    },
    {
      id: 'shooting_arcs',
      label: 'Shooting → Centroid Arcs',
      url: '../../data/02_transformed/2025/shooting_arcs.csv',
      visible: true
    },
    {
      id: 'coordinate_anomalies',
      label: 'Coordinate Anomalies (placeholder/snapped)',
      // All-time, top-level product (not year-partitioned) — a placeholder
      // coordinate is an artifact regardless of the selected year, so this URL
      // has no year segment and stays constant across year changes.
      url: '../../data/02_transformed/coordinate_anomalies.csv',
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
    },

    // -------------------------------------------------------------------
    // Layer 5 — Coordinate Anomalies (placeholder / snapped points)
    // -------------------------------------------------------------------
    // Flags coordinates carrying an implausible number of incidents (> 200) at
    // one exact lat/lon (source-side address/centroid snapping — audit F-19).
    // Sized by incident_count; COLOURED by anomaly_type so the two classes
    // separate: amber = near a known high-traffic venue (mall/hospital — partly
    // organic), magenta = unexplained (likely a pure geocoding artifact).
    // The incidents are real and counted everywhere; this overlay just marks the
    // artifacts so they aren't mistaken for organic hotspots. Hovering a dot
    // shows its classification (see `tooltips.coordinate_anomalies` below).
    {
      kind: 'point',
      id: 'coordinate_anomalies',
      label: 'Coordinate Anomalies (placeholder/snapped)',
      dataId: 'coordinate_anomalies',
      isVisible: true,
      columns: { lat: 'lat', lng: 'lon' },
      visConfig: {
        radius: 20,
        opacity: 0.6,
        filled: true,
        colorRange: ANOMALY_CLASS,
        radiusRange: [6, 36],
        fixedRadius: false,
        outline: true,
        thickness: 1.5
      },
      colorField: { name: 'anomaly_type', type: 'string' },
      colorScale: 'ordinal',
      sizeField: { name: 'incident_count', type: 'integer' },
      sizeScale: 'sqrt'
    }
  ],

  // Hover-tooltip fields per dataset. Without this, Kepler shows only a
  // dataset's first 5 columns — which for the anomaly layer omits the
  // classification entirely. Lead with `description` (a plain-English summary)
  // so hovering any anomaly dot explains how it was classified and why.
  tooltips: {
    coordinate_anomalies: [
      'description',
      'anomaly_type',
      'nearest_location',
      'location_category',
      'incident_count',
      'top_category',
      'regions'
    ]
  },

  // GTA-fitting viewport: covers Toronto + Halton + Peel + York + Durham.
  mapState: {
    longitude: -79.4,
    latitude: 43.85,
    zoom: 8.6,
    pitch: 45,
    bearing: 0,
    dragRotate: true
  },

  mapStyle: 'voyager'
};

/**
 * Standalone-mode map style override.
 *
 * Mapbox tile fetches can be rejected from `null`-origin pages (`file://`).
 * Kepler's built-in 'dark' style ships a Carto dark-matter variant that
 * works from any origin — use it when running standalone.
 */
export const STANDALONE_MAP_STYLE: VisualizationConfig['mapStyle'] = 'voyager';

// --- Lite profile config -----------------------------------------------------
// Replaces the GPU-aggregated hexagon layer with a flat 2D heatmap (deck.gl
// HeatmapLayer). The build script bins the full ~808k crime points into H3
// res-8 cells at build time, computes each cell's centroid lat/lon, and emits
// a compact { lat, lon, count } dataset (~4k rows). The heatmap layer uses
// count as a weight field to approximate the true density distribution.
// This avoids the 3D column-extrusion GLSL shader entirely — mobile-safe.

const LITE_CRIME_LAYER: LayerSpec = {
  kind: 'heatmap',
  id: 'crime_heatmap_lite',
  label: 'Crime Density Heatmap',
  dataId: 'crime_heatmap_lite',
  isVisible: true,
  columns: { lat: 'lat', lng: 'lon' },
  visConfig: {
    opacity: 0.8,
    radius: 20,
    colorRange: GLOBAL_WARMING
  },
  weightField: { name: 'count', type: 'integer' }
};

/**
 * Return the visualization config adjusted for the active profile.
 *
 * - `full` (default): the original VIZ_CONFIG unchanged.
 * - `lite`: flat 2D viewport, crime point layer only (no hexbin GPU
 *   aggregation, no census choropleths, no arc layer).
 */
export function getVizConfig(): VisualizationConfig {
  if (getProfile() === 'lite') {
    return {
      datasets: [
        {
          id: 'crime_heatmap_lite',
          label: 'Crime Density Heatmap',
          url: '', // embedded at build time, not fetched
          visible: true
        }
      ],
      layers: [LITE_CRIME_LAYER],
      mapState: {
        ...VIZ_CONFIG.mapState,
        pitch: 0,
        dragRotate: false
      },
      mapStyle: VIZ_CONFIG.mapStyle
    };
  }
  return VIZ_CONFIG;
}
