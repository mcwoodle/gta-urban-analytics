"""Regression tests for audit finding F-08: municipality names must be normalised
to a single canonical Title-case label (and original_crime_type stripped, F-15)."""

import pandas as pd
from unittest import mock

from gta_urban_analytics.transform.crime.unify_datasets import (
    _normalize_municipality,
    unify_datasets,
)


def test_normalize_municipality_unit():
    # Durham 3-letter codes expand to full names.
    assert _normalize_municipality("AJA") == "Ajax"
    assert _normalize_municipality("OSH            ") == "Oshawa"  # padded code
    # UPPER → Title; the same city resolves identically across regions.
    assert _normalize_municipality("BURLINGTON") == "Burlington"
    assert _normalize_municipality("TORONTO") == "Toronto"        # Peel spelling
    assert _normalize_municipality("VAUGHAN") == "Vaughan"        # Peel spelling
    # Peel's no-internal-space spellings.
    assert _normalize_municipality("HALTONHILLS") == "Halton Hills"
    assert _normalize_municipality("RICHMONDHILL") == "Richmond Hill"
    assert _normalize_municipality("HALTON HILLS") == "Halton Hills"
    # Already-canonical Title case is idempotent; blanks/NaN pass through.
    assert _normalize_municipality("Markham") == "Markham"
    assert _normalize_municipality("") == ""
    assert pd.isna(_normalize_municipality(float("nan")))


@mock.patch("gta_urban_analytics.transform.crime.unify_datasets.os.path.exists")
@mock.patch("gta_urban_analytics.transform.crime.unify_datasets.glob.glob")
@mock.patch("gta_urban_analytics.transform.crime.unify_datasets.pd.read_csv")
def test_unify_normalizes_municipality_and_strips_original(mock_read_csv, mock_glob, mock_exists):
    mock_exists.return_value = False
    mock_glob.side_effect = lambda path: (
        ["/fake/data/01_raw/Durham_Assaults.csv"] if "Durham_" in path else []
    )

    def read_side_effect(filename, **kwargs):
        if "Durham_Assaults" in filename:
            return pd.DataFrame(
                {
                    "event_unique_id": ["GO-1"],
                    "offence": [" Assault Level 1"],          # leading whitespace
                    "occurrence_year": [2025], "occurrence_month": ["Jan"], "occurrence_day": [1],
                    "lat": [43.85], "lon": [-79.05],
                    "municipality": ["AJA            "],        # padded 3-letter code
                }
            )
        return pd.DataFrame()

    mock_read_csv.side_effect = read_side_effect

    df = unify_datasets()
    row = df[df["region"] == "Durham"].iloc[0]
    assert row["municipality"] == "Ajax"
    assert row["original_crime_type"] == "Assault Level 1"  # leading space stripped (F-15)
    assert row["mapped_crime_category"] == "Assault"
