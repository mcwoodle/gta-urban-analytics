// Municipality crime-rate control.
//
// Drives the headline `municipality_crime_3d` layer. A "Total" button plus four
// crime-group toggles (Violent / Property / Nuisance / Other). Per-group rates
// are additive over a shared population denominator, so the displayed rate is
// simply the sum of the selected groups' rates (or the overall total when none
// are selected). The municipality dataset is tiny (~30 polygons), so we recompute
// `selected_rate`/`selected_count` client-side and replace the dataset — cheap and
// instant, and re-adding the layer gives the colour scale a fresh domain.
//
// Re-fetching the per-year GeoJSON needs a URL, so this is gated to the network
// (non-standalone) build; the standalone build shows the static Total rate.

import * as React from 'react';
import { useDispatch } from 'react-redux';
import { wrapTo, removeDataset, addDataToMap } from '@kepler.gl/actions';
import { processGeojson } from '@kepler.gl/processors';

import { GROUP_SLUGS, GROUP_COLOR, type CrimeGroup } from '../config/crimeGroups';
import { datasetUrlForYear } from '../data/loaders';
import { isStandalone } from '../data/standaloneLoader';
import { buildLayers } from '../layers';

const forward = wrapTo('map');
const DATASET_ID = 'municipalities';
const LAYER_ID = 'municipality_crime_3d';

const GROUPS = Object.keys(GROUP_SLUGS) as CrimeGroup[];

type FeatureCollection = { type: string; features: any[] };

/** Recompute every feature's selected_rate/selected_count for the chosen groups
 *  (empty set ⇒ the overall total). When `exclude` is set, the counts that drop
 *  incidents within 500 m of a known high-traffic venue (`*_excl_anomaly`) are
 *  used. Returns a NEW FeatureCollection. */
function withSelection(
  raw: FeatureCollection,
  groups: Set<CrimeGroup>,
  exclude: boolean
): FeatureCollection {
  const isTotal = groups.size === 0;
  const suffix = exclude ? '_excl_anomaly' : '';
  const slugs = [...groups].map((g) => GROUP_SLUGS[g]);

  return {
    ...raw,
    features: raw.features.map((f) => {
      const p = f.properties ?? {};
      const pop = Number(p.Population) || 0;
      const count = isTotal
        ? Number(p[`crime_count${suffix}`]) || 0
        : slugs.reduce((sum, s) => sum + (Number(p[`crime_count_${s}${suffix}`]) || 0), 0);
      const rate = pop > 0 ? Math.round((count / pop) * 1000 * 1000) / 1000 : 0;
      return { ...f, properties: { ...p, selected_count: count, selected_rate: rate } };
    })
  };
}

export function MunicipalityControl({ year }: { year: number }): JSX.Element | null {
  const dispatch = useDispatch();
  const rawRef = React.useRef<FeatureCollection | null>(null);
  const [selected, setSelected] = React.useState<Set<CrimeGroup>>(new Set());
  const [excludeAnomaly, setExcludeAnomaly] = React.useState(false);

  // (Re)fetch the raw GeoJSON whenever the year changes; reset to Total.
  React.useEffect(() => {
    if (isStandalone()) return;
    let cancelled = false;
    const url = datasetUrlForYear(DATASET_ID, year);
    if (!url) return;
    setSelected(new Set());
    setExcludeAnomaly(false);
    (async () => {
      try {
        const res = await fetch(url);
        if (!res.ok) return;
        const json = (await res.json()) as FeatureCollection;
        if (!cancelled) rawRef.current = json;
      } catch {
        /* municipality layer simply stays at its loaded Total values */
      }
    })();
    return () => {
      cancelled = true;
    };
  }, [year]);

  // The standalone build can't re-fetch per-year data, so hide the control there.
  if (isStandalone()) return null;

  const apply = (groups: Set<CrimeGroup>, exclude: boolean) => {
    setSelected(groups);
    setExcludeAnomaly(exclude);
    const raw = rawRef.current;
    if (!raw) return;

    const data = processGeojson(withSelection(raw, groups, exclude));
    if (!data) return;

    const layer = buildLayers().find((l: any) => l.id === LAYER_ID);

    dispatch(forward(removeDataset(DATASET_ID) as any));
    dispatch(
      forward(
        addDataToMap({
          datasets: [{ info: { id: DATASET_ID, label: 'Crime Rate by Municipality' }, data }],
          options: { centerMap: false, readOnly: false, keepExistingConfig: true },
          config: { version: 'v1', config: { visState: { layers: layer ? [layer] : [] } } } as any
        }) as any
      )
    );
  };

  const toggle = (g: CrimeGroup) => {
    const next = new Set(selected);
    next.has(g) ? next.delete(g) : next.add(g);
    apply(next, excludeAnomaly);
  };

  const isTotal = selected.size === 0;

  return (
    <div
      style={{
        position: 'absolute',
        top: 16,
        left: 340,
        zIndex: 100,
        background: 'rgba(41, 50, 60, 0.92)',
        color: '#e6e6e6',
        padding: '10px 14px',
        borderRadius: 6,
        fontFamily: 'ff-clan-web-pro, "Helvetica Neue", Helvetica, sans-serif',
        fontSize: 11,
        boxShadow: '0 2px 8px rgba(0, 0, 0, 0.4)',
        pointerEvents: 'auto',
        userSelect: 'none'
      }}
    >
      <label style={{ display: 'block', marginBottom: 6, fontWeight: 600 }}>
        Crime rate by municipality
      </label>
      <div style={{ display: 'flex', gap: 4, flexWrap: 'wrap', maxWidth: 320 }}>
        <button
          onClick={() => apply(new Set(), excludeAnomaly)}
          style={{
            background: isTotal ? '#4b6479' : '#1f262e',
            color: isTotal ? '#ffffff' : '#c2ccd6',
            border: '1px solid #3a4552',
            borderRadius: 4,
            padding: '4px 9px',
            fontSize: 11,
            fontFamily: 'inherit',
            fontWeight: isTotal ? 600 : 400,
            cursor: 'pointer'
          }}
        >
          Total
        </button>
        {GROUPS.map((g) => {
          const active = selected.has(g);
          return (
            <button
              key={g}
              onClick={() => toggle(g)}
              style={{
                background: active ? GROUP_COLOR[g] : '#1f262e',
                color: active ? '#101418' : '#c2ccd6',
                border: `1px solid ${active ? GROUP_COLOR[g] : '#3a4552'}`,
                borderRadius: 4,
                padding: '4px 9px',
                fontSize: 11,
                fontFamily: 'inherit',
                fontWeight: active ? 600 : 400,
                cursor: 'pointer'
              }}
            >
              {g}
            </button>
          );
        })}
      </div>

      <label
        style={{
          display: 'flex',
          alignItems: 'center',
          gap: 6,
          marginTop: 8,
          cursor: 'pointer'
        }}
      >
        <input
          type="checkbox"
          checked={excludeAnomaly}
          onChange={() => apply(selected, !excludeAnomaly)}
          style={{ cursor: 'pointer' }}
        />
        Exclude crimes near malls / high-traffic venues
      </label>

      <div style={{ marginTop: 6, fontSize: 9, color: '#b8c2cc' }}>
        {isTotal
          ? 'Showing total crime rate / 1,000 residents'
          : `Showing ${[...selected].join(' + ')} rate / 1,000`}
        {excludeAnomaly ? ' · venue-area incidents excluded' : ''}
      </div>
    </div>
  );
}
