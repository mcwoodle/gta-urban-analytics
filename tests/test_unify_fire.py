"""Tests for the fire-incident unifier: raw Toronto Fire Incidents → the
standardised fire_unified_schema (dates parsed, out-of-bounds coords dropped,
stable source_identifier)."""

import pandas as pd

from gta_urban_analytics.transform.fire.unify_fire import unify_fire


def _raw():
    return pd.DataFrame(
        {
            "Incident_Number": ["F1", "F2", "F3"],
            "Final_Incident_Type": ["01 - Fire", "03 - NO LOSS", "01 - Fire"],
            "Incident_Station_Area": ["311", "142 ", "0"],
            "Latitude": [43.70, 43.65, 0.0],          # third row is (0,0) → dropped
            "Longitude": [-79.40, -79.38, 0.0],
            "TFS_Alarm_Time": ["2019-05-01T10:00:00", "2020-11-15T22:30:00", "2021-01-01T00:00:00"],
            "Estimated_Dollar_Loss": [15000.0, None, 0.0],
            "Number_of_responding_personnel": [4.0, 8.0, 4.0],
        }
    )


def test_unifies_to_fire_schema(tmp_path):
    out = unify_fire(fire_df=_raw(), output_dir=str(tmp_path), verbose=False)
    # The (0,0) row is dropped as an out-of-bounds coordinate.
    assert len(out) == 2
    assert set(out.columns) >= {
        "source_identifier", "region", "municipality", "incident_type",
        "station_area", "occurrence_date", "lat", "lon",
        "estimated_dollar_loss", "responding_personnel",
    }
    assert (out["region"] == "Toronto").all()
    assert (out["municipality"] == "Toronto").all()


def test_source_identifier_and_dates(tmp_path):
    out = unify_fire(fire_df=_raw(), output_dir=str(tmp_path), verbose=False)
    first = out.iloc[0]
    assert first["source_identifier"] == "TorontoFire_F1"
    assert first["occurrence_date"] == "2019-05-01"
    # Station area whitespace is stripped.
    assert out["station_area"].tolist() == ["311", "142"]


def test_writes_csv(tmp_path):
    unify_fire(fire_df=_raw(), output_dir=str(tmp_path), verbose=False)
    written = pd.read_csv(tmp_path / "fire_incidents.csv")
    assert "station_area" in written.columns
    assert len(written) == 2


def _brampton_raw():
    # BFES residential fires: DATE_ is YY/MM/DD, lat/lon from the GeoJSON download.
    return pd.DataFrame(
        {
            "FIRE": ["1200362-00", "1300050-00"],
            "DATE_": ["12/01/03", "13/02/04"],
            "PROPERTY_CLASS_DESC": ["Detached Dwelling", "Apartment"],
            "CAUSE_DESC": ["Cooking", "Electrical"],
            "lat": [43.74, 43.70],
            "lon": [-79.75, -79.80],
        }
    )


def test_brampton_incidents_appended(tmp_path):
    out = unify_fire(
        fire_df=_raw(), brampton_df=_brampton_raw(),
        output_dir=str(tmp_path), verbose=False,
    )
    bram = out[out["municipality"] == "Brampton"]
    assert len(bram) == 2
    assert (bram["region"] == "Peel").all()
    assert (bram["incident_type"] == "Residential Fire").all()
    assert set(bram["source_identifier"]) == {
        "BramptonFire_1200362-00", "BramptonFire_1300050-00",
    }
    # DATE_ "12/01/03" is YY/MM/DD → 2012-01-03.
    assert sorted(bram["occurrence_date"]) == ["2012-01-03", "2013-02-04"]
    # Toronto rows are still present (the two in-bounds incidents).
    assert (out["municipality"] == "Toronto").sum() == 2


def test_brampton_skipped_when_not_provided(tmp_path):
    # In test mode (fire_df passed), the Brampton CSV is never read from disk.
    out = unify_fire(fire_df=_raw(), output_dir=str(tmp_path), verbose=False)
    assert "Brampton" not in set(out["municipality"])
