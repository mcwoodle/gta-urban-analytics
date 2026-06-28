// Monthly map control.
//
// Owns the single `municipality_monthly_3d` layer. The municipality GeoJSON
// carries every month's crime as `count_YYYY_MM` / `rate_YYYY_MM_per_1k`
// columns; this control recomputes a per-feature `display_value` for the chosen
// month / mode / metric, then replaces the dataset + re-adds the layer (so the
// colour scale gets a fresh domain) — the same client-side pattern as
// MunicipalityControl, but driven entirely from the in-memory FeatureCollection
// so it works in the standalone single-file build too.
//
// Modes:
//   • single — a month's crime (absolute or per-1k).
//   • yoy    — a 2026 month minus its 2025 twin (Δ). Height encodes Δ: largest
//     decrease ⇒ flat, largest increase ⇒ tallest (Kepler linear height scale).

import * as React from 'react';
import { useDispatch } from 'react-redux';
import { wrapTo, removeDataset, addDataToMap } from '@kepler.gl/actions';
import { processGeojson } from '@kepler.gl/processors';

import {
  MONTHLY_DATASET_ID,
  MONTHLY_TOOLTIPS,
  monthlyLayerSpec,
  type MonthlyMode,
  type MonthlyMetric
} from '../config/monthlyVisualization';
import { buildGeoJsonLayer } from '../layers/geojsonLayer';

const forward = wrapTo('map');

export type FeatureCollection = { type: string; features: any[] };

const COUNT_KEY = /^count_(\d{4})_(\d{2})$/;

/** Distinct 'YYYY_MM' months present in the data, ascending. */
function deriveMonths(raw: FeatureCollection): string[] {
  const found = new Set<string>();
  for (const f of raw.features ?? []) {
    for (const key of Object.keys(f.properties ?? {})) {
      const m = key.match(COUNT_KEY);
      if (m) found.add(`${m[1]}_${m[2]}`);
    }
  }
  return [...found].sort();
}

/** 2026 months that also have their 2025 twin (so a Δ can be computed). */
function yoyMonths(months: string[]): string[] {
  const set = new Set(months);
  return months.filter((m) => m.startsWith('2026_') && set.has(`2025_${m.slice(5)}`));
}

const label = (m: string) => m.replace('_', '-');
const fieldFor = (m: string, metric: MonthlyMetric) =>
  metric === 'per1k' ? `rate_${m}_per_1k` : `count_${m}`;

/** Recompute every feature's display_value for the selection. Returns a NEW
 *  FeatureCollection. */
function withDisplay(
  raw: FeatureCollection,
  mode: MonthlyMode,
  metric: MonthlyMetric,
  month: string
): FeatureCollection {
  const round3 = (n: number) => Math.round(n * 1000) / 1000;
  return {
    ...raw,
    features: raw.features.map((f) => {
      const p = f.properties ?? {};
      let value: number;
      let cur: number;
      let prev: number | null;
      if (mode === 'yoy') {
        const prevMonth = `2025_${month.slice(5)}`;
        cur = Number(p[fieldFor(month, metric)]) || 0;
        prev = Number(p[fieldFor(prevMonth, metric)]) || 0;
        value = round3(cur - prev);
      } else {
        cur = Number(p[fieldFor(month, metric)]) || 0;
        prev = null;
        value = round3(cur);
      }
      return {
        ...f,
        properties: { ...p, display_value: value, display_cur: round3(cur), display_prev: prev }
      };
    })
  };
}

