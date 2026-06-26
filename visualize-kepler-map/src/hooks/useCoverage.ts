// Fetches the per-year coverage.json so the crime-group legend can surface a
// data-driven caveat (which regions report what, and whether the year is YTD).
//
// Degrades quietly: in standalone mode coverage.json isn't embedded, and a
// fetch failure (missing file) simply yields null — the legend then shows a
// static fallback note instead of a data-driven one.

import * as React from 'react';

import { coverageUrlForYear } from '../data/loaders';
import { isStandalone } from '../data/standaloneLoader';

export interface RegionCoverage {
  min_date: string | null;
  max_date: string | null;
  n_incidents: number;
  categories_present: string[];
  groups_present: string[];
}

export interface Coverage {
  scope: string;
  n_incidents: number;
  regions: Record<string, RegionCoverage>;
  category_x_region: Record<string, Record<string, boolean>>;
  multiple_count: Record<string, number>;
  is_partial?: boolean;
  as_of_date?: string;
  fraction_elapsed?: number;
  same_period_prior_year_incidents?: number;
}

export function useCoverage(year: number): Coverage | null {
  const [coverage, setCoverage] = React.useState<Coverage | null>(null);

  React.useEffect(() => {
    // No coverage.json is embedded in the single-file standalone build.
    if (isStandalone()) {
      setCoverage(null);
      return;
    }

    let cancelled = false;
    setCoverage(null);
    (async () => {
      try {
        const res = await fetch(coverageUrlForYear(year));
        if (!res.ok) return;
        const data = (await res.json()) as Coverage;
        if (!cancelled) setCoverage(data);
      } catch {
        // Missing/unreachable coverage.json — legend falls back to a static note.
      }
    })();

    return () => {
      cancelled = true;
    };
  }, [year]);

  return coverage;
}
