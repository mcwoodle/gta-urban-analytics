// ========================================================================
// Dataset loaders
// ========================================================================
// loadAllDatasets(year) fetches every dataset declared in VIZ_CONFIG for the
// requested year, parses each via the matching @kepler.gl/processors function,
// and returns Kepler dataset objects ready to hand to addDataToMap.
//
// When the page runs as the inlined single-file build
// (window.__STANDALONE_MODE__ === true) this forks to standaloneLoader.ts,
// which decodes the gzip+base64 payloads embedded in window.__STANDALONE_DATA__
// instead of hitting the network.
// ========================================================================

import { processCsvData, processGeojson } from '@kepler.gl/processors';

import { getVizConfig } from '../config/visualization';
import type { KeplerDataset } from './types';
import { isStandalone, loadStandaloneDatasets } from './standaloneLoader';

/** Rewrite a config URL's year segment (`.../02_transformed/<year>/...`) to
 *  the requested year, so one config drives every year. */
function urlForYear(url: string, year: number): string {
  return url.replace(/\/\d{4}\//, `/${year}/`);
}

function parseByExtension(url: string, text: string): KeplerDataset['data'] {
  const result = /\.(geo)?json$/i.test(url)
    ? processGeojson(JSON.parse(text))
    : processCsvData(text);
  if (!result) {
    throw new Error(`Parsed dataset from ${url} produced no rows.`);
  }
  return result;
}

export async function loadAllDatasets(year: number): Promise<KeplerDataset[]> {
  if (isStandalone()) {
    return loadStandaloneDatasets();
  }

  const config = getVizConfig();
  return Promise.all(
    config.datasets.map(async (ds): Promise<KeplerDataset> => {
      const url = urlForYear(ds.url, year);
      const res = await fetch(url);
      if (!res.ok) {
        throw new Error(
          `Failed to fetch ${ds.label} (${url}): ${res.status} ${res.statusText}`
        );
      }
      const text = await res.text();
      return { info: { id: ds.id, label: ds.label }, data: parseByExtension(url, text) };
    })
  );
}

/**
 * Warn (don't throw) when a layer's color/size channel references a field that
 * is absent from its dataset — typically a config typo or a pipeline schema
 * change. Logging keeps the rest of the map working while surfacing the issue.
 */
export function validateColorFields(datasets: KeplerDataset[]): void {
  const fieldsById = new Map<string, Set<string>>();
  for (const ds of datasets) {
    fieldsById.set(ds.info.id, new Set((ds.data?.fields ?? []).map((f) => f.name)));
  }

  const config = getVizConfig();
  for (const layer of config.layers) {
    const fields = fieldsById.get(layer.dataId);
    if (!fields) continue; // dataset not loaded (e.g. hidden) — nothing to check

    const referenced: Array<{ role: string; name: string }> = [];
    if ('colorField' in layer && layer.colorField) {
      referenced.push({ role: 'colorField', name: layer.colorField.name });
    }
    if ('sizeField' in layer && layer.sizeField) {
      referenced.push({ role: 'sizeField', name: layer.sizeField.name });
    }

    for (const ref of referenced) {
      if (!fields.has(ref.name)) {
        // eslint-disable-next-line no-console
        console.warn(
          `[viz] layer "${layer.id}" ${ref.role} "${ref.name}" not found in ` +
            `dataset "${layer.dataId}". Available fields: ${[...fields].join(', ')}`
        );
      }
    }
  }
}
