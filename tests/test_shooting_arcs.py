"""Regression test for audit finding F-11: shooting-arc detection must match the
canonical 'Weapons Offences' category (the old code checked 'Weapons', which never
exists, so weapon incidents without 'shoot'/'firearm' in their text were dropped)."""

import pandas as pd

from gta_urban_analytics.transform.crime.build_shooting_arcs import build_shooting_arcs


def test_weapons_offences_incident_is_detected(tmp_path):
    crime_df = pd.DataFrame(
        {
            "mapped_crime_category": ["Weapons Offences", "Assault", "Auto Theft"],
            # Note: no 'shoot'/'firearm' in the weapons row's text, so it can only
            # be caught via the mapped-category branch.
            "original_crime_type": [
                "Possession of a weapon",
                "Assault Level 1",
                "Theft of motor vehicle",
            ],
            "occurrence_date": ["2025-01-01", "2025-01-02", "2025-01-03"],
            "lat": [43.85, 43.86, 43.87],
            "lon": [-79.05, -79.06, -79.07],
            "municipality": ["Markham", "Markham", "Markham"],
        }
    )

    out = build_shooting_arcs(crime_df=crime_df, output_dir=str(tmp_path), verbose=False)

    assert len(out) == 1
    assert out.iloc[0]["src_lat"] == 43.85
    assert out.iloc[0]["municipality"] == "Markham"
