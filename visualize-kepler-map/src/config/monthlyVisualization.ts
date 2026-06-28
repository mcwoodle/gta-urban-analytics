// ========================================================================
// Monthly map configuration
// ========================================================================
// Drives the standalone-monthly Kepler map (dist/standalone-monthly.html and the
// dev `index-monthly.html` entry). One dataset — the per-month municipality
// GeoJSON built by transform/census/build_municipality_monthly.py — and one 3D
// geojson layer whose colour + height encode a single `display_value` field that
// MonthlyControl recomputes client-side for the chosen month / mode / metric.
//
// Two modes share the one layer, differing only in colour ramp + scale:
//   • single — a month's crime (absolute or per-1k). Sequential warm ramp,
//     values ≥ 0, so 0 ⇒ a flat bar and the busiest municipality is tallest.
//   • yoy    — a 2026 month minus its 2025 twin (Δ, absolute or per-1k).
//     Diverging ramp; Kepler's linear height maps the [min,max] Δ domain onto
//     [0, H], so the largest decrease is flat and the largest increase tallest.
// ========================================================================

import type { ColorRangeSpec, GeoJsonLayerSpec, MapStateSpec } from '../data/types';

export type MonthlyMode = 'single' | 'yoy';
export type MonthlyMetric = 'absolute' | 'per1k';

export const MONTHLY_DATASET_ID = 'municipalities_monthly';
export const MONTHLY_LAYER_ID = 'municipality_monthly_3d';

// Dev (non-standalone) fetch path. The standalone build embeds this same file as
// a gzip+base64 payload under the key `municipalities_monthly`.
export const MONTHLY_DATASET_URL =
  '../../data/02_transformed/standalone/gta_municipalities_monthly.geojson';

// Sequential warm ramp for single-month mode (low → high crime).
const GLOBAL_WARMING: ColorRangeSpec = {
  name: 'Global Warming',
  type: 'sequential',
  category: 'Uber',
  colors: ['#5A1846', '#900C3F', '#C70039', '#E3611C', '#F1920E', '#FFC300']
};

// Diverging ramp for YoY mode: blue = decrease (fewer crimes than last year),
// pale = ~no change, red = increase. ColorBrewer RdBu reversed.
const YOY_DIVERGING: ColorRangeSpec = {
  name: 'YoY Change (RdBu reversed)',
  type: 'diverging',
  category: 'ColorBrewer',
  colors: ['#2166ac', '#67a9cf', '#d1e5f0', '#f7f7f7', '#fddbc7', '#ef8a62', '#b2182b']
};

export const MONTHLY_MAP_STATE: MapStateSpec = {
  longitude: -79.4,
  latitude: 43.85,
  zoom: 8.6,
  pitch: 45,
  bearing: 0,
  dragRotate: true
};

export const MONTHLY_MAP_STYLE = 'voyager';

// Hover tooltip fields. MonthlyControl writes display_value plus (in YoY) the two
// underlying month values so a hovered bar reads honestly.
export const MONTHLY_TOOLTIPS: Record<string, string[]> = {
  [MONTHLY_DATASET_ID]: [
    'municipality',
    'display_value',
    'display_cur',
    'display_prev',
    'Population'
  ]
};

/** Build the layer spec for the active mode. Single uses a sequential warm ramp;
 *  YoY a diverging ramp. Both encode `display_value` on colour AND 3D height. */
export function monthlyLayerSpec(mode: MonthlyMode): GeoJsonLayerSpec {
  return {
    kind: 'geojson',
    id: MONTHLY_LAYER_ID,
    label: 'Crime by Municipality (monthly)',
    dataId: MONTHLY_DATASET_ID,
    isVisible: true,
    visConfig: {
      opacity: 0.85,
      filled: true,
      stroked: true,
      strokeColor: [255, 255, 255],
      strokeOpacity: 0.4,
      colorRange: mode === 'yoy' ? YOY_DIVERGING : GLOBAL_WARMING,
      enable3d: true,
      elevationScale: 4,
      heightRange: [0, 4000]
    },
    colorField: { name: 'display_value', type: 'real' },
    colorScale: 'quantize',
    heightField: { name: 'display_value', type: 'real' },
    heightScale: 'linear'
  };
}
