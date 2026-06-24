"""Regression tests for audit finding F-01: Durham must use the canonical
crime-category taxonomy (mapped via the JSON), not the source filename."""

import pandas as pd
from unittest import mock

from gta_urban_analytics.transform.crime.unify_datasets import (
    unify_datasets,
    map_crime,
    _load_mapping,
)


def test_durham_offences_map_to_canonical_categories():
    """The JSON taxonomy canonicalises labels and fixes the filename mis-bucketing."""
    m = _load_mapping()
    assert map_crime("Assault Level 2", m) == "Assault"
    assert map_crime("B&E - Residential", m) == "Break & Enter"
    assert map_crime("Theft from MV over $5,000", m) == "Theft"
    # These lived in Durham's *Robbery* file but the JSON classifies them better:
    assert map_crime("Home Invasion", m) == "Break & Enter"
    assert map_crime("Carjacking", m) == "Auto Theft"
    assert map_crime("Shootings and Firearm Discharge", m) == "Weapons Offences"


@mock.patch("gta_urban_analytics.transform.crime.unify_datasets.os.path.exists")
@mock.patch("gta_urban_analytics.transform.crime.unify_datasets.glob.glob")
@mock.patch("gta_urban_analytics.transform.crime.unify_datasets.pd.read_csv")
def test_unify_durham_emits_canonical_category(mock_read_csv, mock_glob, mock_exists):
    """unify_datasets must set Durham's mapped_crime_category from the offence
    taxonomy, never the legacy filename labels (e.g. 'Assaults')."""
    mock_exists.return_value = False  # skip the direct-path Halton/Peel branches

    def glob_side_effect(path):
        return ["/fake/data/01_raw/Durham_Assaults.csv"] if "Durham_" in path else []

    mock_glob.side_effect = glob_side_effect

    def read_side_effect(filename, **kwargs):
        if "Durham_Assaults" in filename:
            return pd.DataFrame(
                {
                    "event_unique_id": ["GO-1", "GO-2", "GO-3"],
                    "offence": ["Assault Level 2", "Carjacking", "Home Invasion"],
                    "occurrence_year": [2024, 2024, 2024],
                    "occurrence_month": ["Feb", "Mar", "Apr"],
                    "occurrence_day": [9, 10, 11],
                    "lat": [43.85, 43.86, 43.87],
                    "lon": [-79.05, -79.06, -79.07],
                    "municipality": ["AJA", "AJA", "AJA"],
                }
            )
        return pd.DataFrame()

    mock_read_csv.side_effect = read_side_effect

    df = unify_datasets()
    durham = df[df["region"] == "Durham"].reset_index(drop=True)

    assert list(durham["mapped_crime_category"]) == ["Assault", "Auto Theft", "Break & Enter"]
    # The raw offence text is preserved in original_crime_type.
    assert list(durham["original_crime_type"]) == ["Assault Level 2", "Carjacking", "Home Invasion"]
    # No legacy non-canonical Durham labels survive anywhere.
    assert {"Assaults", "Break and Enter", "Theft Over 5000", "Drug Violations"}.isdisjoint(
        set(df["mapped_crime_category"])
    )


@mock.patch("gta_urban_analytics.transform.crime.unify_datasets.os.path.exists")
@mock.patch("gta_urban_analytics.transform.crime.unify_datasets.glob.glob")
@mock.patch("gta_urban_analytics.transform.crime.unify_datasets.pd.read_csv")
def test_unify_durham_shootings_file_without_offence_column(mock_read_csv, mock_glob, mock_exists):
    """F-01c: the shootings file has no 'offence' column, so original_crime_type
    falls back to the file category — which must still map canonically."""
    mock_exists.return_value = False
    mock_glob.side_effect = lambda path: (
        ["/fake/data/01_raw/Durham_Shootings_and_Firearm_Discharge.csv"] if "Durham_" in path else []
    )

    def read_side_effect(filename, **kwargs):
        if "Durham_Shootings_and_Firearm_Discharge" in filename:
            return pd.DataFrame(
                {
                    "event_unique_id": ["GO-9"],  # NOTE: no 'offence' column
                    "report_year": [2025],
                    "lat": [43.85], "lon": [-79.05], "municipality": ["PIC"],
                }
            )
        return pd.DataFrame()

    mock_read_csv.side_effect = read_side_effect

    df = unify_datasets()
    durham = df[df["region"] == "Durham"].reset_index(drop=True)
    assert list(durham["original_crime_type"]) == ["Shootings and Firearm Discharge"]
    assert list(durham["mapped_crime_category"]) == ["Weapons Offences"]


@mock.patch("gta_urban_analytics.transform.crime.unify_datasets.os.path.exists")
@mock.patch("gta_urban_analytics.transform.crime.unify_datasets.glob.glob")
@mock.patch("gta_urban_analytics.transform.crime.unify_datasets.pd.read_csv")
def test_unify_durham_unmapped_offence_falls_back_to_canonical(mock_read_csv, mock_glob, mock_exists):
    """F-01b: an offence absent from the JSON maps to 'Other', which must fall back
    to the canonicalised file category — never leaving a non-canonical/'Other' label."""
    mock_exists.return_value = False
    mock_glob.side_effect = lambda path: (
        ["/fake/data/01_raw/Durham_Assaults.csv"] if "Durham_" in path else []
    )

    def read_side_effect(filename, **kwargs):
        if "Durham_Assaults" in filename:
            return pd.DataFrame(
                {
                    "event_unique_id": ["GO-1"],
                    "offence": ["Made Up Offence XYZ"],  # not in crime_category_mappings.json
                    "occurrence_year": [2025], "occurrence_month": ["Jan"], "occurrence_day": [1],
                    "lat": [43.85], "lon": [-79.05], "municipality": ["AJA"],
                }
            )
        return pd.DataFrame()

    mock_read_csv.side_effect = read_side_effect

    df = unify_datasets()
    durham = df[df["region"] == "Durham"].reset_index(drop=True)
    assert list(durham["mapped_crime_category"]) == ["Assault"]  # fallback for the "Assaults" file
    assert "Other" not in set(df["mapped_crime_category"])


@mock.patch("gta_urban_analytics.transform.crime.unify_datasets.os.path.exists")
@mock.patch("gta_urban_analytics.transform.crime.unify_datasets.glob.glob")
@mock.patch("gta_urban_analytics.transform.crime.unify_datasets.pd.read_csv")
def test_unify_durham_bad_month_yields_nat(mock_read_csv, mock_glob, mock_exists):
    """F-15: an unrecognised occurrence_month must produce NaT, not a fabricated January."""
    mock_exists.return_value = False
    mock_glob.side_effect = lambda path: (
        ["/fake/data/01_raw/Durham_Assaults.csv"] if "Durham_" in path else []
    )

    def read_side_effect(filename, **kwargs):
        if "Durham_Assaults" in filename:
            return pd.DataFrame(
                {
                    "event_unique_id": ["GO-good", "GO-bad"],
                    "offence": ["Assault Level 1", "Assault Level 1"],
                    "occurrence_year": [2025, 2025],
                    "occurrence_month": ["Jan", "Xyz"],  # second month is unrecognised
                    "occurrence_day": [1, 2],
                    "lat": [43.85, 43.86], "lon": [-79.05, -79.06], "municipality": ["AJA", "AJA"],
                }
            )
        return pd.DataFrame()

    mock_read_csv.side_effect = read_side_effect

    df = unify_datasets().set_index("source_identifier")
    assert df.loc["Durham_GO-good", "occurrence_date"] == "2025-01-01"
    assert pd.isna(df.loc["Durham_GO-bad", "occurrence_date"])
