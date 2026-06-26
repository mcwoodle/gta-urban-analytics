// Legend for the crime-group per-capita rate choropleth.
//
// Visible only while the `crime_rate_choropleth` layer is visible (i.e. a bucket
// is active in CrimeGroupControl). Shows the active bucket, the sequential rate
// ramp Kepler is actually using, and a coverage caveat sourced from
// coverage.json — because per-capita bucket rates are structurally low for
// regions that never report a category (Durham, Toronto-MCI), so they must never
// be shown without the caveat (R2).

import * as React from 'react';

import { GROUP_SLUGS } from '../config/crimeGroups';
import { useLayerById } from '../hooks/useHexbinLayer';
import { useCoverage, type Coverage } from '../hooks/useCoverage';

const RATE_LAYER_ID = 'crime_rate_choropleth';
const MUTED = '#b8c2cc';

// Reverse of rateFieldName(): per-bucket rate column → bucket display label.
const FIELD_TO_LABEL: Record<string, string> = {
  crime_rate_per_1k: 'Total',
  ...Object.fromEntries(
    Object.entries(GROUP_SLUGS).map(([label, slug]) => [
      `crime_rate_${slug}_per_1k`,
      label
    ])
  )
};

/** Build a one-line, data-driven coverage caveat from coverage.json. */
function coverageCaveat(coverage: Coverage | null): string {
  if (!coverage) {
    return 'Coverage varies by region — some report only a subset of crime types; current-year data may be year-to-date.';
  }

  const parts: string[] = [];

  // Regions that report fewer than all four buckets (the structural-gap warning).
  const ALL_GROUPS = new Set(Object.keys(GROUP_SLUGS));
  const limited = Object.entries(coverage.regions)
    .map(([region, info]) => ({
      region,
      groups: (info.groups_present ?? []).filter((g) => ALL_GROUPS.has(g))
    }))
    .filter((r) => r.groups.length > 0 && r.groups.length < ALL_GROUPS.size)
    .sort((a, b) => a.groups.length - b.groups.length);

  if (limited.length) {
    const r = limited[0];
    parts.push(`${r.region} reports only ${r.groups.join(' + ')}`);
  }

  if (coverage.is_partial && coverage.as_of_date) {
    parts.push(`${coverage.scope} is year-to-date through ${coverage.as_of_date}`);
  }

  return parts.length
    ? parts.join(' · ')
    : 'Per-capita rates are windowed to a single reference year for comparability.';
}

export function CrimeGroupLegend({ year }: { year: number }): JSX.Element | null {
  const rateLayer = useLayerById(RATE_LAYER_ID);
  const coverage = useCoverage(year);

  const visible = Boolean(rateLayer?.config?.isVisible);
  if (!visible) return null;

  const fieldName: string | undefined = rateLayer?.config?.colorField?.name;
  const bucket = (fieldName && FIELD_TO_LABEL[fieldName]) || 'Total';
  const ramp: string[] = rateLayer?.config?.visConfig?.colorRange?.colors ?? [];

  return (
    <div
      style={{
        position: 'absolute',
        bottom: 28,
        right: 16,
        zIndex: 101, // above BivariateLegend's slot (they're mutually exclusive)
        background: 'rgba(41, 50, 60, 0.92)',
        color: '#e6e6e6',
        padding: '12px 14px',
        borderRadius: 6,
        fontFamily: 'ff-clan-web-pro, "Helvetica Neue", Helvetica, sans-serif',
        fontSize: 11,
        boxShadow: '0 2px 8px rgba(0, 0, 0, 0.4)',
        userSelect: 'none',
        pointerEvents: 'auto',
        maxWidth: 230
      }}
    >
      <div style={{ fontWeight: 600, marginBottom: 8 }}>
        {bucket === 'Total' ? 'Crime rate' : `${bucket} crime rate`} / 1,000
      </div>

      {/* Sequential ramp the choropleth is using (low → high). */}
      <div style={{ display: 'flex', height: 12, borderRadius: 2, overflow: 'hidden' }}>
        {ramp.map((c, i) => (
          <div key={i} style={{ flex: 1, background: c }} />
        ))}
      </div>
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
        <span>Higher</span>
      </div>

      <div style={{ marginTop: 10, fontSize: 9, lineHeight: 1.35, color: MUTED }}>
        {coverageCaveat(coverage)}
      </div>
    </div>
  );
}
