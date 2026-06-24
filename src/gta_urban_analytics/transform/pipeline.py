"""
Transform Pipeline
==================
Two explicit phases (audit F-17 — the data flow is now honest):

  Phase 1 — in-memory transform (``TRANSFORM_STEPS``): unify → verify → filter →
  deduplicate. A single working DataFrame is threaded through these steps and then
  written once to ``data/02_transformed/unified_data.csv``. That CSV is the
  hand-off to phase 2.

  Phase 2 — derived products (``DERIVED_STEPS``): census, crime-rate enrichment,
  shooting arcs, coordinate anomalies, standalone-compact variants, and per-year
  partitions. Each reads what it needs from disk (the unified CSV and/or the census
  GeoJSON written by earlier steps) and writes its own output(s) — they do NOT take
  the in-memory frame.

Note: phase 2 counts post-dedup *incidents* (a multi-offence occurrence is one
row), not individual offences — so e.g. ``crime_rate_per_1k`` is incidents per
1,000 residents.

Outputs:
  - data/02_transformed/unified_data.csv
  - data/02_transformed/gta_census_da.geojson   (enriched with crime_count + crime_rate_per_1k)
  - data/02_transformed/shooting_arcs.csv
  - data/02_transformed/coordinate_anomalies.csv
  - data/02_transformed/standalone/unified_data_compact.csv
  - data/02_transformed/standalone/gta_census_da_compact.geojson
  - data/02_transformed/standalone/shooting_arcs.csv
  - data/02_transformed/<year>/unified_data.csv
  - data/02_transformed/<year>/gta_census_da.geojson
  - data/02_transformed/<year>/shooting_arcs.csv
  - data/02_transformed/<year>/standalone/...
"""

import os
import logging

from gta_urban_analytics.transform.crime.unify_datasets import unify_datasets
from gta_urban_analytics.transform.crime.verify_mappings import verify_mappings
from gta_urban_analytics.transform.crime.filter_invalid_incidents import filter_invalid_incidents
from gta_urban_analytics.transform.crime.deduplicate_incidents import deduplicate_incidents
from gta_urban_analytics.transform.crime.build_shooting_arcs import build_shooting_arcs
from gta_urban_analytics.transform.crime.build_coordinate_anomalies import build_coordinate_anomalies
from gta_urban_analytics.transform.census.build_gta_census import build_gta_census_geojson
from gta_urban_analytics.transform.census.enrich_with_crime_rate import enrich_census_with_crime_rate, REFERENCE_YEAR
from gta_urban_analytics.transform.build_standalone_compact import build_standalone_compact
from gta_urban_analytics.transform.partition_by_year import partition_all_years

logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')
logger = logging.getLogger(__name__)

# Resolve paths relative to the project root (3 levels up from this file)
_project_root = os.path.normpath(os.path.join(os.path.dirname(__file__), '..', '..', '..'))

VERBOSE = True


def _verify_and_pass(df):
    """verify_mappings is a check (returns None); keep the frame flowing."""
    verify_mappings(df)
    return df


# ── Phase 1: in-memory transform ──────────────────────────────────────────
# Each callable receives and returns the working DataFrame.
TRANSFORM_STEPS = [
    ("Unifying regional datasets",      lambda _df: unify_datasets()),
    ("Verifying crime type mappings",   _verify_and_pass),
    ("Filtering invalid rows",          lambda df: filter_invalid_incidents(df, verbose=VERBOSE)),
    ("Deduplicating incidents",         lambda df: deduplicate_incidents(df, verbose=VERBOSE)),
]

# ── Phase 2: derived products ─────────────────────────────────────────────
# Each callable reads the written unified_data.csv / census GeoJSON from disk and
# writes its own output(s). None of them take the in-memory frame.
DERIVED_STEPS = [
    ("Building GTA census GeoJSON",                 lambda: build_gta_census_geojson(verbose=VERBOSE)),
    ("Enriching census DAs with crime rate",        lambda: enrich_census_with_crime_rate(reference_year=REFERENCE_YEAR, verbose=VERBOSE)),
    ("Building shooting arcs",                      lambda: build_shooting_arcs(verbose=VERBOSE)),
    ("Flagging coordinate anomalies",               lambda: build_coordinate_anomalies(verbose=VERBOSE)),
    ("Building standalone compact variants",        lambda: build_standalone_compact(verbose=VERBOSE)),
    ("Partitioning outputs by year (2020–present)", lambda: partition_all_years(verbose=VERBOSE)),
]


def _log_step(step_num, total, description, *, first=False):
    """Log a step banner matching the existing output format."""
    if not first:
        logger.info("")
    logger.info("=" * 60)
    logger.info(f"Step {step_num}/{total}: {description}")
    logger.info("=" * 60)


def _write_unified(df):
    """Persist the unified table — the hand-off from phase 1 to phase 2."""
    output_dir = os.path.join(_project_root, 'data', '02_transformed')
    os.makedirs(output_dir, exist_ok=True)
    output_file = os.path.join(output_dir, 'unified_data.csv')
    logger.info("")
    logger.info("=" * 60)
    logger.info(f"Writing {len(df):,} rows to {output_file}")
    logger.info("=" * 60)
    df.to_csv(output_file, index=False)


def run():
    """Build the unified incident table (phase 1), then the derived products (phase 2)."""
    total = len(TRANSFORM_STEPS) + len(DERIVED_STEPS)

    # ── Phase 1: in-memory transform → unified_data.csv ──
    df = None
    for i, (description, action) in enumerate(TRANSFORM_STEPS, start=1):
        _log_step(i, total, description, first=(i == 1))
        df = action(df)

        if i == 1 and df.empty:
            logger.error("No data to process. Aborting pipeline.")
            return

    _write_unified(df)

    # ── Phase 2: derived products (each reads the written files from disk) ──
    for j, (description, action) in enumerate(DERIVED_STEPS, start=len(TRANSFORM_STEPS) + 1):
        _log_step(j, total, description)
        action()

    logger.info("Transform pipeline complete.")


if __name__ == "__main__":
    run()
