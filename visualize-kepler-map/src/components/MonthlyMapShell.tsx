// Monthly map shell.
//
// A trimmed sibling of MapShell for the standalone-monthly map. It loads ONE
// dataset — the per-month municipality GeoJSON — as a raw FeatureCollection
// (standalone: decode the embedded payload; dev: fetch from disk), seeds the
// viewport, and hands the raw collection to MonthlyControl, which owns all
// layer rendering (initial + on every month/mode/metric change).

import * as React from 'react';
import { useDispatch } from 'react-redux';
import AutoSizerRaw from 'react-virtualized/dist/commonjs/AutoSizer';
import KeplerGl from '@kepler.gl/components';
import { wrapTo, updateMap, mapStyleChange } from '@kepler.gl/actions';

import {
  MONTHLY_DATASET_ID,
  MONTHLY_DATASET_URL,
  MONTHLY_MAP_STATE,
  MONTHLY_MAP_STYLE
} from '../config/monthlyVisualization';
import { isStandalone, decodeEmbeddedText } from '../data/standaloneLoader';
import { MonthlyControl, type FeatureCollection } from './MonthlyControl';

const AutoSizer = AutoSizerRaw as unknown as React.ComponentType<{
  children: (size: { height: number; width: number }) => React.ReactNode;
}>;

const MAP_ID = 'map';
const forward = wrapTo(MAP_ID);

declare const process: { env: { MapboxAccessToken?: string } };

async function loadRaw(): Promise<FeatureCollection> {
  if (isStandalone()) {
    const text = await decodeEmbeddedText(MONTHLY_DATASET_ID);
    if (!text) {
      throw new Error(
        `Standalone payload missing "${MONTHLY_DATASET_ID}" — rebuild with ` +
          `\`yarn build:standalone:monthly\`.`
      );
    }
    return JSON.parse(text) as FeatureCollection;
  }
  const res = await fetch(MONTHLY_DATASET_URL);
  if (!res.ok) {
    throw new Error(
      `Failed to fetch monthly municipality data (${MONTHLY_DATASET_URL}): ` +
        `${res.status} ${res.statusText}`
    );
  }
  return (await res.json()) as FeatureCollection;
}

export function MonthlyMapShell(): JSX.Element {
  const dispatch = useDispatch();
  const [raw, setRaw] = React.useState<FeatureCollection | null>(null);
  const [error, setError] = React.useState<string | null>(null);

  React.useEffect(() => {
    let cancelled = false;
    dispatch(forward(updateMap(MONTHLY_MAP_STATE) as any));
    dispatch(forward(mapStyleChange(MONTHLY_MAP_STYLE) as any));
    (async () => {
      try {
        const fc = await loadRaw();
        if (!cancelled) setRaw(fc);
      } catch (e: any) {
        // eslint-disable-next-line no-console
        console.error('[viz] failed to load monthly data:', e);
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
      {raw ? <MonthlyControl raw={raw} /> : null}
    </div>
  );
}
