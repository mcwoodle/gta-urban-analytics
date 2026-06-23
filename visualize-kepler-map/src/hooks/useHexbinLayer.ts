// Selector hook that returns the live hexbin layer instance (or null before
// it's mounted). Used by RadiusControl to read the current worldUnitSize
// and dispatch updates via wrapTo('map').

import { useSelector } from 'react-redux';
import type { RootState } from '../store';

const HEXBIN_LAYER_ID = 'crime_hex';

export function useHexbinLayer(): any {
  return useSelector((state: RootState) => {
    // Kepler stores layers under keplerGl[mapId].visState.layers. The id we
    // pass to <KeplerGl id="map" /> is 'map'.
    const kepler = (state as any).keplerGl;
    const mapInstance = kepler?.map;
    const layers: any[] = mapInstance?.visState?.layers ?? [];
    return layers.find((l) => l.id === HEXBIN_LAYER_ID) ?? null;
  });
}
