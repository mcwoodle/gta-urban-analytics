"""
Transform Pipeline
==================
Runs the full sequence of data transformations:

  1. Unify     — merge all regional CSVs into 01_unified.csv
  2. Filter    — validate schema, separate invalid rows → 02_unified_valid.csv
  3. Deduplicate — merge multi-offence rows → 03_unified_valid_deduplicated.csv
"""

import logging

logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')
logger = logging.getLogger(__name__)


def run():
    """Execute the full transform pipeline in order."""
    from gta_crime_data.transform.unify_datasets import run as unify
    from gta_crime_data.transform.filter_invalid_incidents import run as filter_invalid
    from gta_crime_data.transform.deduplicate_incidents import run as deduplicate

    logger.info("=" * 60)
    logger.info("Step 1/3: Unifying regional datasets → 01_unified.csv")
    logger.info("=" * 60)
    unify()

    logger.info("")
    logger.info("=" * 60)
    logger.info("Step 2/3: Filtering invalid rows → 02_unified_valid.csv")
    logger.info("=" * 60)
    filter_invalid()

    logger.info("")
    logger.info("=" * 60)
    logger.info("Step 3/3: Deduplicating → 03_unified_valid_deduplicated.csv")
    logger.info("=" * 60)
    deduplicate()

    logger.info("")
    logger.info("=" * 60)
    logger.info("Transform pipeline complete.")
    logger.info("=" * 60)


if __name__ == "__main__":
    run()
