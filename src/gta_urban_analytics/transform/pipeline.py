"""
Transform Pipeline
==================
Runs the full sequence of data transformations in memory:

  1. Unify                — merge all regional CSVs into a single DataFrame
  2. Verify              — ensure every original crime type has an explicit mapping
  3. Filter               — validate schema, separate invalid rows
  4. Deduplicate          — merge multi-offence rows → unified_data.csv
  5. Census               — build GTA census GeoJSON from StatCan data
  6. Enrich census        — spatial-join crimes → DAs, add crime_count + crime_rate_per_1k
  7. Shooting arcs        — build shooting_arcs.csv (Kepler arc layer input)
  8. Standalone compact   — slim variants for the embedded single-file HTML build
  9. Partition by year    — per-year subfolders (2020–present) with all outputs

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
    from gta_urban_analytics.transform.crime.verify_mappings import verify_mappings
    from gta_urban_analytics.transform.crime.filter_invalid_incidents import filter_invalid_incidents
    from gta_urban_analytics.transform.crime.deduplicate_incidents import deduplicate_incidents
    from gta_urban_analytics.transform.crime.build_shooting_arcs import build_shooting_arcs
    from gta_urban_analytics.transform.census.build_gta_census import build_gta_census_geojson
    from gta_urban_analytics.transform.census.enrich_with_crime_rate import enrich_census_with_crime_rate
    from gta_urban_analytics.transform.build_standalone_compact import build_standalone_compact
    from gta_urban_analytics.transform.partition_by_year import partition_all_years

    def run_unify(df):
        return unify_datasets()

    def run_verify(df):
        verify_mappings(df)
        return df

    def run_filter(df):
        return filter_invalid_incidents(df, verbose=VERBOSE)

    def run_dedup(df):
        return deduplicate_incidents(df, verbose=VERBOSE)

    def run_write(df):
        output_dir = os.path.join(_project_root, 'data', '02_transformed')
        os.makedirs(output_dir, exist_ok=True)
        output_file = os.path.join(output_dir, 'unified_data.csv')

        logger.info("")
        logger.info("=" * 60)
        logger.info(f"Writing {len(df):,} rows to {output_file}")
        logger.info("=" * 60)
        df.to_csv(output_file, index=False)
        return df

    def run_census(df):
        build_gta_census_geojson()
        return df

    def run_enrich(df):
        enrich_census_with_crime_rate(verbose=VERBOSE)
        return df

    def run_arcs(df):
        build_shooting_arcs(verbose=VERBOSE)
        return df

    def run_compact(df):
        build_standalone_compact(verbose=VERBOSE)
        return df

    def run_partition(df):
        partition_all_years(verbose=VERBOSE)
        return df

    pipeline_steps = [
        ("Unifying regional datasets", run_unify),
        ("Verifying crime type mappings", run_verify),
        ("Filtering invalid rows", run_filter),
        ("Deduplicating incidents", run_dedup),
        (None, run_write),
        ("Building GTA census GeoJSON", run_census),
        ("Enriching census DAs with crime rate", run_enrich),
        ("Building shooting arcs", run_arcs),
        ("Building standalone compact variants", run_compact),
        ("Partitioning outputs by year (2020–present)", run_partition),
    ]

    df = None
    numbered_steps = [s for s in pipeline_steps if s[0] is not None]
    total_steps = len(numbered_steps)
    current_step = 1

    for desc, step_func in pipeline_steps:
        if desc is not None:
            if current_step > 1:
                logger.info("")
            logger.info("=" * 60)
            logger.info(f"Step {current_step}/{total_steps}: {desc}")
            logger.info("=" * 60)
            current_step += 1

        df = step_func(df)

        if desc == "Unifying regional datasets" and (df is None or df.empty):
            logger.error("No data to process. Aborting pipeline.")
            return

    logger.info("Transform pipeline complete.")


if __name__ == "__main__":
    run()
