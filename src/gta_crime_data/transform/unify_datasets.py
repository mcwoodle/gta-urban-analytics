import pandas as pd
import glob
import os
import json
import logging
from importlib import resources
from pyproj import Transformer
from gta_crime_data.schemas import (
    durham_schema, halton_schema, peel_schema, 
    toronto_schema, york_schema, unified_schema
)
from gta_crime_data.extract.durham import DURHAM_DATASETS

logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')

# Resolve paths relative to the project root (3 levels up from this file)
_project_root = os.path.normpath(os.path.join(os.path.dirname(__file__), '..', '..', '..'))
data_dir = os.path.join(_project_root, 'data', '01_raw')
output_dir = os.path.join(_project_root, 'data', '02_transformed')
output_file = os.path.join(output_dir, '01_unified.csv')

def _load_mapping():
    mapping_ref = resources.files('gta_crime_data.transform').joinpath('crime_category_mappings.json')
    with resources.as_file(mapping_ref) as mapping_path:
        with open(mapping_path, 'r') as f:
            return json.load(f)

def map_crime(crime_type, mapping):
    if pd.isna(crime_type) or not str(crime_type).strip() or str(crime_type).strip().lower() == 'nan':
        return "Other"
    ct = str(crime_type).strip()
    return mapping.get(ct, "Other")

# Setup pyproj transformer for York (EPSG:26917 to EPSG:4326)
transformer = Transformer.from_crs("EPSG:26917", "EPSG:4326", always_xy=True)

