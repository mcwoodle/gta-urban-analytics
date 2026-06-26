"""Tests for the 15 → 4 crime-group bucketing (Violent / Property / Nuisance /
Other). All bucketing lives in the pipeline; the viz only renders the column."""

import json
import os

import pandas as pd

from gta_urban_analytics.transform.crime.crime_groups import (
    CRIME_GROUPS,
    CATEGORY_TO_GROUP,
    GROUP_SLUGS,
    assign_crime_group,
)

# The 15 canonical categories, read from the mapping file the pipeline uses.
_MAPPINGS_PATH = os.path.join(
    os.path.dirname(__file__),
    "..",
    "src",
    "gta_urban_analytics",
    "transform",
    "crime",
    "crime_category_mappings.json",
)


def _canonical_categories() -> set[str]:
    with open(_MAPPINGS_PATH) as f:
        return set(json.load(f).values())


def test_every_canonical_category_maps_exactly_once():
    canonical = _canonical_categories()
    # Every canonical value the mapping file emits has a bucket.
    assert canonical <= set(CATEGORY_TO_GROUP), (
        f"Unbucketed categories: {canonical - set(CATEGORY_TO_GROUP)}"
    )
    # And every bucketed category is one of the canonical 15 (no typos/strays).
    assert set(CATEGORY_TO_GROUP) == canonical
    # No category appears in two buckets.
    seen = [c for cats in CRIME_GROUPS.values() for c in cats]
    assert len(seen) == len(set(seen))


def test_known_bucket_assignments():
    assert CATEGORY_TO_GROUP["Assault"] == "Violent"
    assert CATEGORY_TO_GROUP["Weapons Offences"] == "Violent"  # judgment call
    assert CATEGORY_TO_GROUP["Auto Theft"] == "Property"
    assert CATEGORY_TO_GROUP["Fraud"] == "Property"
    assert CATEGORY_TO_GROUP["Impaired Driving & Traffic"] == "Nuisance"  # judgment
    assert CATEGORY_TO_GROUP["Drug Offences"] == "Nuisance"
    assert CATEGORY_TO_GROUP["Missing Person"] == "Other"


def test_group_slugs_cover_all_buckets():
    assert set(GROUP_SLUGS) == set(CRIME_GROUPS)
    assert set(GROUP_SLUGS.values()) == {"violent", "property", "nuisance", "other"}


def test_assign_crime_group_folds_multiple_and_unknown_to_other():
    df = pd.DataFrame(
        {
            "mapped_crime_category": [
                "Assault",
                "Break & Enter",
                "MULTIPLE",
                "Other",
                "Something Unmapped",
                None,
            ]
        }
    )
    out = assign_crime_group(df)
    assert list(out["crime_group"]) == [
        "Violent",
        "Property",
        "Other",  # MULTIPLE → Other
        "Other",  # unmapped runtime "Other" → Other
        "Other",  # genuinely unknown → Other
        "Other",  # NaN → Other
    ]
    # Original frame not mutated in place.
    assert "crime_group" not in df.columns


def test_assign_crime_group_idempotent():
    df = pd.DataFrame({"mapped_crime_category": ["Assault", "Theft", "MULTIPLE"]})
    once = assign_crime_group(df)
    twice = assign_crime_group(once)
    assert list(once["crime_group"]) == list(twice["crime_group"])
