"""
Crime-Group Buckets (15 → 4)
============================
Collapses the 15 canonical crime categories into 4 high-level buckets so the
viz can colour / filter by crime *type* without lumping everything together:

    Violent · Property · Nuisance · Other

ALL bucketing lives here in the pipeline (mirroring the sibling
``_DURHAM_CANONICAL_CATEGORY`` / ``_MUNICIPALITY_ALIASES`` constants in
``unify_datasets.py``); the Kepler viz only renders the resulting
``crime_group`` column.

Judgment calls (documented for the normalization-strategy doc):
  - **Weapons Offences → Violent.** A firearm/weapon offence is treated as an
    interpersonal-violence indicator rather than a property/nuisance one.
  - **Impaired Driving & Traffic → Nuisance.** Public-order / regulatory rather
    than an offence against a specific victim's person or property.
  - **MULTIPLE → Other.** A multi-offence incident already had its category
    overwritten to ``MULTIPLE`` by the dedup step, so it can't be assigned to a
    single bucket; it (and any unmapped ``Other``) fall to the Other bucket.
    The per-region ``MULTIPLE`` count is surfaced in ``coverage.json`` so this
    folding stays auditable.
"""

from __future__ import annotations

import pandas as pd

# 4 buckets → their member canonical categories. The 15 canonical categories
# are partitioned across exactly these four lists (Missing Person is the only
# member of Other besides the runtime MULTIPLE / unmapped values).
CRIME_GROUPS: dict[str, list[str]] = {
    "Violent": [
        "Assault",
        "Sexual Offences",
        "Robbery",
        "Homicide",
        "Threats & Harassment",
        "Weapons Offences",  # judgment call — see module docstring
    ],
    "Property": [
        "Break & Enter",
        "Theft",
        "Auto Theft",
        "Fraud",
        "Property Damage",
    ],
    "Nuisance": [
        "Public Order",
        "Drug Offences",
        "Impaired Driving & Traffic",  # judgment call — see module docstring
    ],
    "Other": [
        "Missing Person",
        # plus runtime-only MULTIPLE and any unmapped "Other" (handled by the
        # .fillna('Other') in assign_crime_group — no need to list them here).
    ],
}

# Inverse map (canonical category → bucket display name), built once at import.
CATEGORY_TO_GROUP: dict[str, str] = {
    category: group
    for group, categories in CRIME_GROUPS.items()
    for category in categories
}

# Display name → URL/column slug, used for the per-bucket rate column names
# (crime_rate_<slug>_per_1k) and the viz control.
GROUP_SLUGS: dict[str, str] = {
    "Violent": "violent",
    "Property": "property",
    "Nuisance": "nuisance",
    "Other": "other",
}


def assign_crime_group(df: pd.DataFrame) -> pd.DataFrame:
    """Add a ``crime_group`` column derived from ``mapped_crime_category``.

    Must run *after* deduplication — ``deduplicate_incidents`` overwrites
    ``mapped_crime_category`` to ``MULTIPLE`` for multi-offence incidents, so
    deriving the group any earlier would be inconsistent. Categories with no
    bucket (``MULTIPLE``, unmapped ``Other``, anything unexpected) fall to the
    ``Other`` bucket. Idempotent: re-running simply recomputes the column.
    """
    df = df.copy()
    df["crime_group"] = (
        df["mapped_crime_category"].map(CATEGORY_TO_GROUP).fillna("Other")
    )
    return df
