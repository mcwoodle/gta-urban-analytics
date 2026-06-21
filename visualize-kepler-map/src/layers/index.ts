// Central layer dispatcher.
//
// `buildLayers()` filters the config's `layers` array to those referencing
// a *visible* dataset, then dispatches each to its type-specific builder
// via a discriminated-union switch.
//
// Uses `getVizConfig()` so the active profile (full vs lite) is respected.

import { getVizConfig } from '../config/visualization';
import type { LayerSpec } from '../data/types';
import { buildHexbinLayer } from './hexbinLayer';
import { buildGeoJsonLayer } from './geojsonLayer';
import { buildArcLayer } from './arcLayer';
import { buildPointLayer } from './pointLayer';

export function buildLayers() {
  const config = getVizConfig();
  const visibleDatasetIds = new Set(
    config.datasets.filter((d) => d.visible).map((d) => d.id)
  );

  return config.layers
    .filter((layer) => visibleDatasetIds.has(layer.dataId))
    .map(buildLayer);
}

function buildLayer(layer: LayerSpec) {
  switch (layer.kind) {
    case 'hexbin':
      return buildHexbinLayer(layer);
    case 'geojson':
      return buildGeoJsonLayer(layer);
    case 'arc':
      return buildArcLayer(layer);
    case 'point':
      return buildPointLayer(layer);
    default: {
      // Exhaustiveness check — TS will flag a new `kind` that isn't handled.
      const _exhaustive: never = layer;
      return _exhaustive;
    }
  }
}
