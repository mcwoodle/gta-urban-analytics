// Layers 2 & 3 — GeoJSON choropleths (same builder, different colorField).
// Pure function of the config.

import type { GeoJsonLayerSpec } from '../data/types';

export function buildGeoJsonLayer(spec: GeoJsonLayerSpec) {
  return {
    id: spec.id,
    type: 'geojson',
    config: {
      dataId: spec.dataId,
      label: spec.label,
      columns: { geojson: '_geojson' },
      isVisible: spec.isVisible,
      visConfig: {
        opacity: spec.visConfig.opacity,
        filled: spec.visConfig.filled,
        stroked: spec.visConfig.stroked,
        strokeColor: spec.visConfig.strokeColor,
        strokeOpacity: spec.visConfig.strokeOpacity,
        colorRange: spec.visConfig.colorRange,
        radius: 10,
        wireframe: false
      }
    },
    visualChannels: {
      colorField: spec.colorField,
      colorScale: spec.colorScale,
      sizeField: null,
      sizeScale: 'linear'
    }
  };
}
