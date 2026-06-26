# Cross-Region Normalization Strategy

> Authored 2026-06-26. Companion to the crime-type-buckets work. Explains how the
> pipeline makes five differently-shaped police feeds comparable, and where the
> comparison still needs caveats.

## The problem

The five GTA police services publish crime data on wildly different terms. The
date windows and category breadth are not comparable out of the box (figures from
the all-years `coverage.json`):

| Region  | Window (min → max)        | Incidents | Distinct categories |
|---------|---------------------------|-----------|---------------------|
| Toronto | 1964-09 → 2026-06         | 419,669   | 9                   |
| York    | 2021-01 → 2026-06         | 243,062   | 14                  |
| Peel    | 2023-06 → 2026-06         | 82,367    | 11                  |
| Durham  | 1982-01 → 2026-05         | 35,825    | 8                   |
| Halton  | 2025-06 → 2026-06         | 20,260    | 8                   |

A naive cross-region count therefore reflects *how much each service publishes*
far more than *how much crime occurs*. Two structural distortions dominate:

1. **Time spans differ.** Toronto's Major Crime Indicators reach back decades;
   Halton's feed starts ~2025-06. Summing raw counts compares a decade to a year.
2. **Category subsets differ.** Durham ships single-crime-type files and never
   reports Fraud, Sexual Offences, Public Order, Property Damage, Threats &
   Harassment, Impaired Driving, Homicide, or Missing Person. Toronto's MCI is a
   curated subset too. So a "Fraud" total is really "Fraud where it is reported."

## How the pipeline normalizes

### 1. Reference-year windowing (audit F-04)

The headline `crime_rate_per_1k` (and now every per-bucket rate) is computed over
a **single reference year, 2025** — the only full calendar year covered by all
five regions — rather than all-years counts over a single-year population. Per-year
partition folders keep their own single-year rates (`reference_year=None`).

### 2. Per-capita rates against census population

Counts are spatially joined to Statistics Canada Dissemination Areas and divided
by DA population (×1,000). DAs below 50 residents are nulled to avoid noisy
spikes. This is applied identically to the total and to each bucket, so the four
bucket counts sum to the DA total.

### 3. 15 → 4 crime-group buckets

To allow viewing crime by type without 15-way noise, the 15 canonical categories
collapse into 4 buckets (`crime_group`, in `crime_groups.py`):

| Bucket   | Categories |
|----------|------------|
| Violent  | Assault, Sexual Offences, Robbery, Homicide, Threats & Harassment, Weapons Offences |
| Property | Break & Enter, Theft, Auto Theft, Fraud, Property Damage |
| Nuisance | Public Order, Drug Offences, Impaired Driving & Traffic |
| Other    | Missing Person (+ runtime `MULTIPLE` and any unmapped `Other`) |

**Judgment calls** (intentional, documented here and in code):

- **Weapons Offences → Violent.** A firearm/weapon offence is treated as an
  indicator of interpersonal violence, not property or nuisance.
- **Impaired Driving & Traffic → Nuisance.** Regulatory / public-order in
  character rather than an offence against a specific victim's person or property.
- **MULTIPLE → Other.** The dedup step overwrites a multi-offence incident's
  category to `MULTIPLE`; it cannot be assigned to one bucket, so it falls to
  Other. This under-counts Violent/Property for multi-offence incidents — the
  per-region `MULTIPLE` count is therefore surfaced in `coverage.json` (Toronto
  28,567; Durham 918; others 0) so the folding stays auditable. A
  precedence-mapping alternative (assign the "most serious" offence) was
  considered and deferred.

### 4. Coverage metadata (`coverage.json`)

The binning and rates above don't *erase* the structural gaps — they just make
them comparable where data exists. `build_coverage_metadata.py` records the gaps
explicitly so they can never be silently misread:

- per-region date window, incident count, and which categories/groups appear;
- a `category_x_region` boolean matrix (the Durham/Toronto-MCI subset gaps);
- per-region `MULTIPLE` counts (audits the Other-bucket folding);
- per-year: `is_partial`, `fraction_elapsed`, and a **same-period-prior-year**
  count.

The viz's `CrimeGroupLegend` reads this file and renders a caveat alongside any
bucket rate (R2 — a per-capita bucket rate is structurally low for a region that
never reports that category, so it must never be shown bare).

## 2026 is year-to-date

2026 partitions are partial (`is_partial: true`). We deliberately do **not**
annualize (×365/N): crime is seasonal, so a linear projection from a half-year
would mislead. Instead the current year is reported as raw YTD plus a
**same-period-prior-year** comparison — the prior year's incidents from Jan 1
through the same month/day as the as-of date — which is the honest like-for-like.

## Open items

- Precedence mapping for `MULTIPLE` (recover bucket signal from multi-offence
  incidents) instead of folding all to Other.
- Embedding `coverage.json` into the standalone HTML build so its legend caveat
  is data-driven there too (currently a static fallback).
