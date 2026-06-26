// Crime-group control overlay.
//
// A segmented single-select (Total · Violent · Property · Nuisance · Other) that
// re-colours the per-capita rate choropleth by bucket (mechanism B) AND filters
// a crime-point scatter to that bucket (mechanism A). The buckets are an
// already-loaded column (`crime_group` on crime_points, `crime_rate_<slug>_per_1k`
// on census_da), so this MUTATES Kepler state — it never reloads data.
//
// Modelled on RadiusControl: absolutely positioned overlay, dispatches through
// wrapTo('map').

import * as React from 'react';
import { useDispatch } from 'react-redux';
import {
  wrapTo,
  layerConfigChange,
  layerVisualChannelConfigChange,
  addFilter,
  setFilter,
  removeFilter
} from '@kepler.gl/actions';

import { GROUP_SLUGS } from '../config/crimeGroups';
import {
  useLayerById,
  useDatasetFields,
  useFilters
} from '../hooks/useHexbinLayer';

const forward = wrapTo('map');

const RATE_LAYER_ID = 'crime_rate_choropleth';
const POINT_LAYER_ID = 'crime_by_group';
const BIVARIATE_LAYER_ID = 'income_crime_bivariate';
const CRIME_DATASET_ID = 'crime_points';

type Selection = 'Total' | keyof typeof GROUP_SLUGS;

const OPTIONS: Selection[] = ['Total', 'Violent', 'Property', 'Nuisance', 'Other'];

/** Column on census_da that the rate choropleth should colour by for a given
 *  selection. Total → the all-crime total; a bucket → its per-bucket rate. */
function rateFieldName(sel: Selection): string {
  return sel === 'Total'
    ? 'crime_rate_per_1k'
    : `crime_rate_${GROUP_SLUGS[sel]}_per_1k`;
}

export function CrimeGroupControl(): JSX.Element | null {
  const dispatch = useDispatch();
  const [selected, setSelected] = React.useState<Selection>('Total');

  const rateLayer = useLayerById(RATE_LAYER_ID);
  const pointLayer = useLayerById(POINT_LAYER_ID);
  const bivariateLayer = useLayerById(BIVARIATE_LAYER_ID);
  const censusFields = useDatasetFields('census_da');
  const filters = useFilters();

  // Cache the crime_group filter's index so we create it only once (R5).
  const filterIdxRef = React.useRef<number | null>(null);

  // If a year change rebuilt the datasets, the cached filter is gone — forget it
  // so the next bucket selection recreates it.
  React.useEffect(() => {
    const idx = filterIdxRef.current;
    if (idx !== null && !filters[idx]) {
      filterIdxRef.current = null;
    }
  }, [filters]);

  // Hide the control until the layers it drives exist on the map.
  if (!rateLayer || !pointLayer) return null;

  const apply = (sel: Selection) => {
    setSelected(sel);

    const isTotal = sel === 'Total';

    // ── Mechanism B: per-capita rate choropleth recolor ──────────────────
    // Resolve the REAL Kepler Field object (not a bare {name,type}) — the
    // visual-channel change needs the dataset's actual Field (R3).
    const field = censusFields.find((f: any) => f.name === rateFieldName(sel));

    if (isTotal) {
      // Headline state: restore the bivariate choropleth, hide the single-metric
      // rate choropleth (avoid two stacked census choropleths — R6).
      if (bivariateLayer) {
        dispatch(forward(layerConfigChange(bivariateLayer, { isVisible: true }) as any));
      }
      dispatch(forward(layerConfigChange(rateLayer, { isVisible: false }) as any));
      if (field) {
        dispatch(
          forward(
            layerVisualChannelConfigChange(rateLayer, { colorField: field } as any, 'color') as any
          )
        );
      }
    } else {
      // Bucket active: hide bivariate, show the rate choropleth recoloured to
      // this bucket's per-capita rate.
      if (bivariateLayer) {
        dispatch(forward(layerConfigChange(bivariateLayer, { isVisible: false }) as any));
      }
      dispatch(forward(layerConfigChange(rateLayer, { isVisible: true }) as any));
      if (field) {
        dispatch(
          forward(
            layerVisualChannelConfigChange(rateLayer, { colorField: field } as any, 'color') as any
          )
        );
      }
    }

    // ── Mechanism A: filtered crime-point scatter ────────────────────────
    if (isTotal) {
      // Drop the filter and hide the 126k-point scatter (keeps first paint
      // light — points only render while a bucket is chosen).
      const idx = filterIdxRef.current;
      if (idx !== null && filters[idx]) {
        dispatch(forward(removeFilter(idx) as any));
        filterIdxRef.current = null;
      }
      dispatch(forward(layerConfigChange(pointLayer, { isVisible: false }) as any));
    } else {
      // Lazily create the crime_group filter once, then point it at this bucket.
      let idx = filterIdxRef.current;
      if (idx === null || !filters[idx]) {
        idx = filters.length;
        filterIdxRef.current = idx;
        dispatch(forward(addFilter(CRIME_DATASET_ID) as any));
        dispatch(forward(setFilter(idx, 'name', 'crime_group') as any));
      }
      dispatch(forward(setFilter(idx, 'value', [sel]) as any));
      dispatch(forward(layerConfigChange(pointLayer, { isVisible: true }) as any));
    }
  };

  return (
    <div
      style={{
        position: 'absolute',
        top: 64,
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
        Crime type
      </label>
      <div style={{ display: 'flex', gap: 4 }}>
        {OPTIONS.map((opt) => {
          const active = opt === selected;
          return (
            <button
              key={opt}
              onClick={() => apply(opt)}
              style={{
                background: active ? '#4b6479' : '#1f262e',
                color: active ? '#ffffff' : '#c2ccd6',
                border: '1px solid #3a4552',
                borderRadius: 4,
                padding: '4px 9px',
                fontSize: 11,
                fontFamily: 'inherit',
                fontWeight: active ? 600 : 400,
                cursor: 'pointer'
              }}
            >
              {opt}
            </button>
          );
        })}
      </div>
    </div>
  );
}
