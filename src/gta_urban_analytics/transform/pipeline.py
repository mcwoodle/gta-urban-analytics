"""
Transform Pipeline
==================
Runs the full sequence of data transformations in memory:

  1. Unify       — merge all regional CSVs into a single DataFrame
  2. Verify      — ensure every original crime type has an explicit mapping
  3. Filter      — validate schema, separate invalid rows
  4. Deduplicate — merge multi-offence rows
  5. Census      — build GTA census GeoJSON from StatCan data

Outputs:
  - data/02_transformed/unified_data.csv
  - data/02_transformed/gta_census_da.geojson
"""

import os
import logging

logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')
logger = logging.getLogger(__name__)

# Resolve paths relative to the project root (3 levels up from this file)
_project_root = os.path.normpath(os.path.join(os.path.dirname(__file__), '..', '..', '..'))

VERBOSE = True

def run():
    """Execute the full transform pipeline in memory, writing a single output CSV."""
    from gta_urban_analytics.transform.crime.unify_datasets import unify_datasets
    from gta_urban_analytics.transform.crime.verify_mappings import verify_mappings
    from gta_urban_analytics.transform.crime.filter_invalid_incidents import filter_invalid_incidents
    from gta_urban_analytics.transform.crime.deduplicate_incidents import deduplicate_incidents
    from gta_urban_analytics.transform.census.build_gta_census import build_gta_census_geojson

    # Step 1: Unify
    logger.info("=" * 60)
    logger.info("Step 1/5: Unifying regional datasets")
    logger.info("=" * 60)
    df = unify_datasets()

    if df.empty:
        logger.error("No data to process. Aborting pipeline.")
        return

    # Step 2: Verify all crime types have explicit mappings
    logger.info("")
    logger.info("=" * 60)
    logger.info("Step 2/5: Verifying crime type mappings")
    logger.info("=" * 60)
    verify_mappings(df)

    # Step 3: Filter invalid rows
    logger.info("")
    logger.info("=" * 60)
    logger.info("Step 3/5: Filtering invalid rows")
    logger.info("=" * 60)
    df = filter_invalid_incidents(df, verbose=VERBOSE)

    # Step 4: Deduplicate
    logger.info("")
    logger.info("=" * 60)
    logger.info("Step 4/5: Deduplicating incidents")
    logger.info("=" * 60)
    df = deduplicate_incidents(df, verbose=VERBOSE)

    # Write final output
    output_dir = os.path.join(_project_root, 'data', '02_transformed')
    os.makedirs(output_dir, exist_ok=True)
    output_file = os.path.join(output_dir, 'unified_data.csv')

    logger.info("")
    logger.info("=" * 60)
    logger.info(f"Writing {len(df):,} rows to {output_file}")
    logger.info("=" * 60)
    df.to_csv(output_file, index=False)

    # Step 5: Build census GeoJSON
    logger.info("")
    logger.info("=" * 60)
    logger.info("Step 5/5: Building GTA census GeoJSON")
    logger.info("=" * 60)
    build_gta_census_geojson()

    logger.info("Transform pipeline complete.")


if __name__ == "__main__":
    run()
