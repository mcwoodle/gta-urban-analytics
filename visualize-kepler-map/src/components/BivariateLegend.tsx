// 3×3 key for the Income × Crime-Rate bivariate choropleth.
//
// A bivariate choropleth is unreadable without its 2D legend, so this renders
// the same nine colours the pipeline classes map to (imported from the central
// config, the single source of truth) laid out as income (vertical) × crime
// rate (horizontal). It mounts as an absolutely-positioned overlay, bottom-right,
// and only while the bivariate layer is actually visible — toggling that layer
// off in Kepler's panel hides the key too.

import * as React from 'react';
import { useSelector } from 'react-redux';
import { BIVARIATE_INCOME_CRIME } from '../config/visualization';

const COLORS = BIVARIATE_INCOME_CRIME.colors;

// Class index k = incomeTercile * 3 + crimeTercile (income outer, both
// Lower→Higher). Render rows top→bottom = higher→lower income, cols left→right
// = lower→higher crime, so the strong "lower-income · higher-crime" red sits in
// the bottom-right and "higher-income · lower-crime" blue in the top-left.
const GRID: number[][] = [
  [6, 7, 8], // higher income
  [3, 4, 5], // mid income
  [0, 1, 2] // lower income
];

const CELL_PX = 26;

const MUTED = '#b8c2cc';

/** True only while the bivariate layer exists on the map and is visible. */
function useBivariateVisible(): boolean {
  return useSelector((s: any) => {
    const layers = s.keplerGl?.map?.visState?.layers ?? [];
    const layer = layers.find((l: any) => l.id === 'income_crime_bivariate');
    return Boolean(layer?.config?.isVisible);
  });
}

export function BivariateLegend(): JSX.Element | null {
  const visible = useBivariateVisible();
  if (!visible) return null;

  return (
    <div
      style={{
        position: 'absolute',
        bottom: 28,
        right: 16,
        zIndex: 100,
        background: 'rgba(41, 50, 60, 0.92)',
        color: '#e6e6e6',
        padding: '12px 14px',
        borderRadius: 6,
        fontFamily: 'ff-clan-web-pro, "Helvetica Neue", Helvetica, sans-serif',
        fontSize: 11,
        boxShadow: '0 2px 8px rgba(0, 0, 0, 0.4)',
        userSelect: 'none',
        pointerEvents: 'auto',
        maxWidth: 220
      }}
    >
      <div style={{ fontWeight: 600, marginBottom: 8 }}>Income × Crime rate</div>

      <div style={{ display: 'flex', alignItems: 'stretch' }}>
        {/* Vertical income axis */}
        <div
          style={{
            display: 'flex',
            flexDirection: 'column',
            justifyContent: 'space-between',
            marginRight: 6,
            fontSize: 9,
            lineHeight: 1.1,
            color: MUTED,
            textAlign: 'right'
          }}
        >
          <span>Higher<br />income</span>
          <span>Lower<br />income</span>
        </div>

        <div>
          {/* The 3×3 colour matrix */}
          <div
            style={{
              display: 'grid',
              gridTemplateColumns: `repeat(3, ${CELL_PX}px)`,
              gridTemplateRows: `repeat(3, ${CELL_PX}px)`,
              gap: 2
            }}
          >
            {GRID.flat().map((k, i) => (
              <div key={i} style={{ background: COLORS[k], borderRadius: 2 }} />
            ))}
          </div>

          {/* Horizontal crime-rate axis */}
          <div
            style={{
              display: 'flex',
              justifyContent: 'space-between',
              marginTop: 4,
              fontSize: 9,
              color: MUTED
            }}
          >
            <span>Lower</span>
            <span>Crime&nbsp;rate&nbsp;→</span>
            <span>Higher</span>
          </div>
        </div>
      </div>

      <div style={{ marginTop: 10, fontSize: 9, lineHeight: 1.35, color: MUTED }}>
        Red = lower-income &amp; higher-crime · Blue = affluent &amp; safer ·
        Dark = affluent but higher-crime
      </div>
    </div>
  );
}