export function MonthlyControl({ raw }: { raw: FeatureCollection }): JSX.Element {
  const dispatch = useDispatch();

  const months = React.useMemo(() => deriveMonths(raw), [raw]);
  const yoy = React.useMemo(() => yoyMonths(months), [months]);

  const [mode, setMode] = React.useState<MonthlyMode>('single');
  const [metric, setMetric] = React.useState<MonthlyMetric>('per1k');
  const [month, setMonth] = React.useState<string>(
    () => months[months.length - 1] ?? ''
  );

  // Months selectable for the active mode (YoY needs a 2025 twin).
  const available = mode === 'yoy' ? yoy : months;

  // Keep `month` valid when the mode flips (e.g. single → yoy with a 2025 month).
  React.useEffect(() => {
    if (available.length && !available.includes(month)) {
      setMonth(available[available.length - 1]);
    }
  }, [mode]); // eslint-disable-line react-hooks/exhaustive-deps

  // (Re)render the layer whenever the selection changes — also the initial paint.
  React.useEffect(() => {
    if (!month || !available.includes(month)) return;
    const data = processGeojson(withDisplay(raw, mode, metric, month));
    if (!data) return;

    const layer = buildGeoJsonLayer(monthlyLayerSpec(mode));

    dispatch(forward(removeDataset(MONTHLY_DATASET_ID) as any));
    dispatch(
      forward(
        addDataToMap({
          datasets: [
            { info: { id: MONTHLY_DATASET_ID, label: 'Crime by Municipality (monthly)' }, data }
          ],
          options: { centerMap: false, readOnly: false, keepExistingConfig: true },
          config: {
            version: 'v1',
            config: {
              visState: {
                layers: [layer],
                interactionConfig: {
                  tooltip: {
                    fieldsToShow: MONTHLY_TOOLTIPS,
                    compareMode: false,
                    compareType: 'absolute',
                    enabled: true
                  }
                }
              }
            }
          } as any
        }) as any
      )
    );
  }, [raw, mode, metric, month, available, dispatch]);

  const btn = (active: boolean) => ({
    background: active ? '#4b6479' : '#1f262e',
    color: active ? '#ffffff' : '#c2ccd6',
    border: '1px solid #3a4552',
    borderRadius: 4,
    padding: '4px 9px',
    fontSize: 11,
    fontFamily: 'inherit',
    fontWeight: active ? 600 : 400,
    cursor: 'pointer'
  });

  const isPartial = month && month >= '2026_06'; // current YTD month may be incomplete

  return (
    <div
      style={{
        position: 'absolute',
        top: 16,
        left: 16,
        zIndex: 100,
        background: 'rgba(41, 50, 60, 0.92)',
        color: '#e6e6e6',
        padding: '10px 14px',
        borderRadius: 6,
        fontFamily: 'ff-clan-web-pro, "Helvetica Neue", Helvetica, sans-serif',
        fontSize: 11,
        boxShadow: '0 2px 8px rgba(0, 0, 0, 0.4)',
        pointerEvents: 'auto',
        userSelect: 'none',
        maxWidth: 280
      }}
    >
      <label style={{ display: 'block', marginBottom: 6, fontWeight: 600 }}>
        Monthly crime by municipality
      </label>

      <div style={{ display: 'flex', gap: 4, marginBottom: 6 }}>
        <button style={btn(mode === 'single')} onClick={() => setMode('single')}>
          Single month
        </button>
        <button style={btn(mode === 'yoy')} onClick={() => setMode('yoy')}>
          Year-over-year
        </button>
      </div>

      <div style={{ display: 'flex', gap: 4, marginBottom: 6 }}>
        <button style={btn(metric === 'absolute')} onClick={() => setMetric('absolute')}>
          Absolute
        </button>
        <button style={btn(metric === 'per1k')} onClick={() => setMetric('per1k')}>
          Per 1,000
        </button>
      </div>

      <div style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
        <label style={{ fontWeight: 600 }}>{mode === 'yoy' ? '2026 month:' : 'Month:'}</label>
        <select
          value={month}
          onChange={(e) => setMonth(e.target.value)}
          style={{
            background: '#1f262e',
            color: '#e6e6e6',
            border: '1px solid #3a4552',
            padding: '4px 8px',
            borderRadius: 4,
            outline: 'none',
            cursor: 'pointer',
            fontFamily: 'inherit'
          }}
        >
          {available.map((m) => (
            <option key={m} value={m}>
              {label(m)}
            </option>
          ))}
        </select>
      </div>

      <div style={{ marginTop: 6, fontSize: 9, color: '#b8c2cc', lineHeight: 1.4 }}>
        {mode === 'yoy'
          ? `Δ vs ${label('2025_' + month.slice(5))} — height: largest decrease flat, largest increase tallest; blue = down, red = up.`
          : `Showing ${metric === 'per1k' ? 'crimes / 1,000 residents' : 'absolute crime count'} for ${label(month)}.`}
        {isPartial ? ' Note: latest month is year-to-date and may be partial.' : ''}
      </div>
    </div>
  );
}
