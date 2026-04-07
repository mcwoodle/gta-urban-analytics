// Layer 1 — Unified Crime Hexbin.
// Pure function of the config; no React, no Redux, no side effects.

import type { HexbinLayerSpec } from '../data/types';

export function buildHexbinLayer(spec: HexbinLayerSpec) {
  return {
    id: spec.id,
    type: 'hexagon',
    config: {
      dataId: spec.dataId,
      label: spec.label,
      columns: spec.columns,
      isVisible: spec.isVisible,
      visConfig: {
        worldUnitSize: spec.visConfig.worldUnitSize,
        elevationScale: spec.visConfig.elevationScale,
        enable3d: spec.visConfig.enable3d,
        coverage: spec.visConfig.coverage,
        opacity: spec.visConfig.opacity,
        colorRange: spec.visConfig.colorRange,
        resolution: 8
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
