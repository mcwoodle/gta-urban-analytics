"""Regression test backing audit finding F-03's end-to-end contract: rows with
missing (NaN) coordinates — which is how F-03 marks (0,0)/out-of-bounds points —
must be removed from the valid output and written to invalid_data.csv."""

import numpy as np
import pandas as pd

from gta_urban_analytics.transform.crime import filter_invalid_incidents as fmod


def _row(**over):
    base = dict(
        source_file_name="f", source_identifier="X_1", region="Toronto",
        original_crime_type="Assault", mapped_crime_category="Assault",
        occurrence_date="2025-01-01", lat=43.65, lon=-79.38, municipality="Toronto",
    )
    base.update(over)
    return base


def test_nan_coordinates_are_quarantined(tmp_path, monkeypatch):
    # Redirect the hard-coded invalid_data.csv output into the test's tmp dir.
    monkeypatch.setattr(fmod, "_project_root", str(tmp_path))

    df = pd.DataFrame(
        [
            _row(source_identifier="X_ok"),
            _row(source_identifier="X_bad", lat=np.nan, lon=np.nan),
        ]
    )

    valid = fmod.filter_invalid_incidents(df, verbose=False)

    # The NaN-coordinate row is dropped from the valid output...
    assert list(valid["source_identifier"]) == ["X_ok"]
    # ...and quarantined to invalid_data.csv for inspection.
    invalid_csv = tmp_path / "data" / "02_transformed" / "invalid_data.csv"
    assert invalid_csv.exists()
    inv = pd.read_csv(invalid_csv)
    assert list(inv["source_identifier"]) == ["X_bad"]
