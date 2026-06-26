// Kepler 'point' (ScatterplotLayer) builder.
//
// Supports an optional colorField/sizeField so a point layer can be data-driven
// (e.g. the coordinate-anomaly overlay sized + coloured by incident_count).
// When neither is set it renders as a plain fixed-style scatter.

import type { PointLayerSpec } from '../data/types';

export function buildPointLayer(spec: PointLayerSpec) {
  const visConfig: Record<string, unknown> = {
    radius: spec.visConfig.radius,
    opacity: spec.visConfig.opacity,
    filled: spec.visConfig.filled,
    colorRange: spec.visConfig.colorRange,
    radiusRange: spec.visConfig.radiusRange,
    fixedRadius: spec.visConfig.fixedRadius
  };
  if (spec.visConfig.outline !== undefined) visConfig.outline = spec.visConfig.outline;
  if (spec.visConfig.thickness !== undefined) visConfig.thickness = spec.visConfig.thickness;

  return {
    id: spec.id,
    type: 'point',
    config: {
      dataId: spec.dataId,
      label: spec.label,
      columns: spec.columns,
      isVisible: spec.isVisible,
      visConfig
    },
    visualChannels: {
      colorField: spec.colorField ?? null,
      colorScale: spec.colorScale ?? 'quantile',
      sizeField: spec.sizeField ?? null,
      sizeScale: spec.sizeScale ?? 'linear'
    }
  };
}
