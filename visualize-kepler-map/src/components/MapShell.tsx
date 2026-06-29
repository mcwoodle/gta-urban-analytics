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
import AutoSizerRaw from 'react-virtualized/dist/commonjs/AutoSizer';
import KeplerGl from '@kepler.gl/components';
import {
  addDataToMap,
  wrapTo,
  updateMap,
  mapStyleChange,
  removeDataset,
  toggleSidePanel
} from '@kepler.gl/actions';

import { getVizConfig, getProfile } from '../config/visualization';
import { loadAllDatasets, validateColorFields } from '../data/loaders';
import { buildLayers } from '../layers';
import { RadiusControl } from './RadiusControl';
import { YearControl } from './YearControl';
import { BivariateLegend } from './BivariateLegend';

// react-virtualized ships its own (pre-18) React types, so its AutoSizer class
// fails @types/react@18's `ElementClass` check when used as JSX. Re-type it as
// a function component with just the render-prop signature we use.
const AutoSizer = AutoSizerRaw as unknown as React.ComponentType<{
  children: (size: { height: number; width: number }) => React.ReactNode;
}>;

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
  const [year, setYear] = React.useState<number>(2025);

  const initialMount = React.useRef(true);

  React.useEffect(() => {
    let cancelled = false;
    const isInitial = initialMount.current;
    const vizConfig = getVizConfig();

    if (isInitial) {
      // Set location immediately so we don't look at SF while data loads
      dispatch(forward(updateMap(vizConfig.mapState) as any));
      dispatch(forward(mapStyleChange(vizConfig.mapStyle) as any));
      initialMount.current = false;
    } else {
      // Clear existing datasets from the map immediately upon year change
      vizConfig.datasets.forEach((d) => {
        dispatch(forward(removeDataset(d.id) as any));
      });
    }

    (async () => {
      try {
        const datasets = await loadAllDatasets(year);
        if (cancelled) return;

        validateColorFields(datasets);

        const layers = buildLayers();

        // Per-dataset hover tooltips. Kepler defaults to a dataset's first 5
        // columns, which hides the anomaly classification; this surfaces the
        // chosen fields (with `description` leading) on hover instead.
        const visState: Record<string, unknown> = { layers };
        if (vizConfig.tooltips) {
          visState.interactionConfig = {
            tooltip: {
              fieldsToShow: vizConfig.tooltips,
              compareMode: false,
              compareType: 'absolute',
              enabled: true
            }
          };
        }

        dispatch(
          forward(
            addDataToMap({
              datasets,
              options: { centerMap: false, readOnly: false, keepExistingConfig: true },
              config: {
                version: 'v1',
                config: {
                  visState,
                  mapState: vizConfig.mapState,
                  mapStyle: {
                    styleType: vizConfig.mapStyle
                  }
                }
              } as any
            }) as any
          )
        );

        setLoaded(true);

        // Collapse the left side panel by default — but only AFTER the first
        // load has rendered. Baking `activeSidePanel: null` into the initial
        // store state changes the very-first map layout and leaves the
        // deck.gl HeatmapLayer (mobile profile) stuck un-aggregated/blank.
        // Letting the map paint with the panel open, then collapsing, lets the
        // heatmap aggregate first; the collapse-driven resize keeps it painted.
        if (isInitial) {
          setTimeout(() => {
            if (!cancelled) dispatch(forward(toggleSidePanel(null as any) as any));
          }, 700);
        }
      } catch (e: any) {
        // eslint-disable-next-line no-console
        console.error('[viz] failed to load datasets:', e);
        if (!cancelled) setError(e?.message ?? String(e));
      }
    })();

    return () => {
      cancelled = true;
    };
  }, [dispatch, year]);

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
      {loaded ? (
        <>
          {getProfile() !== 'lite' && <RadiusControl />}
          {getProfile() !== 'lite' && <BivariateLegend />}
          <YearControl year={year} setYear={setYear} />
        </>
      ) : null}
    </div>
  );
}
