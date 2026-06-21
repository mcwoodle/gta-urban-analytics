// Lite-profile H3 hexagon layer.
// Uses Kepler's built-in 'hexagonId' (H3HexagonLayer) — renders pre-aggregated
// hexagon columns with NO client-side GPU aggregation. Mobile-safe.

import type { H3LayerSpec } from '../data/types';

export function buildH3Layer(spec: H3LayerSpec) {
  return {
    id: spec.id,
    type: 'hexagonId',
    config: {
      dataId: spec.dataId,
      label: spec.label,
      columns: {
        hex_id: spec.columns.hex_id
      },
      isVisible: spec.isVisible,
      visConfig: {
        opacity: spec.visConfig.opacity,
        coverage: spec.visConfig.coverage,
        enable3d: spec.visConfig.enable3d,
        elevationScale: spec.visConfig.elevationScale,
        sizeRange: spec.visConfig.sizeRange,
        colorRange: spec.visConfig.colorRange,
        filled: true,
        outline: false,
        strokeOpacity: 0.5,
        enableElevationZoomFactor: true
      }
    },
    visualChannels: {
      colorField: {
        name: spec.colorField.name,
        type: spec.colorField.type
      },
      colorScale: spec.colorScale,
      sizeField: {
        name: spec.sizeField.name,
        type: spec.sizeField.type
      },
      sizeScale: spec.sizeScale
    }
  };
}
