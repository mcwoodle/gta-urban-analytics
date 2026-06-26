"""Tests for the coverage-metadata builder: per-region date windows, the
category × region presence matrix (which flags subset gaps like Durham's), the
MULTIPLE folding audit, and the partial-year / same-period-prior-year block."""

import datetime
import json

import pandas as pd

from gta_urban_analytics.transform.build_coverage_metadata import (
    build_coverage_metadata,
)


def _frame():
    """Two regions with deliberately different coverage:
    - Toronto: long window, several categories.
    - Durham: a narrow subset (Violent/Property only), no Fraud/Public Order.
    """
    rows = [
        # Toronto — wide window, varied categories
        ("Toronto", "Assault", "Violent", "2014-05-01"),
        ("Toronto", "Fraud", "Property", "2025-02-10"),
        ("Toronto", "Public Order", "Nuisance", "2025-08-01"),
        ("Toronto", "MULTIPLE", "Other", "2025-09-01"),
        # Durham — only Assault + Break & Enter, recent
        ("Durham", "Assault", "Violent", "2025-03-15"),
        ("Durham", "Break & Enter", "Property", "2025-07-20"),
    ]
    return pd.DataFrame(
        rows, columns=["region", "mapped_crime_category", "crime_group", "occurrence_date"]
    )


def test_region_summaries_and_windows(tmp_path):
    payload = build_coverage_metadata(
        crime_df=_frame(), output_dir=str(tmp_path), verbose=False
    )
    regions = payload["regions"]
    assert regions["Toronto"]["min_date"] == "2014-05-01"
    assert regions["Toronto"]["max_date"] == "2025-09-01"
    assert regions["Durham"]["min_date"] == "2025-03-15"
    assert regions["Durham"]["n_incidents"] == 2
    assert set(regions["Durham"]["groups_present"]) == {"Violent", "Property"}


def test_category_matrix_flags_subset_gap(tmp_path):
    payload = build_coverage_metadata(
        crime_df=_frame(), output_dir=str(tmp_path), verbose=False
    )
    matrix = payload["category_x_region"]
    # Durham reports Assault but NOT Fraud / Public Order — the gap is explicit.
    assert matrix["Durham"]["Assault"] is True
    assert matrix["Durham"]["Fraud"] is False
    assert matrix["Durham"]["Public Order"] is False
    assert matrix["Toronto"]["Fraud"] is True


def test_multiple_count_audits_folding(tmp_path):
    payload = build_coverage_metadata(
        crime_df=_frame(), output_dir=str(tmp_path), verbose=False
    )
    assert payload["multiple_count"]["Toronto"] == 1
    assert payload["multiple_count"].get("Durham", 0) == 0


def test_writes_file(tmp_path):
    build_coverage_metadata(crime_df=_frame(), output_dir=str(tmp_path), verbose=False)
    written = json.loads((tmp_path / "coverage.json").read_text())
    assert written["scope"] == "all_years"


def test_current_year_is_partial_with_sppy(tmp_path):
    this_year = datetime.datetime.now().year
    last_year = this_year - 1
    # One incident this year, two in the prior year's Jan-1 window.
    df = pd.DataFrame(
        {
            "region": ["York"] * 3,
            "mapped_crime_category": ["Assault"] * 3,
            "crime_group": ["Violent"] * 3,
            "occurrence_date": [
                f"{this_year}-01-05",
                f"{last_year}-01-03",
                f"{last_year}-01-04",
            ],
        }
    )
    payload = build_coverage_metadata(
        crime_df=df, year=this_year, output_dir=str(tmp_path), verbose=False
    )
    assert payload["is_partial"] is True
    assert payload["year"] == this_year
    assert 0 < payload["fraction_elapsed"] <= 1
    # Both prior-year incidents fall before today's month/day → counted.
    assert payload["same_period_prior_year_incidents"] == 2


def test_past_year_not_partial(tmp_path):
    past = datetime.datetime.now().year - 1
    df = pd.DataFrame(
        {
            "region": ["York"],
            "mapped_crime_category": ["Assault"],
            "crime_group": ["Violent"],
            "occurrence_date": [f"{past}-06-01"],
        }
    )
    payload = build_coverage_metadata(
        crime_df=df, year=past, output_dir=str(tmp_path), verbose=False
    )
    assert payload["is_partial"] is False
    assert payload["fraction_elapsed"] == 1.0
    assert payload["as_of_date"] == f"{past}-12-31"
