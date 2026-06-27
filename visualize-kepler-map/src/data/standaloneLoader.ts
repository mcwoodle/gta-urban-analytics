// ========================================================================
// Standalone-mode dataset loader
// ========================================================================
// Used by the single-file build (dist/standalone.html), where the three
// datasets are gzip-compressed + base64-encoded and inlined into the page by
// scripts/build-standalone.mjs as:
//
//   window.__STANDALONE_MODE__ = true;
//   window.__STANDALONE_DATA__ = { crime_points: "<b64>", census_da: "<b64>", ... };
//
// We decode each payload entirely in the browser (no network) via the native
// DecompressionStream API, then hand it to the same @kepler.gl/processors
// parsers the network loader uses.
//
// The embedded payload is a single snapshot baked at build time, so it is not
// year-partitioned — every year selection resolves to the same data here.
// ========================================================================

import { processCsvData, processGeojson } from '@kepler.gl/processors';
import type { KeplerDataset } from './types';

interface StandaloneEntry {
  id: string;
  label: string;
  format: 'csv' | 'geojson';
}

// Embedded payload keys (set by scripts/build-standalone.mjs) → the
// dataset id/label/format the rest of the app expects. Ids must match
// VIZ_CONFIG.datasets so layers bind to the right data.
//
// Full profile embeds: crime_points, census_da, shooting_arcs, coordinate_anomalies
// Lite profile embeds: crime_h3_lite (pre-aggregated H3 cells)
const ENTRIES_FULL: StandaloneEntry[] = [
  { id: 'crime_points', label: 'Unified GTA Crime', format: 'csv' },
  { id: 'census_da', label: 'Census Dissemination Areas', format: 'geojson' },
  { id: 'shooting_arcs', label: 'Shooting → Centroid Arcs', format: 'csv' },
  { id: 'coordinate_anomalies', label: 'Coordinate Anomalies (placeholder/snapped)', format: 'csv' },
  { id: 'municipalities', label: 'Crime Rate by Municipality', format: 'geojson' }
];

const ENTRIES_LITE: StandaloneEntry[] = [
  { id: 'crime_heatmap_lite', label: 'Crime Density Heatmap', format: 'csv' }
];

function getEntries(): StandaloneEntry[] {
  const isLite =
    typeof window !== 'undefined' && (window as any).__VIZ_PROFILE__ === 'lite';
  return isLite ? ENTRIES_LITE : ENTRIES_FULL;
}

export function isStandalone(): boolean {
  return typeof window !== 'undefined' && Boolean((window as any).__STANDALONE_MODE__);
}

function embeddedData(): Record<string, string> {
  const data = (window as any).__STANDALONE_DATA__;
  if (!data) {
    throw new Error(
      'Standalone mode is enabled but window.__STANDALONE_DATA__ is missing. ' +
        'Rebuild with `yarn build:standalone`.'
    );
  }
  return data as Record<string, string>;
}

/** Decode a base64 string into raw bytes. */
function base64ToBytes(b64: string): Uint8Array {
  const binary = atob(b64);
  const bytes = new Uint8Array(binary.length);
  for (let i = 0; i < binary.length; i++) {
    bytes[i] = binary.charCodeAt(i);
  }
  return bytes;
}

/** Gunzip raw bytes into text using the browser-native DecompressionStream. */
async function gunzipToText(bytes: Uint8Array): Promise<string> {
  if (typeof (globalThis as any).DecompressionStream !== 'function') {
    throw new Error(
      'This browser lacks the DecompressionStream API required to read the ' +
        'embedded data. Use Chrome 80+, Firefox 113+, Safari 16.4+, or Edge 80+.'
    );
  }
  const ds = new (globalThis as any).DecompressionStream('gzip');
  const stream = new Blob([bytes]).stream().pipeThrough(ds);
  return await new Response(stream).text();
}

export async function loadStandaloneDatasets(): Promise<KeplerDataset[]> {
  const data = embeddedData();
  const datasets: KeplerDataset[] = [];

  for (const entry of getEntries()) {
    const b64 = data[entry.id];
    if (!b64) {
      // eslint-disable-next-line no-console
      console.warn(`[viz] standalone payload missing key "${entry.id}" — skipping.`);
      continue;
    }
    const text = await gunzipToText(base64ToBytes(b64));
    const parsed =
      entry.format === 'geojson' ? processGeojson(JSON.parse(text)) : processCsvData(text);
    if (!parsed) {
      // eslint-disable-next-line no-console
      console.warn(`[viz] standalone payload "${entry.id}" parsed to no rows — skipping.`);
      continue;
    }
    datasets.push({ info: { id: entry.id, label: entry.label }, data: parsed });
  }

  return datasets;
}
