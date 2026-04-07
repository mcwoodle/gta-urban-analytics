// Top-level map shell.
//
// Responsibilities:
//   1. On mount, load all configured datasets via loaders.ts
//      (which automatically forks to standaloneLoader.ts when
//       window.__STANDALONE_MODE__ is set).
//   2. Build layer specs from the central config.
//   3. Dispatch `addDataToMap` with a frozen initial view state.
//   4. Render <KeplerGl> inside an AutoSizer with a custom RadiusControl
//      overlay.
//   5. When running in standalone mode, skip the Mapbox basemap and use
//      Kepler's bundled Carto dark-matter style so the page works from
//      file:// without hitting Mapbox's tile server.

import * as React from 'react';
import { useDispatch } from 'react-redux';
import AutoSizer from 'react-virtualized/dist/commonjs/AutoSizer';
import KeplerGl from '@kepler.gl/components';
import { addDataToMap, wrapTo, updateMap } from '@kepler.gl/actions';

import { VIZ_CONFIG } from '../config/visualization';
import { loadAllDatasets, validateColorFields } from '../data/loaders';
import { buildLayers } from '../layers';
import { RadiusControl } from './RadiusControl';

const MAP_ID = 'map';
const forward = wrapTo(MAP_ID);

// Injected by esbuild via `define` at build time. Empty string in the
// standalone build (no Mapbox required).
declare const process: { env: { MapboxAccessToken?: string } };

function isStandalone(): boolean {
  return typeof window !== 'undefined' && Boolean((window as any).__STANDALONE_MODE__);
}

export function MapShell(): JSX.Element {
  const dispatch = useDispatch();
  const [loaded, setLoaded] = React.useState(false);
  const [error, setError] = React.useState<string | null>(null);

  React.useEffect(() => {
    let cancelled = false;

    // Set location immediately so we don't look at SF while data loads
    dispatch(forward(updateMap(VIZ_CONFIG.mapState) as any));

    (async () => {
      try {
        const datasets = await loadAllDatasets();
        if (cancelled) return;

        validateColorFields(datasets);

        const layers = buildLayers();

        dispatch(
          forward(
            addDataToMap({
              datasets,
              options: { centerMap: false, readOnly: false },
              config: {
                version: 'v1',
                config: {
                  visState: { layers },
                  mapState: VIZ_CONFIG.mapState,
                  mapStyle: {
                    styleType: VIZ_CONFIG.mapStyle
                  }
                }
              } as any
            }) as any
          )
        );

        setLoaded(true);
      } catch (e: any) {
        // eslint-disable-next-line no-console
        console.error('[viz] failed to load datasets:', e);
        if (!cancelled) setError(e?.message ?? String(e));
      }
    })();

    return () => {
      cancelled = true;
    };
  }, [dispatch]);

  if (error) {
    return (
      <div
        style={{
          position: 'absolute',
          inset: 0,
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          color: '#ff8080',
          background: '#29323c',
          fontFamily: 'monospace',
          padding: 32,
          textAlign: 'center'
        }}
      >
        <div>
          <h2>Failed to load data</h2>
          <pre>{error}</pre>
        </div>
      </div>
    );
  }

  // Mapbox token is not needed in standalone mode — Carto basemap works
  // without it. In normal mode, use the baked-in token (may be empty, in
  // which case Kepler shows its own no-token overlay).
  const mapboxToken =
    (!isStandalone() && typeof process !== 'undefined' && process.env?.MapboxAccessToken) || '';

  return (
    <div style={{ position: 'absolute', inset: 0, overflow: 'hidden' }}>
      <AutoSizer>
        {({ height, width }: { height: number; width: number }) => (
          <KeplerGl
            id={MAP_ID}
            mapboxApiAccessToken={mapboxToken}
            width={width}
            height={height}
          />
        )}
      </AutoSizer>
      {loaded ? <RadiusControl /> : null}
    </div>
  );
}
