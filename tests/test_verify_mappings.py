"""Tests for verify_mappings: pass when every original_crime_type is a JSON key,
raise (aborting the pipeline) when one is missing (closes a T12/F-14 gap)."""

import pandas as pd
import pytest

from gta_urban_analytics.transform.crime.verify_mappings import verify_mappings


def test_passes_when_all_types_mapped():
    # Both are confirmed keys in crime_category_mappings.json.
    df = pd.DataFrame({"original_crime_type": ["Assault Level 2", "B&E - Residential"]})
    verify_mappings(df)  # must not raise


def test_raises_on_unmapped_type():
    df = pd.DataFrame({"original_crime_type": ["Assault Level 2", "Totally Unmapped Offence ZZZ"]})
    with pytest.raises(ValueError, match="not found"):
        verify_mappings(df)
