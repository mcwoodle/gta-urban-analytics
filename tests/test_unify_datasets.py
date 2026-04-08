import pandas as pd
from unittest import mock
import pytest
import os

from gta_urban_analytics.transform.crime.unify_datasets import unify_datasets

@mock.patch("gta_urban_analytics.transform.crime.unify_datasets.os.path.exists")
@mock.patch("gta_urban_analytics.transform.crime.unify_datasets.glob.glob")
@mock.patch("gta_urban_analytics.transform.crime.unify_datasets.pd.read_csv")
def test_unify_datasets_prevents_source_identifier_collisions(mock_read_csv, mock_glob, mock_exists):
    """
    Ensures that unify_datasets correctly prevents ID collisions
    between different regions by prepending the region name to the source_identifier.
    """
    # Force the files to look like they exist
    mock_exists.return_value = True
    
    # We will simulate Peel and Halton data, which were natively overlapping 
    # since both use generic OBJECTID sequences starting from 1.
    def mock_csv_side_effect(filename, **kwargs):
        if "Peel_Crime_Map_Data" in filename:
            return pd.DataFrame({
                "OBJECTID": [10844],
                "OccurrenceDate": ["2026-01-29"],
                "Description": ["Motor Vehicle Theft - Automobile"],
                "lat": [43.56],
                "lon": [-79.64],
                "Municipality": ["MISSISSAUGA"]
            })
        elif "Halton_Crime_Map_Data" in filename:
            return pd.DataFrame({
                "OBJECTID": [10844],
                "DATE": [1769684400000],  # some ms timestamp
                "DESCRIPTION": ["THEFT OF VEHICLE"],
                "Latitude": [43.49],
                "Longitude": [-79.69],
                "CITY": ["OAKVILLE"]
            })
        elif "Toronto_Major_Crime" in filename:
            return pd.DataFrame({
                "EVENT_UNIQUE_ID": ["GO-1234"],
                "OCC_DATE": ["2026-01-01"],
                "OFFENCE": ["Robbery"],
                "LAT_WGS84": [43.65],
                "LONG_WGS84": [-79.38]
            })
        # For simplicity, empty dfs for the others so we only test what we need
        return pd.DataFrame()

    mock_read_csv.side_effect = mock_csv_side_effect
    
    # Only return our fake CSVs for Durham and York when globbed
    mock_glob.side_effect = lambda path: []

    # Run the unify pipeline
    unified_df = unify_datasets()
    
    # Assert that Peel and Halton were loaded
    assert "Peel" in unified_df['region'].values, "Peel data should be loaded"
    assert "Halton" in unified_df['region'].values, "Halton data should be loaded"

    # Extract the rows
    peel_row = unified_df[unified_df['region'] == 'Peel'].iloc[0]
    halton_row = unified_df[unified_df['region'] == 'Halton'].iloc[0]

    # Verify that the generic ID '10844' from the mocks wasn't used identically.
    # The fix ensures that the region string is prepended, so the source_identifiers shouldn't match!
    assert peel_row['source_identifier'] != halton_row['source_identifier'], \
        "Collision Bug: Peel and Halton rows share the same source_identifier!"
        
    # Specifically, it should start with the region
    assert peel_row['source_identifier'].startswith("Peel_")
    assert halton_row['source_identifier'].startswith("Halton_")
