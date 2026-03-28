import pandas as pd
import logging
import os
import pandera.errors as pa_errors
from gta_crime_data.schemas import unified_schema

logger = logging.getLogger(__name__)

logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')

# Resolve paths relative to the project root (3 levels up from this file)
_project_root = os.path.normpath(os.path.join(os.path.dirname(__file__), '..', '..', '..'))


def filter_invalid_incidents(df: pd.DataFrame, verbose: bool = True) -> pd.DataFrame:
    """
    Validates a unified DataFrame against the unified_schema.
    
    Returns only the valid rows. Invalid rows are saved to a separate CSV
    with a 'validation_errors' column explaining why they were rejected.
    """
    try:
        unified_schema.validate(df, lazy=True)
        if verbose:
            logger.info("All rows passed schema validation.")
        return df.copy()
    except pa_errors.SchemaErrors as err:
        # Build a per-row summary of why each row is invalid
        cases = err.failure_cases.copy()
        cases['reason'] = cases['check'].astype(str) + ' on [' + cases['column'].astype(str) + ']'
        reasons = cases.groupby('index')['reason'].apply(lambda r: '; '.join(r))
        
        invalid_indices = reasons.index
        
        # Separate invalid and valid data
        invalid_df = df.loc[invalid_indices].copy()
        invalid_df['validation_errors'] = reasons.values
        valid_df = df.drop(index=invalid_indices)
        
        # Save invalid rows for inspection
        invalid_path = os.path.join(_project_root, 'data', '02_transformed', '02_invalid.csv')
        invalid_df.to_csv(invalid_path, index=False)
        
        if verbose:
            logger.info(f"Found {len(err.failure_cases)} validation errors affecting {len(invalid_indices):,} rows.")
            logger.info(f"  Valid rows:   {len(valid_df):,}")
            logger.info(f"  Invalid rows: {len(invalid_df):,} (saved to {invalid_path})")
            logger.info("\nReasons breakdown:")
            logger.info("\n" + cases['reason'].value_counts().to_string())
        
        return valid_df


def run():
    """Run filtering as a standalone step: reads 01_unified.csv, writes 02_unified_valid.csv."""
    input_file = os.path.join(_project_root, 'data', '02_transformed', '01_unified.csv')
    output_file = os.path.join(_project_root, 'data', '02_transformed', '02_unified_valid.csv')

    if not os.path.exists(input_file):
        logger.error(f"Input file not found: {input_file}")
        return

    logger.info(f"Loading data from {input_file}...")
    df = pd.read_csv(input_file, low_memory=False)

    logger.info("Filtering invalid incidents...")
    valid_df = filter_invalid_incidents(df, verbose=True)

    logger.info(f"Saving valid data to {output_file}...")
    valid_df.to_csv(output_file, index=False)
    logger.info("Done.")


if __name__ == "__main__":
    run()
