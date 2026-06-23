"""
Transform Pipeline
==================
Runs the full sequence of data transformations in memory (see PIPELINE_STEPS below).

Outputs:
  - data/02_transformed/unified_data.csv
  - data/02_transformed/gta_census_da.geojson   (enriched with crime_count + crime_rate_per_1k)
  - data/02_transformed/shooting_arcs.csv
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
from gta_urban_analytics.transform.census.build_gta_census import build_gta_census_geojson
from gta_urban_analytics.transform.census.enrich_with_crime_rate import enrich_census_with_crime_rate
from gta_urban_analytics.transform.build_standalone_compact import build_standalone_compact
from gta_urban_analytics.transform.partition_by_year import partition_all_years

logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')
logger = logging.getLogger(__name__)

# Resolve paths relative to the project root (3 levels up from this file)
_project_root = os.path.normpath(os.path.join(os.path.dirname(__file__), '..', '..', '..'))

VERBOSE = True

# ── Pipeline steps ────────────────────────────────────────────────────────
# Each entry is (description, callable). Callables receive and return the
# current DataFrame — steps that don't transform it return it unchanged.
PIPELINE_STEPS = [
    ("Unifying regional datasets",                  lambda _df: unify_datasets()),
    ("Verifying crime type mappings",               lambda df: (verify_mappings(df), df)[1]),
    ("Filtering invalid rows",                      lambda df: filter_invalid_incidents(df, verbose=VERBOSE)),
    ("Deduplicating incidents",                     lambda df: deduplicate_incidents(df, verbose=VERBOSE)),
    ("Building GTA census GeoJSON",                 lambda df: (build_gta_census_geojson(), df)[1]),
    ("Enriching census DAs with crime rate",        lambda df: (enrich_census_with_crime_rate(verbose=VERBOSE), df)[1]),
    ("Building shooting arcs",                      lambda df: (build_shooting_arcs(verbose=VERBOSE), df)[1]),
    ("Building standalone compact variants",        lambda df: (build_standalone_compact(verbose=VERBOSE), df)[1]),
    ("Partitioning outputs by year (2020–present)", lambda df: (partition_all_years(verbose=VERBOSE), df)[1]),
]


def _log_step(step_num, total, description, *, first=False):
    """Log a step banner matching the existing output format."""
    if not first:
        logger.info("")
    logger.info("=" * 60)
    logger.info(f"Step {step_num}/{total}: {description}")
    logger.info("=" * 60)


def run():
    """Execute the full transform pipeline in memory, writing a single output CSV."""
    total = len(PIPELINE_STEPS)
    df = None
    write_csv_after_step = 4  # write unified CSV between Deduplicate and Census

    for i, (description, action) in enumerate(PIPELINE_STEPS, start=1):
        _log_step(i, total, description, first=(i == 1))
        df = action(df)

        if i == 1 and df.empty:
            logger.error("No data to process. Aborting pipeline.")
            return

        if i == write_csv_after_step:
            output_dir = os.path.join(_project_root, 'data', '02_transformed')
            os.makedirs(output_dir, exist_ok=True)
            output_file = os.path.join(output_dir, 'unified_data.csv')
            logger.info("")
            logger.info("=" * 60)
            logger.info(f"Writing {len(df):,} rows to {output_file}")
            logger.info("=" * 60)
            df.to_csv(output_file, index=False)

    logger.info("Transform pipeline complete.")


if __name__ == "__main__":
    run()
