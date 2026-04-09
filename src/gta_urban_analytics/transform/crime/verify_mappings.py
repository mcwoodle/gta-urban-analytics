"""
Verify that every original_crime_type in the unified data has an explicit
entry in crime_category_mappings.json.  Raises ValueError listing any
unmapped types so the mapping file can be updated before downstream steps.
"""

import json
import logging
from importlib import resources

import pandas as pd

logger = logging.getLogger(__name__)


def _load_mapping_keys() -> set[str]:
    ref = resources.files('gta_urban_analytics.transform.crime').joinpath('crime_category_mappings.json')
    with resources.as_file(ref) as path:
        with open(path, 'r') as f:
            return set(json.load(f).keys())


def verify_mappings(df: pd.DataFrame) -> None:
    """Check that every non-null original_crime_type has a mapping entry.

    Args:
        df: Unified DataFrame with an ``original_crime_type`` column.

    Raises:
        ValueError: If any crime types are missing from the mapping file.
    """
    mapping_keys = _load_mapping_keys()

    unique_types = set(
        df['original_crime_type']
        .dropna()
        .str.strip()
        .loc[lambda s: s.ne('')]
        .unique()
    )

    missing = sorted(unique_types - mapping_keys)

    if missing:
        RED = "\033[91m"
        RESET = "\033[0m"
        msg = (
            f"{len(missing)} original crime type(s) not found in "
            f"crime_category_mappings.json:\n"
            + "\n".join(f"  - {t}" for t in missing)
        )
        raise ValueError(f"{RED}{msg}{RESET}")

    logger.info(
        "All %d unique original crime types have explicit mappings.",
        len(unique_types),
    )