def run():
    os.makedirs(output_dir, exist_ok=True)
    mapping = _load_mapping()
    _map = lambda ct: map_crime(ct, mapping)

    all_dfs = []

    # Map Durham filenames to categories
    durham_category_map = {
        os.path.splitext(d['raw_csv_file'])[0]: d['category'] 
        for d in DURHAM_DATASETS
    }

    # Durham
    for f in glob.glob(os.path.join(data_dir, 'Durham_*.csv')):
        logging.info(f"Processing Durham: {f}")
        raw_file = os.path.splitext(os.path.basename(f))[0]
        
        # Look up the top-level crime category from the registry
        file_category = durham_category_map.get(raw_file, "Other")
        
        df = pd.read_csv(f, low_memory=False, encoding='utf-8-sig')
        durham_schema.validate(df)
        
        if 'occurrence_year' in df.columns:
            month_map = {'Jan':'01','Feb':'02','Mar':'03','Apr':'04','May':'05','Jun':'06',
                         'Jul':'07','Aug':'08','Sep':'09','Oct':'10','Nov':'11','Dec':'12'}
            m = df['occurrence_month'].map(month_map).fillna('01')
            y = df['occurrence_year'].fillna(0).astype(int).astype(str)
            d = df['occurrence_day'].fillna(1).astype(int).astype(str).str.zfill(2)
            dates = pd.to_datetime(y + '-' + m + '-' + d, errors='coerce').dt.strftime('%Y-%m-%d')
        else:
            dates = pd.NaT

        out = pd.DataFrame({
            'source_file_name': raw_file,
            'source_identifier': df.get('event_unique_id', df.index.to_series().astype(str)),
            'region': 'Durham',
            # Use 'offence' column if available, fall back to the filename-derived category
            'original_crime_type': df.get('offence', pd.Series([file_category]*len(df))).fillna(file_category),
            'mapped_crime_category': file_category,
            'occurrence_date': dates,
            'lat': df.get('lat'),
            'lon': df.get('lon'),
            'municipality': df.get('municipality', pd.Series(dtype=str)).str.strip()
        })
        all_dfs.append(out)

    # Halton
    halton = os.path.join(data_dir, 'Halton_Crime_Map_Data.csv')
    if os.path.exists(halton):
        logging.info(f"Processing Halton: {halton}")
        df = pd.read_csv(halton, low_memory=False)
        halton_schema.validate(df)
        dates = pd.to_datetime(df['DATE'], unit='ms', errors='coerce').dt.strftime('%Y-%m-%d')
        
        raw_file = os.path.splitext(os.path.basename(halton))[0]
        out = pd.DataFrame({
            'source_file_name': raw_file,
            'source_identifier': df.get('OBJECTID', df.index.to_series()).astype(str),
            'region': 'Halton',
            'original_crime_type': df.get('DESCRIPTION'),
            'mapped_crime_category': df.get('DESCRIPTION', pd.Series(dtype=str)).apply(_map),
            'occurrence_date': dates,
            'lat': df.get('Latitude'),
            'lon': df.get('Longitude'),
            'municipality': df.get('CITY')
        })
        all_dfs.append(out)

    # Peel
    peel = os.path.join(data_dir, 'Peel_Crime_Map_Data.csv')
    if os.path.exists(peel):
        logging.info(f"Processing Peel: {peel}")
        df = pd.read_csv(peel, low_memory=False)
        peel_schema.validate(df)
        
        if 'OccDate' in df.columns:
            dates = pd.to_datetime(df['OccDate'], unit='ms', errors='coerce').dt.strftime('%Y-%m-%d')
        elif 'OccurrenceDate' in df.columns:
            dates = pd.to_datetime(df['OccurrenceDate'], errors='coerce').dt.strftime('%Y-%m-%d')
        else:
            dates = pd.NaT

        raw_file = os.path.splitext(os.path.basename(peel))[0]
        out = pd.DataFrame({
            'source_file_name': raw_file,
            'source_identifier': df.get('OBJECTID', df.index.to_series()).astype(str),
            'region': 'Peel',
            'original_crime_type': df.get('Description'),
            'mapped_crime_category': df.get('Description', pd.Series(dtype=str)).apply(_map),
            'occurrence_date': dates,
            'lat': df.get('lat'),
            'lon': df.get('lon'),
            'municipality': df.get('Municipality')
        })
        all_dfs.append(out)

    # Toronto
    toronto = os.path.join(data_dir, 'Toronto_Major_Crime_Indicators.csv')
    if os.path.exists(toronto):
        logging.info(f"Processing Toronto: {toronto}")
        df = pd.read_csv(toronto, low_memory=False)
        toronto_schema.validate(df)
        
        dates = pd.to_datetime(df['OCC_DATE'], errors='coerce').dt.strftime('%Y-%m-%d')
        
        raw_file = os.path.splitext(os.path.basename(toronto))[0]
        out = pd.DataFrame({
            'source_file_name': raw_file,
            'source_identifier': df.get('EVENT_UNIQUE_ID', df.index.to_series().astype(str)),
            'region': 'Toronto',
            'original_crime_type': df.get('OFFENCE'),
            'mapped_crime_category': df.get('OFFENCE', pd.Series(dtype=str)).apply(_map),
            'occurrence_date': dates,
            'lat': df.get('LAT_WGS84'),
            'lon': df.get('LONG_WGS84'),
            'municipality': 'Toronto'
        })
        all_dfs.append(out)

    # York
    for f in glob.glob(os.path.join(data_dir, 'York_*.csv')):
        logging.info(f"Processing York: {f}")
        raw_file = os.path.splitext(os.path.basename(f))[0]
        df = pd.read_csv(f, low_memory=False)
        york_schema.validate(df)
        
        dates = pd.to_datetime(df.get('Occurrence Date', pd.NaT), errors='coerce').dt.strftime('%Y-%m-%d')
        
        crime_type = df.get('Occurrence Type', df.get('Occurrence Detail'))
        if crime_type is None:
            crime_type = pd.Series([None]*len(df))
        
        if 'x' in df.columns and 'y' in df.columns:
            valid_idx = df['x'].notna() & df['y'].notna()
            res_lon, res_lat = transformer.transform(df.loc[valid_idx, 'x'].values, df.loc[valid_idx, 'y'].values)
            
            lons_series = pd.Series(index=df.index, dtype=float)
            lats_series = pd.Series(index=df.index, dtype=float)
            lons_series[valid_idx] = res_lon
            lats_series[valid_idx] = res_lat
        else:
            lons_series = pd.Series([None]*len(df))
            lats_series = pd.Series([None]*len(df))
            
        uid_col = df.get('UniqueIdentifier', df.get('OBJECTID', df.index.to_series())).astype(str)
            
        out = pd.DataFrame({
            'source_file_name': raw_file,
            'source_identifier': uid_col,
            'region': 'York',
            'original_crime_type': crime_type,
            'mapped_crime_category': crime_type.apply(_map),
            'occurrence_date': dates,
            'lat': lats_series,
            'lon': lons_series,
            'municipality': df.get('Municipality', pd.Series(dtype=str))
        })
        all_dfs.append(out)

    logging.info("Concatenating all regions...")
    if all_dfs:
        unified_df = pd.concat(all_dfs, ignore_index=True)
        unified_df.to_csv(output_file, index=False)
        logging.info(f"Finished writing {len(unified_df)} rows and {len(unified_df.columns)} columns to {output_file}")
    else:
        logging.info("No data frames to concatenate.")

if __name__ == "__main__":
    run()
