"""Regression test for audit finding F-03: null-island (0,0) and out-of-bounds
coordinates must be nulled so the filter step quarantines those rows."""

import pandas as pd

from gta_urban_analytics.transform.crime.unify_datasets import _null_out_of_bounds_coords


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

    # (0,0) null-island is nulled.
    assert pd.isna(out.loc[1, "lat"]) and pd.isna(out.loc[1, "lon"])

    # Far out-of-bounds is nulled.
    assert pd.isna(out.loc[3, "lat"]) and pd.isna(out.loc[3, "lon"])

    # The input frame is not mutated in place.
    assert df.loc[1, "lat"] == 0.0
