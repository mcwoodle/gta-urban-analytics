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

// Sequential heat ramp for the fire layers (incident density, station volume,
// per-capita fire rate). Distinct yellow→deep-orange so fire reads apart from the
// crime layers' magenta→amber "Global Warming" ramp.
const FIRE_HEAT: ColorRangeSpec = {
  name: 'Fire Heat',
  type: 'sequential',
  category: 'Custom',
  colors: ['#ffffb2', '#fed976', '#feb24c', '#fd8d3c', '#fc4e2a', '#e31a1c', '#b10026']
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

// 3×3 bivariate palette for the income × crime-rate layer. The pipeline pre-bins
// each DA into class A..I = income tercile (outer, Lower→Higher) × crime-rate
// tercile (inner, Lower→Higher); Kepler's ordinal scale sorts A..I and maps these
// nine colours index-for-index. Joshua Stevens' two-hue scheme reads as:
//   • light grey  (A) = lower income · lower crime   — unremarkable
//   • strong red  (C) = lower income · HIGHER crime  — disadvantaged & high-crime
//   • teal/blue   (G) = higher income · lower crime  — affluent & safe
//   • dark slate  (I) = higher income · higher crime — affluent but high-crime
// Keep this array in exact A→I order; it is the legend's source of truth too.
export const BIVARIATE_INCOME_CRIME: ColorRangeSpec = {
  name: 'Income × Crime (bivariate 3×3)',
  type: 'qualitative',
  category: 'Custom',
  colors: [
    '#e8e8e8', '#e4acac', '#c85a5a', // A B C — lower income  · lower/mid/higher crime
    '#b0d5df', '#ad9ea5', '#985356', // D E F — mid income    · lower/mid/higher crime
    '#64acbe', '#627f8c', '#574249'  // G H I — higher income · lower/mid/higher crime
  ]
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
    },
    // Fire datasets (Toronto Fire Services). Top-level products (not
    // year-partitioned, like coordinate_anomalies) — URLs have no year segment,
    // so the year selector leaves them unchanged.
    {
      id: 'fire_incidents',
      label: 'Toronto Fire Incidents',
      url: '../../data/02_transformed/fire_incidents.csv',
      visible: true
    },
    {
      id: 'fire_stations',
      label: 'Fire Stations (fires handled)',
      url: '../../data/02_transformed/fire_stations.geojson',
      visible: true
    },
    {
      id: 'fire_da',
      label: 'Fire Rate by DA',
      url: '../../data/02_transformed/fire_da.geojson',
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
      // Hidden by default so first paint leads with the bivariate income×crime
      // choropleth (the headline relationship). One toggle in Kepler's panel
      // brings the 3D density hexbin back.
      isVisible: false,
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
    // Flags coordinates carrying an implausible number of incidents (> 500) at
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
        radiusRange: [10, 150],
        fixedRadius: false,
        outline: true,
        thickness: 1.5
      },
      colorField: { name: 'anomaly_type', type: 'string' },
      colorScale: 'ordinal',
      sizeField: { name: 'incident_count', type: 'integer' },
      sizeScale: 'sqrt'
    },

    // -------------------------------------------------------------------
    // Layer 6 — Income × Crime-Rate Bivariate Choropleth  (★ headline)
    // -------------------------------------------------------------------
    // Answers "how does crime rate vary with income?" in ONE view. Each DA is
    // pre-binned by the pipeline into class A..I (income tercile × crime-rate
    // tercile) and coloured from BIVARIATE_INCOME_CRIME. Visible by default;
    // appended last so it renders BELOW the anomaly dots (Kepler draws the first
    // array entry on top). See BivariateLegend.tsx for the 3×3 key.
    {
      kind: 'geojson',
      id: 'income_crime_bivariate',
      label: 'Income × Crime Rate (bivariate)',
      dataId: 'census_da',
      isVisible: true,
      visConfig: {
        opacity: 0.8,
        filled: true,
        stroked: true,
        strokeColor: [25, 25, 25],
        strokeOpacity: 0.2,
        colorRange: BIVARIATE_INCOME_CRIME
      },
      colorField: { name: 'bivariate_class', type: 'string' },
      colorScale: 'ordinal'
    },

    // -------------------------------------------------------------------
    // Layer 7 — Crime Rate (colour) × Population (3D height)
    // -------------------------------------------------------------------
    // The other half of the question: crime rate *with respect to population*.
    // Colour = per-capita crime rate (warm = high); bar height = residents, so a
    // tall warm bar = many people AND high per-capita crime, while a tall cool
    // bar = a dense-but-safe neighbourhood. Hidden by default (3D; toggle on).
    {
      kind: 'geojson',
      id: 'crime_rate_by_population_3d',
      label: 'Crime Rate × Population (3D)',
      dataId: 'census_da',
      isVisible: false,
      visConfig: {
        opacity: 0.85,
        filled: true,
        stroked: false,
        colorRange: GLOBAL_WARMING,
        enable3d: true,
        elevationScale: 6,
        heightRange: [0, 1200]
      },
      colorField: { name: 'crime_rate_per_1k', type: 'real' },
      colorScale: 'quantile',
      heightField: { name: 'Population', type: 'integer' },
      heightScale: 'sqrt'
    },

    // -------------------------------------------------------------------
    // Layer 8 — Toronto Fire Incident Hexbin
    // -------------------------------------------------------------------
    // Density of fire incidents (parallel to the crime hexbin). Hidden by
    // default; toggle on to see where fires concentrate.
    {
      kind: 'hexbin',
      id: 'fire_hex',
      label: 'Fire Incident Hexbin',
      dataId: 'fire_incidents',
      isVisible: false,
      columns: { lat: 'lat', lng: 'lon' },
      visConfig: {
        worldUnitSize: 0.3,
        elevationScale: 40,
        enable3d: true,
        coverage: 0.95,
        opacity: 0.85,
        colorRange: FIRE_HEAT
      }
    },

    // -------------------------------------------------------------------
    // Layer 9 — Fire Stations sized by "fires handled"  (★ headline fire view)
    // -------------------------------------------------------------------
    // One dot per Toronto fire station, sized + coloured by how many incidents
    // it responded to (incidents grouped on Incident_Station_Area). Directly
    // answers "how many fires did each station handle?". Hover shows the count
    // and total dollar loss.
    {
      kind: 'point',
      id: 'fire_stations',
      label: 'Fire Stations (fires handled)',
      dataId: 'fire_stations',
      isVisible: false,
      columns: { lat: 'lat', lng: 'lon' },
      visConfig: {
        radius: 20,
        opacity: 0.85,
        filled: true,
        colorRange: FIRE_HEAT,
        radiusRange: [8, 120],
        fixedRadius: false,
        outline: true,
        thickness: 1.5
      },
      colorField: { name: 'fires_handled', type: 'integer' },
      colorScale: 'quantize',
      sizeField: { name: 'fires_handled', type: 'integer' },
      sizeScale: 'sqrt'
    },

    // -------------------------------------------------------------------
    // Layer 10 — Fire Rate per 1,000 by DA
    // -------------------------------------------------------------------
    // Per-capita fire-incident rate per Dissemination Area (the fire analogue
    // of the crime-rate choropleth). Hidden by default.
    {
      kind: 'geojson',
      id: 'fire_rate_choropleth',
      label: 'Fire Rate per 1,000 by DA',
      dataId: 'fire_da',
      isVisible: false,
      visConfig: {
        opacity: 0.6,
        filled: true,
        stroked: true,
        strokeColor: [255, 255, 255],
        strokeOpacity: 0.4,
        colorRange: FIRE_HEAT
      },
      colorField: { name: 'fire_rate_per_1k', type: 'real' },
      colorScale: 'quantize'
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
    ],
    // Census DAs back the income, crime-rate, bivariate, and 3D layers. Lead
    // with the plain-English bivariate label, then the raw values behind it.
    census_da: [
      'bivariate_label',
      'Median_Income',
      'crime_rate_per_1k',
      'crime_count',
      'Population',
      'DAUID'
    ],
    // Fire layers. Station tooltip leads with the headline "fires handled".
    fire_stations: [
      'station',
      'municipality',
      'address',
      'fires_handled',
      'total_dollar_loss'
    ],
    // The standalone build embeds a slim fire-incident CSV (lat/lon + these two).
    fire_incidents: ['incident_type', 'occurrence_date'],
    fire_da: ['fire_rate_per_1k', 'fire_count', 'Population', 'DAUID']
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
