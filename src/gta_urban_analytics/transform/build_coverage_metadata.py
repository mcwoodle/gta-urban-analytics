"""
Coverage Metadata Builder
=========================
Crime data from five regions can't be naively compared: the regions cover wildly
different time spans (Toronto from ~2014, Halton only ~2025-06 onward) and
publish different *subsets* of crime (Durham ships only single-crime-type files,
so it never reports Fraud, Sexual Offences, Public Order, …). The current year is
also year-to-date. Nothing recorded these gaps, so a naive cross-region count
misleads.

This step writes a ``coverage.json`` alongside the transformed data describing,
per region:

  - the date window actually covered (``min_date`` / ``max_date``),
  - how many incidents are present,
  - which canonical categories and which crime-group buckets appear, and
  - a ``category_x_region`` boolean matrix that makes the subset gaps explicit.

It also reports a per-region ``MULTIPLE`` count so the ``MULTIPLE → Other``
bucket folding (see ``crime_groups.py``) stays auditable.

When called with a ``year``, the payload is restricted to that year and gains a
partial-year block: ``is_partial`` (true for the current calendar year),
``fraction_elapsed``, and a ``same_period_prior_year`` count (the prior year's
incidents within Jan 1 → the same month/day as ``as_of_date``). No annualized
projection is produced — ×365/N would ignore crime seasonality and mislead.
"""

from __future__ import annotations

import datetime
import json
import os
import logging

import pandas as pd

from gta_urban_analytics.transform.crime.crime_groups import CATEGORY_TO_GROUP

logger = logging.getLogger(__name__)

_project_root = os.path.normpath(
    os.path.join(os.path.dirname(__file__), "..", "..", "..")
)

# The 15 canonical categories, sorted — the columns of the coverage matrix.
_CANONICAL_CATEGORIES = sorted(CATEGORY_TO_GROUP.keys())


def _region_summaries(df: pd.DataFrame) -> dict:
    """Per-region date window, incident count, and categories/groups present."""
    has_group = "crime_group" in df.columns
    summaries: dict[str, dict] = {}
    for region, g in df.groupby("region"):
        dates = g["occurrence_date"].dropna()
        summaries[str(region)] = {
            "min_date": dates.min().date().isoformat() if not dates.empty else None,
            "max_date": dates.max().date().isoformat() if not dates.empty else None,
            "n_incidents": int(len(g)),
            "categories_present": sorted(
                str(c) for c in g["mapped_crime_category"].dropna().unique()
            ),
            "groups_present": sorted(
                str(x) for x in g["crime_group"].dropna().unique()
            )
            if has_group
            else [],
        }
    return summaries


def _category_x_region(df: pd.DataFrame) -> dict:
    """Boolean matrix region → {canonical_category: present?}. Makes the Durham /
    Toronto-MCI subset gaps explicit (a region simply never reports some types)."""
    matrix: dict[str, dict] = {}
    for region, g in df.groupby("region"):
        present = set(str(c) for c in g["mapped_crime_category"].dropna().unique())
        matrix[str(region)] = {cat: (cat in present) for cat in _CANONICAL_CATEGORIES}
    return matrix


def _multiple_counts(df: pd.DataFrame) -> dict:
    """Per-region count of incidents folded to MULTIPLE (→ Other bucket)."""
    is_multi = df["mapped_crime_category"] == "MULTIPLE"
    return {
        str(region): int(is_multi[df["region"] == region].sum())
        for region in df["region"].dropna().unique()
    }


def _safe_date(year: int, month: int, day: int) -> datetime.date:
    """Build a date, clamping an invalid day (e.g. Feb 29 in a non-leap prior
    year) back to that month's last valid day."""
    while day > 28:
        try:
            return datetime.date(year, month, day)
        except ValueError:
            day -= 1
    return datetime.date(year, month, day)


def _year_block(all_years: pd.DataFrame, year: int) -> dict:
    """Partial-year honesty block: elapsed fraction + same-period-prior-year.

    ``all_years`` is the full (unrestricted) frame so the prior-year comparison
    window can be computed even when the caller passed only the current year's
    rows for the rest of the payload.
    """
    today = datetime.datetime.now().date()
    is_partial = year == today.year
    as_of = today if is_partial else datetime.date(year, 12, 31)

    start = datetime.date(year, 1, 1)
    year_end = datetime.date(year, 12, 31)
    days_in_year = (year_end - start).days + 1
    days_elapsed = (as_of - start).days + 1
    fraction_elapsed = days_elapsed / days_in_year

    # Same-period-prior-year: prior year's incidents from Jan 1 through the same
    # month/day as as_of (no seasonality-distorting annualization).
    prior = year - 1
    prior_start = datetime.date(prior, 1, 1)
    prior_end = _safe_date(prior, as_of.month, as_of.day)
    dates = all_years["occurrence_date"]
    in_window = (dates.dt.date >= prior_start) & (dates.dt.date <= prior_end)
    sppy = int(in_window.sum())

    return {
        "year": year,
        "as_of_date": as_of.isoformat(),
        "is_partial": is_partial,
        "days_elapsed": days_elapsed,
        "days_in_year": days_in_year,
        "fraction_elapsed": round(fraction_elapsed, 4),
        "same_period_prior_year_incidents": sppy,
    }


def build_coverage_metadata(
    crime_df: pd.DataFrame | None = None,
    year: int | None = None,
    output_dir: str | None = None,
    verbose: bool = True,
) -> dict:
    """Write ``coverage.json`` describing regional/temporal coverage gaps.

    Parameters:
        crime_df:   Pre-loaded unified frame (all years). When *None* the full
                    ``unified_data.csv`` is read. When ``year`` is set, pass the
                    all-years frame so the prior-year comparison works.
        year:       Restrict the summary to a single year and add a partial-year
                    block. When *None* the summary covers all years.
        output_dir: Directory to write ``coverage.json`` into. Defaults to
                    ``data/02_transformed/``.

    Returns:
        The payload dict (also written to disk).
    """
    if output_dir is None:
        output_dir = os.path.join(_project_root, "data", "02_transformed")

    if crime_df is None:
        crime_csv = os.path.join(
            _project_root, "data", "02_transformed", "unified_data.csv"
        )
        if not os.path.exists(crime_csv):
            raise FileNotFoundError(
                f"Missing {crime_csv}. Run the transform pipeline first."
            )
        df = pd.read_csv(crime_csv, low_memory=False)
    else:
        df = crime_df.copy()

    df["occurrence_date"] = pd.to_datetime(df["occurrence_date"], errors="coerce")
    all_years = df

    scope = df if year is None else df[df["occurrence_date"].dt.year == year]

    payload: dict = {
        "generated_at": datetime.datetime.now().isoformat(timespec="seconds"),
        "scope": "all_years" if year is None else str(year),
        "n_incidents": int(len(scope)),
        "regions": _region_summaries(scope),
        "category_x_region": _category_x_region(scope),
        "multiple_count": _multiple_counts(scope),
    }

    if year is not None:
        payload.update(_year_block(all_years, year))

    os.makedirs(output_dir, exist_ok=True)
    out_path = os.path.join(output_dir, "coverage.json")
    with open(out_path, "w") as f:
        json.dump(payload, f, indent=2, default=str)

    if verbose:
        scope_label = "all years" if year is None else str(year)
        partial = " (partial/YTD)" if payload.get("is_partial") else ""
        logger.info(
            f"Wrote coverage.json for {scope_label}{partial}: "
            f"{payload['n_incidents']:,} incidents across "
            f"{len(payload['regions'])} regions → {out_path}"
        )

    return payload


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
    build_coverage_metadata()
