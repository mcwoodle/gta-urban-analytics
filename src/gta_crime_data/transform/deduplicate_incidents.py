import pandas as pd
import logging
import os

logger = logging.getLogger(__name__)

logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')

def deduplicate_incidents(df: pd.DataFrame, verbose: bool = True) -> pd.DataFrame:
    """
    De-duplicates crime records by source_identifier.
    
    If multiple distinct crime types exist for the same incident (source_identifier), 
    they are merged into a single concatenated string in the 'original_crime_type' 
    column (using ' && ') and the 'mapped_crime_category' is set to 'MULTIPLE'.
    """
    before = len(df)

    # 1. Drop duplicates for all non-crime columns
    # We keep the first row for each source_identifier as the base record
    df_deduped = df.drop_duplicates(subset='source_identifier', keep='first').copy()

    # 2. Extract valid crimes and find distinct (source_id, crime_type) pairs
    # This ignores rows where the crime type is missing
    valid_crimes = df.dropna(subset=['original_crime_type'])
    distinct_crimes = valid_crimes.drop_duplicates(subset=['source_identifier', 'original_crime_type']).copy()

    # 3. Identify and isolate source_identifiers that have multiple distinct crimes
    crime_counts = distinct_crimes['source_identifier'].value_counts()
    multi_ids = crime_counts[crime_counts > 1].index

    if not multi_ids.empty:
        # Group and aggregate ONLY the multi-crime rows (typically a small percentage of the dataset)
        multi_crimes = distinct_crimes[distinct_crimes['source_identifier'].isin(multi_ids)].copy()
        multi_crimes = multi_crimes.sort_values(by=['source_identifier', 'original_crime_type'])
        
        # Concatenate multiple crime descriptions (e.g., "Assault && Robbery")
        agg_crimes = multi_crimes.groupby('source_identifier')['original_crime_type'].agg(' && '.join).reset_index()
        
        # Set mapped category to 'MULTIPLE' for these entries in the deduped dataframe
        df_deduped.loc[df_deduped['source_identifier'].isin(multi_ids), 'mapped_crime_category'] = 'MULTIPLE'
        
        # Merge the concatenated strings back into the base records
        df_deduped = df_deduped.merge(agg_crimes, on='source_identifier', how='left', suffixes=('_old', ''))
        
        # Overwrite the original_crime_type column where aggregation occurred
        df_deduped['original_crime_type'] = df_deduped['original_crime_type'].fillna(df_deduped['original_crime_type_old'])
        df_deduped = df_deduped.drop(columns=['original_crime_type_old'])

    if verbose:
        multi_count = df_deduped['mapped_crime_category'].eq('MULTIPLE').sum()
        logger.info(f"Deduplication report:")
        logger.info(f"  Rows before: {before:,}")
        logger.info(f"  Rows after:  {len(df_deduped):,} ({before - len(df_deduped):,} removed)")
        logger.info(f"  Multi-offence incidents identified: {multi_count:,}")

    return df_deduped


def run():
    _project_root = os.path.normpath(os.path.join(os.path.dirname(__file__), '..', '..', '..'))
    input_file = os.path.join(_project_root, 'data', '02_transformed', '02_unified_valid.csv')
    output_file = os.path.join(_project_root, 'data', '02_transformed', '03_unified_valid_deduplicated.csv')

    if not os.path.exists(input_file):
        logging.error(f"Input file not found: {input_file}")
        return

    logging.info(f"Loading data from {input_file}...")
    df = pd.read_csv(input_file, low_memory=False)

    logging.info("Deduplicating incidents...")
    df_deduped = deduplicate_incidents(df, verbose=True)

    logging.info(f"Saving deduplicated data to {output_file}...")
    df_deduped.to_csv(output_file, index=False)
    logging.info("Done.")

if __name__ == "__main__":
    run()