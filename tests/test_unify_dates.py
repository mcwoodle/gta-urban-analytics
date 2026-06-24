"""Date-parsing regression tests for unify_datasets (broadens coverage; also locks
the F-07 trap — epoch-ms columns must keep parsing to real dates, not NaT)."""

import pandas as pd
from unittest import mock

from gta_urban_analytics.transform.crime.unify_datasets import unify_datasets


@mock.patch("gta_urban_analytics.transform.crime.unify_datasets.os.path.exists")
@mock.patch("gta_urban_analytics.transform.crime.unify_datasets.glob.glob")
@mock.patch("gta_urban_analytics.transform.crime.unify_datasets.pd.read_csv")
def test_toronto_ytd_epoch_ms_date(mock_read_csv, mock_glob, mock_exists):
    mock_exists.return_value = False
    mock_glob.side_effect = lambda path: (
        ["/fake/data/01_raw/Toronto_YTD_to_2026-06-18.csv"] if "Toronto_" in path else []
    )

    def read_side_effect(filename, **kwargs):
        if "Toronto_YTD" in filename:
            return pd.DataFrame(
                {
                    "OBJECTID": [1],
                    "OCC_DATE_AGOL": [1735689600000],  # 2025-01-01 00:00:00 UTC, epoch ms
                    "EVENT_UNIQUE_ID": ["GO-2025-1"],
                    "CRIME_TYPE": ["Assault"],
                    "LAT_WGS84": [43.65], "LONG_WGS84": [-79.38],
                }
            )
        return pd.DataFrame()

    mock_read_csv.side_effect = read_side_effect
    tor = unify_datasets().iloc[0]
    assert tor["occurrence_date"] == "2025-01-01"
    assert tor["mapped_crime_category"] == "Assault"


@mock.patch("gta_urban_analytics.transform.crime.unify_datasets.os.path.exists")
@mock.patch("gta_urban_analytics.transform.crime.unify_datasets.glob.glob")
@mock.patch("gta_urban_analytics.transform.crime.unify_datasets.pd.read_csv")
def test_toronto_mci_us_format_date(mock_read_csv, mock_glob, mock_exists):
    mock_exists.return_value = False
    mock_glob.side_effect = lambda path: (
        ["/fake/data/01_raw/Toronto_Major_Crime_Indicators.csv"] if "Toronto_" in path else []
    )

    def read_side_effect(filename, **kwargs):
        if "Toronto_Major_Crime" in filename:
            return pd.DataFrame(
                {
                    "EVENT_UNIQUE_ID": ["GO-1"],
                    "OCC_DATE": ["3/15/2024 5:00:00 AM"],  # M/D/YYYY
                    "OFFENCE": ["Assault"],
                    "LAT_WGS84": [43.65], "LONG_WGS84": [-79.38],
                }
            )
        return pd.DataFrame()

    mock_read_csv.side_effect = read_side_effect
    tor = unify_datasets().iloc[0]
    assert tor["occurrence_date"] == "2024-03-15"


@mock.patch("gta_urban_analytics.transform.crime.unify_datasets.os.path.exists")
@mock.patch("gta_urban_analytics.transform.crime.unify_datasets.glob.glob")
@mock.patch("gta_urban_analytics.transform.crime.unify_datasets.pd.read_csv")
def test_peel_epoch_ms_date(mock_read_csv, mock_glob, mock_exists):
    # Peel loads via os.path.exists, not glob.
    mock_exists.side_effect = lambda p: "Peel_Crime_Map_Data" in p
    mock_glob.side_effect = lambda path: []

    def read_side_effect(filename, **kwargs):
        if "Peel_Crime_Map_Data" in filename:
            return pd.DataFrame(
                {
                    "OBJECTID": [1],
                    "OccDate": [1735689600000],  # 2025-01-01, epoch ms
                    "Description": ["Assault"],
                    "lat": [43.6], "lon": [-79.7], "Municipality": ["MISSISSAUGA"],
                }
            )
        return pd.DataFrame()

    mock_read_csv.side_effect = read_side_effect
    peel = unify_datasets().iloc[0]
    assert peel["occurrence_date"] == "2025-01-01"
    assert peel["municipality"] == "Mississauga"  # normalized (F-08)
