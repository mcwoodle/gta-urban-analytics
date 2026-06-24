"""Regression tests for audit finding F-03: null-island (0,0) and out-of-bounds
coordinates must be nulled by the helper AND by the real unify output (so the
filter step can quarantine those rows)."""

from unittest import mock

import pandas as pd

from gta_urban_analytics.transform.crime.unify_datasets import (
    _null_out_of_bounds_coords,
    unify_datasets,
)


def test_null_island_and_out_of_bounds_coords_are_nulled():
    df = pd.DataFrame(
        {
            "lat": [43.65, 0.0, 44.0, 50.0, 43.7],
            "lon": [-79.38, 0.0, -79.0, -100.0, -79.4],
            "region": ["Toronto", "Toronto", "York", "Elsewhere", "Toronto"],
        }
    )

    out = _null_out_of_bounds_coords(df)

    # In-box coordinates are preserved.
    assert (out.loc[0, "lat"], out.loc[0, "lon"]) == (43.65, -79.38)
    assert out.loc[2, "lat"] == 44.0
    assert out.loc[4, "lat"] == 43.7
    # (0,0) null-island and far out-of-bounds are nulled.
    assert pd.isna(out.loc[1, "lat"]) and pd.isna(out.loc[1, "lon"])
    assert pd.isna(out.loc[3, "lat"]) and pd.isna(out.loc[3, "lon"])
    # The input frame is not mutated in place.
    assert df.loc[1, "lat"] == 0.0


@mock.patch("gta_urban_analytics.transform.crime.unify_datasets.os.path.exists")
@mock.patch("gta_urban_analytics.transform.crime.unify_datasets.glob.glob")
@mock.patch("gta_urban_analytics.transform.crime.unify_datasets.pd.read_csv")
def test_unify_applies_coordinate_nulling(mock_read_csv, mock_glob, mock_exists):
    """unify_datasets must run the bbox/(0,0) nulling on its concatenated output,
    not just expose the helper."""
    mock_exists.return_value = False
    mock_glob.side_effect = lambda path: (
        ["/fake/data/01_raw/Durham_Assaults.csv"] if "Durham_" in path else []
    )

    def read_side_effect(filename, **kwargs):
        if "Durham_Assaults" in filename:
            return pd.DataFrame(
                {
                    "event_unique_id": ["GO-good", "GO-zero"],
                    "offence": ["Assault Level 1", "Assault Level 1"],
                    "occurrence_year": [2025, 2025], "occurrence_month": ["Jan", "Jan"],
                    "occurrence_day": [1, 2],
                    "lat": [43.85, 0.0], "lon": [-79.05, 0.0], "municipality": ["AJA", "AJA"],
                }
            )
        return pd.DataFrame()

    mock_read_csv.side_effect = read_side_effect

    df = unify_datasets().set_index("source_identifier")
    assert (df.loc["Durham_GO-good", "lat"], df.loc["Durham_GO-good", "lon"]) == (43.85, -79.05)
    assert pd.isna(df.loc["Durham_GO-zero", "lat"]) and pd.isna(df.loc["Durham_GO-zero", "lon"])
