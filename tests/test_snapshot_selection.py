"""Regression tests for audit finding F-05/F-06: date-stamped snapshot files must
be de-duplicated to the newest per source so stale copies aren't double-loaded."""

from gta_urban_analytics.transform.crime.unify_datasets import _drop_stale_snapshots


def test_keeps_only_newest_york_snapshot():
    files = [
        "/d/York_Historical_2021_to_2025.csv",   # not a date snapshot -> passthrough
        "/d/York_2025_to_2026-06-18.csv",         # stale
        "/d/York_2025_to_2026-06-19.csv",         # newest
    ]
    kept = set(_drop_stale_snapshots(files))
    assert kept == {
        "/d/York_Historical_2021_to_2025.csv",
        "/d/York_2025_to_2026-06-19.csv",
    }


def test_keeps_only_newest_toronto_ytd_snapshot():
    files = [
        "/d/Toronto_Major_Crime_Indicators.csv",  # not a date snapshot -> passthrough
        "/d/Toronto_YTD_to_2026-06-17.csv",        # stale
        "/d/Toronto_YTD_to_2026-06-18.csv",        # newest
    ]
    kept = set(_drop_stale_snapshots(files))
    assert kept == {
        "/d/Toronto_Major_Crime_Indicators.csv",
        "/d/Toronto_YTD_to_2026-06-18.csv",
    }


def test_passthrough_when_no_snapshots():
    files = ["/d/Durham_Assaults.csv", "/d/Peel_Crime_Map_Data.csv"]
    assert _drop_stale_snapshots(files) == files
