// ========================================================================
// Visualization type contract
// ========================================================================
// The single source of truth for the shapes consumed by:
//   - src/config/visualization.ts  (authors the VIZ_CONFIG object)
//   - src/layers/*                 (read LayerSpec variants)
//   - src/data/loaders.ts          (produce KeplerDataset[])
//
// A discriminated union on `kind` lets buildLayers() dispatch each layer to
// its type-specific builder with full exhaustiveness checking.
// ========================================================================

/** A Kepler.gl color ramp definition (matches Kepler's ColorRange shape). */
export interface ColorRangeSpec {
  name: string;
  type: string;
  category: string;
  colors: string[];
}

/** A field reference for a visual channel (color/size). `type` mirrors
 *  Kepler's field types: 'real' | 'integer' | 'string' | 'timestamp' | ... */
export interface FieldSpec {
  name: string;
  type: string;
}

/** One dataset to load. `url` is resolved relative to the host page; the
 *  loader rewrites the year segment per the selected year. */
export interface DatasetSpec {
  id: string;
  label: string;
  url: string;
  visible: boolean;
}

/** Initial viewport. */
export interface MapStateSpec {
  longitude: number;
  latitude: number;
  zoom: number;
  pitch?: number;
  bearing?: number;
  dragRotate?: boolean;
}

interface BaseLayerSpec {
  id: string;
  label: string;
  dataId: string;
  isVisible: boolean;
}

export interface HexbinLayerSpec extends BaseLayerSpec {
  kind: 'hexbin';
  columns: { lat: string; lng: string };
  visConfig: {
    worldUnitSize: number;
    elevationScale: number;
    enable3d: boolean;
    coverage: number;
    opacity: number;
    colorRange: ColorRangeSpec;
  };
}

export interface GeoJsonLayerSpec extends BaseLayerSpec {
  kind: 'geojson';
  visConfig: {
    opacity: number;
    filled: boolean;
    stroked: boolean;
    strokeColor?: [number, number, number];
    strokeOpacity?: number;
    colorRange: ColorRangeSpec;
  };
  colorField: FieldSpec;
  colorScale: string;
}

export interface ArcLayerSpec extends BaseLayerSpec {
  kind: 'arc';
  columns: { lat0: string; lng0: string; lat1: string; lng1: string };
  visConfig: {
    opacity: number;
    thickness: number;
    targetColor: [number, number, number];
    colorRange: ColorRangeSpec;
  };
  colorField: FieldSpec;
  sizeField?: FieldSpec;
}

export interface PointLayerSpec extends BaseLayerSpec {
  kind: 'point';
  columns: { lat: string; lng: string };
  visConfig: {
    radius: number;
    opacity: number;
    filled: boolean;
    colorRange: ColorRangeSpec;
    radiusRange: [number, number];
    fixedRadius: boolean;
  };
}

export interface H3LayerSpec extends BaseLayerSpec {
  kind: 'h3';
  columns: { hex_id: string };
  visConfig: {
    opacity: number;
    coverage: number;
    enable3d: boolean;
    elevationScale: number;
    sizeRange: [number, number];
    colorRange: ColorRangeSpec;
  };
  colorField: FieldSpec;
  colorScale: string;
  sizeField: FieldSpec;
  sizeScale: string;
}

export interface HeatmapLayerSpec extends BaseLayerSpec {
  kind: 'heatmap';
  columns: { lat: string; lng: string };
  visConfig: {
    opacity: number;
    radius: number;
    colorRange: ColorRangeSpec;
  };
  weightField: FieldSpec;
}

export type LayerSpec = HexbinLayerSpec | GeoJsonLayerSpec | ArcLayerSpec | PointLayerSpec | H3LayerSpec | HeatmapLayerSpec;

export interface VisualizationConfig {
  datasets: DatasetSpec[];
  layers: LayerSpec[];
  mapState: MapStateSpec;
  /** Kepler base map style id (e.g. 'voyager', 'dark', 'light'). */
  mapStyle: string;
}

/** A dataset in the shape `addDataToMap` expects: dataset info plus the
 *  `{ fields, rows }` payload produced by @kepler.gl/processors. `fields`
 *  mirrors Kepler's `ProtoDatasetField` (both `name` and `type` required). */
export interface KeplerDataset {
  info: { id: string; label: string };
  data: {
    fields: Array<{ name: string; type: string; [key: string]: any }>;
    rows: any[][];
  };
}
