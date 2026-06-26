// Selector hooks over the live Kepler visState.
//
// Kepler stores its state under keplerGl[mapId]; the id we pass to
// <KeplerGl id="map" /> is 'map', so everything hangs off keplerGl.map.visState.

import { useSelector } from 'react-redux';
import type { RootState } from '../store';

const MAP_ID = 'map';
const HEXBIN_LAYER_ID = 'crime_hex';

/** Return the live layer instance with the given id (or null before mount). */
export function useLayerById(id: string): any {
  return useSelector((state: RootState) => {
    const mapInstance = (state as any).keplerGl?.[MAP_ID];
    const layers: any[] = mapInstance?.visState?.layers ?? [];
    return layers.find((l) => l.id === id) ?? null;
  });
}

/** Return the live hexbin layer instance (used by RadiusControl). */
export function useHexbinLayer(): any {
  return useLayerById(HEXBIN_LAYER_ID);
}

/** Return the real Kepler `Field[]` for a dataset (needed to resolve a
 *  colorField to the actual Field object, not a bare {name,type}). Empty
 *  array before the dataset is loaded. */
export function useDatasetFields(datasetId: string): any[] {
  return useSelector((state: RootState) => {
    const mapInstance = (state as any).keplerGl?.[MAP_ID];
    const dataset = mapInstance?.visState?.datasets?.[datasetId];
    return dataset?.fields ?? [];
  });
}

/** Return the live filters array from visState (for caching a filter idx). */
export function useFilters(): any[] {
  return useSelector((state: RootState) => {
    const mapInstance = (state as any).keplerGl?.[MAP_ID];
    return mapInstance?.visState?.filters ?? [];
  });
}
