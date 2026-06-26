// Crime-group bucket metadata for the viz (mirrors the Python source of truth
// in src/gta_urban_analytics/transform/crime/crime_groups.py). The pipeline does
// ALL bucketing; this just maps each bucket's display name to the slug used in
// the per-bucket census column names (crime_rate_<slug>_per_1k / crime_count_<slug>)
// and pairs it with the colour the legend/scatter use.

import { CRIME_GROUP_COLORS } from './visualization';

/** Bucket display name → column slug. */
export const GROUP_SLUGS = {
  Violent: 'violent',
  Property: 'property',
  Nuisance: 'nuisance',
  Other: 'other'
} as const;

export type CrimeGroup = keyof typeof GROUP_SLUGS;

/** Bucket → its colour. CRIME_GROUP_COLORS is ordered to Kepler's ALPHABETICAL
 *  ordinal sort of the `crime_group` domain (Nuisance, Other, Property, Violent),
 *  so index into it by that sorted position — keep this in lockstep with the
 *  palette comment in visualization.ts. */
const ALPHABETICAL_DOMAIN: CrimeGroup[] = ['Nuisance', 'Other', 'Property', 'Violent'];

export const GROUP_COLOR: Record<CrimeGroup, string> = ALPHABETICAL_DOMAIN.reduce(
  (acc, group, i) => {
    acc[group] = CRIME_GROUP_COLORS.colors[i];
    return acc;
  },
  {} as Record<CrimeGroup, string>
);
