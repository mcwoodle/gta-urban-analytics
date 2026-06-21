// Lite-profile heatmap layer.
// Uses Kepler's built-in 'heatmap' type (deck.gl HeatmapLayer) -- a flat,
// texture-aggregated density map that avoids the 3D column-extrusion shader
// path entirely. Mobile-safe: no GLSL fragment-shader issues.

import type { HeatmapLayerSpec } from '../data/types';

export function buildHeatmapLayer(spec: HeatmapLayerSpec) {
  return {
    id: spec.id,
    type: 'heatmap',
    config: {
      dataId: spec.dataId,
      label: spec.label,
      columns: {
        lat: spec.columns.lat,
        lng: spec.columns.lng
      },
      isVisible: spec.isVisible,
      visConfig: {
        opacity: spec.visConfig.opacity,
        radius: spec.visConfig.radius,
        colorRange: spec.visConfig.colorRange
      }
    },
    visualChannels: {
      weightField: {
        name: spec.weightField.name,
        type: spec.weightField.type
      }
    }
  };
}
