// Layer 4 — Shootings → municipality centroid arcs.
// Pure function of the config.

import type { ArcLayerSpec } from '../data/types';

export function buildArcLayer(spec: ArcLayerSpec) {
  return {
    id: spec.id,
    type: 'arc',
    config: {
      dataId: spec.dataId,
      label: spec.label,
      columns: spec.columns,
      isVisible: spec.isVisible,
      visConfig: {
        opacity: spec.visConfig.opacity,
        thickness: spec.visConfig.thickness,
        targetColor: spec.visConfig.targetColor,
        colorRange: spec.visConfig.colorRange
      }
    },
    visualChannels: {
      colorField: spec.colorField,
      colorScale: 'quantile',
      sizeField: spec.sizeField ?? null,
      sizeScale: 'linear'
    }
  };
}
