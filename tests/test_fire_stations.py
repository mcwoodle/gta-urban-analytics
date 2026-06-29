"""Tests for the fire-station volume builder: unified incidents are grouped by
station_area and joined to station points, yielding fires_handled per station.
Covers the float-key normalisation ("115.0" → "115") that the join depends on."""

import pandas as pd

from gta_urban_analytics.transform.fire.build_fire_stations import build_fire_stations


def _stations():
    # Two stations with GeoJSON Point geometry strings, as the CKAN CSV provides.
    return pd.DataFrame(
        {
            "STATION": [311, 142],
            "MUNICIPALITY_NAME": ["former Toronto", "North York"],
            "ADDRESS": ["1 Main St", "2 Yonge St"],
            "geometry": [
                '{"type": "Point", "coordinates": [-79.40, 43.70]}',
                '{"type": "Point", "coordinates": [-79.38, 43.75]}',
            ],
        }
    )


def _incidents():
    # 3 incidents for station 311, 1 for 142, 1 for an unknown station (999).
    return pd.DataFrame(
        {
            "station_area": ["311", "311", "311", "142", "999"],
            "estimated_dollar_loss": [1000.0, 2000.0, 0.0, 500.0, 100.0],
            "lat": [43.70, 43.70, 43.70, 43.75, 43.6],
            "lon": [-79.40, -79.40, -79.40, -79.38, -79.5],
        }
    )


def test_fires_handled_grouping(tmp_path):
    out = build_fire_stations(
        fire_df=_incidents(), stations_df=_stations(),
        output_dir=str(tmp_path), verbose=False,
    )
    by_station = out.set_index("station")["fires_handled"].to_dict()
    assert by_station["311"] == 3
    assert by_station["142"] == 1
    # The unknown station (999) has no physical station → not in the layer.
    assert "999" not in by_station


def test_dollar_loss_summed(tmp_path):
    out = build_fire_stations(
        fire_df=_incidents(), stations_df=_stations(),
        output_dir=str(tmp_path), verbose=False,
    )
    s311 = out[out["station"] == "311"].iloc[0]
    assert s311["total_dollar_loss"] == 3000.0


def test_join_handles_float_station_keys(tmp_path):
    # When a CSV round-trip makes station numbers floats ("311.0"), the join must
    # still match the integer-style station ids.
    inc = _incidents().copy()
    inc["station_area"] = ["311.0", "311.0", "311.0", "142.0", "999.0"]
    out = build_fire_stations(
        fire_df=inc, stations_df=_stations(),
        output_dir=str(tmp_path), verbose=False,
    )
    assert out.set_index("station")["fires_handled"].to_dict()["311"] == 3


def _brampton_stations():
    # Raw municipal station CSV as the ArcGIS GeoJSON download provides it.
    return pd.DataFrame(
        {
            "FIRE_STATION_NUMBER": ["203", "204"],
            "FIRE_STN_ADDRESS": ["425 CHRYSLER DR", "1 MAIN ST"],
            "ACCESS_FROM": ["CHRYSLER DR", "MAIN ST"],
            "lat": [43.70, 43.72],
            "lon": [-79.75, -79.76],
        }
    )


def test_municipal_stations_appended_without_volume(tmp_path):
    out = build_fire_stations(
        fire_df=_incidents(), stations_df=_stations(),
        municipal_station_dfs={"Brampton": _brampton_stations()},
        output_dir=str(tmp_path), verbose=False,
    )
    bram = out[out["municipality"] == "Brampton"]
    assert len(bram) == 2
    assert (bram["region"] == "Peel").all()
    # Location-only: no volume reading, flagged so the map can distinguish them.
    assert (~bram["has_volume"]).all()
    assert bram["fires_handled"].isna().all()
    assert out.set_index("station").loc["203", "address"] == "425 CHRYSLER DR"
    # Toronto stations still carry volume.
    tor = out[out["region"] == "Toronto"]
    assert tor["has_volume"].all()
    assert tor.set_index("station")["fires_handled"].to_dict()["311"] == 3


def test_municipal_stations_skipped_in_test_mode(tmp_path):
    # When stations_df is passed and no municipal frames are given, nothing is
    # read from disk — output is Toronto-only.
    out = build_fire_stations(
        fire_df=_incidents(), stations_df=_stations(),
        output_dir=str(tmp_path), verbose=False,
    )
    assert (out["region"] == "Toronto").all()
    assert out["has_volume"].all()
