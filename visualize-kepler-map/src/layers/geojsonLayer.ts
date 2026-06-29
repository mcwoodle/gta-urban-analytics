// GeoJSON choropleths — one builder for every census polygon layer (income,
// crime-rate, the bivariate income×crime class, and the 3D crime-rate-by-
// population extrusion). Pure function of the config.

import type { GeoJsonLayerSpec } from '../data/types';

export function buildGeoJsonLayer(spec: GeoJsonLayerSpec) {
  const v = spec.visConfig;

  const visConfig: Record<string, unknown> = {
    opacity: v.opacity,
    filled: v.filled,
    stroked: v.stroked,
    strokeColor: v.strokeColor,
    strokeOpacity: v.strokeOpacity,
    colorRange: v.colorRange,
    radius: 10,
    wireframe: false
  };

  // Optional 3D extrusion (only the population-height layer sets these). Leaving
  // them undefined keeps every existing flat choropleth pixel-for-pixel the same.
  if (v.enable3d !== undefined) visConfig.enable3d = v.enable3d;
  if (v.elevationScale !== undefined) visConfig.elevationScale = v.elevationScale;
  if (v.heightRange !== undefined) visConfig.heightRange = v.heightRange;

  return {
    id: spec.id,
    type: 'geojson',
    config: {
      dataId: spec.dataId,
      label: spec.label,
      columns: { geojson: '_geojson' },
      isVisible: spec.isVisible,
      visConfig
    },
    visualChannels: {
      colorField: spec.colorField,
      colorScale: spec.colorScale,
      sizeField: null,
      sizeScale: 'linear',
      heightField: spec.heightField ?? null,
      heightScale: spec.heightScale ?? 'linear'
    }
  };
}
