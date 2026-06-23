// Lite-profile crime point layer.
// Uses Kepler's built-in 'point' (ScatterplotLayer) — zero GPU aggregation,
// maximally mobile-safe.

import type { PointLayerSpec } from '../data/types';

export function buildPointLayer(spec: PointLayerSpec) {
  return {
    id: spec.id,
    type: 'point',
    config: {
      dataId: spec.dataId,
      label: spec.label,
      columns: spec.columns,
      isVisible: spec.isVisible,
      visConfig: {
        radius: spec.visConfig.radius,
        opacity: spec.visConfig.opacity,
        filled: spec.visConfig.filled,
        colorRange: spec.visConfig.colorRange,
        radiusRange: spec.visConfig.radiusRange,
        fixedRadius: spec.visConfig.fixedRadius
      }
    },
    visualChannels: {
      colorField: null,
      colorScale: 'quantile',
      sizeField: null,
      sizeScale: 'linear'
    }
  };
}
