"""
Transform Pipeline
==================
Runs the full sequence of data transformations in memory:

  1. Unify                — merge all regional CSVs into a single DataFrame
  2. Filter               — validate schema, separate invalid rows
  3. Deduplicate          — merge multi-offence rows → unified_data.csv
  4. Census               — build GTA census GeoJSON from StatCan data
  5. Enrich census        — spatial-join crimes → DAs, add crime_count + crime_rate_per_1k
  6. Shooting arcs        — build shooting_arcs.csv (Kepler arc layer input)
  7. Standalone compact   — slim variants for the embedded single-file HTML build
  8. Partition by year    — per-year subfolders (2020–present) with all outputs

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

logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')
logger = logging.getLogger(__name__)

# Resolve paths relative to the project root (3 levels up from this file)
_project_root = os.path.normpath(os.path.join(os.path.dirname(__file__), '..', '..', '..'))

VERBOSE = True

def run():
    """Execute the full transform pipeline in memory, writing a single output CSV."""
    from gta_urban_analytics.transform.crime.unify_datasets import unify_datasets
    from gta_urban_analytics.transform.crime.filter_invalid_incidents import filter_invalid_incidents
    from gta_urban_analytics.transform.crime.deduplicate_incidents import deduplicate_incidents
    from gta_urban_analytics.transform.crime.build_shooting_arcs import build_shooting_arcs
    from gta_urban_analytics.transform.census.build_gta_census import build_gta_census_geojson
    from gta_urban_analytics.transform.census.enrich_with_crime_rate import enrich_census_with_crime_rate
    from gta_urban_analytics.transform.build_standalone_compact import build_standalone_compact
    from gta_urban_analytics.transform.partition_by_year import partition_all_years

    # Step 1: Unify
    logger.info("=" * 60)
    logger.info("Step 1/8: Unifying regional datasets")
    logger.info("=" * 60)
    df = unify_datasets()

    if df.empty:
        logger.error("No data to process. Aborting pipeline.")
        return

    # Step 2: Filter invalid rows
    logger.info("")
    logger.info("=" * 60)
    logger.info("Step 2/8: Filtering invalid rows")
    logger.info("=" * 60)
    df = filter_invalid_incidents(df, verbose=VERBOSE)

    # Step 3: Deduplicate
    logger.info("")
    logger.info("=" * 60)
    logger.info("Step 3/8: Deduplicating incidents")
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

    # Step 4: Build census GeoJSON
    logger.info("")
    logger.info("=" * 60)
    logger.info("Step 4/8: Building GTA census GeoJSON")
    logger.info("=" * 60)
    build_gta_census_geojson()

    # Step 5: Enrich census with per-DA crime rate
    logger.info("")
    logger.info("=" * 60)
    logger.info("Step 5/8: Enriching census DAs with crime rate")
    logger.info("=" * 60)
    enrich_census_with_crime_rate(verbose=VERBOSE)

    # Step 6: Build shooting arcs
    logger.info("")
    logger.info("=" * 60)
    logger.info("Step 6/8: Building shooting arcs")
    logger.info("=" * 60)
    build_shooting_arcs(verbose=VERBOSE)

    # Step 7: Produce compact variants for the standalone HTML build
    logger.info("")
    logger.info("=" * 60)
    logger.info("Step 7/8: Building standalone compact variants")
    logger.info("=" * 60)
    build_standalone_compact(verbose=VERBOSE)

    # Step 8: Partition by year
    logger.info("")
    logger.info("=" * 60)
    logger.info("Step 8/8: Partitioning outputs by year (2020–present)")
    logger.info("=" * 60)
    partition_all_years(verbose=VERBOSE)

    logger.info("Transform pipeline complete.")


if __name__ == "__main__":
    run()

