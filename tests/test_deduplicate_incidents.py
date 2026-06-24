"""Tests for the deduplication stage: one row per source_identifier, with
multi-offence incidents concatenated and flagged MULTIPLE (closes an F-14 gap)."""

import pandas as pd

from gta_urban_analytics.transform.crime.deduplicate_incidents import deduplicate_incidents


def test_dedup_collapses_and_flags_multi_offence():
    df = pd.DataFrame(
        {
            "source_identifier": ["A", "A", "B", "C", "C"],
            "original_crime_type": ["Robbery", "Assault", "Theft", "Fraud", "Fraud"],
            "mapped_crime_category": ["Robbery", "Assault", "Theft", "Fraud", "Fraud"],
            "lat": [43.6] * 5, "lon": [-79.4] * 5, "region": ["Toronto"] * 5,
        }
    )

    out = deduplicate_incidents(df, verbose=False).set_index("source_identifier")

    # A had two distinct crimes → MULTIPLE, concatenated in sorted order.
    assert out.loc["A", "mapped_crime_category"] == "MULTIPLE"
    assert out.loc["A", "original_crime_type"] == "Assault && Robbery"
    # B is a single incident → unchanged.
    assert out.loc["B", "mapped_crime_category"] == "Theft"
    assert out.loc["B", "original_crime_type"] == "Theft"
    # C had a duplicate of the SAME crime → collapsed to one, not MULTIPLE.
    assert out.loc["C", "mapped_crime_category"] == "Fraud"
    # One row per source_identifier overall.
    assert len(out) == 3
