"""Tests for the pipeline orchestration (audit F-17): phase 1 threads the working
frame and writes unified_data.csv; phase 2 builds the derived products. Aborts
cleanly when there is no data."""

from unittest import mock

import pandas as pd

import gta_urban_analytics.transform.pipeline as pipe

_DERIVED = [
    "build_gta_census_geojson", "enrich_census_with_crime_rate",
    "build_municipality_choropleth", "build_coverage_metadata",
    "build_shooting_arcs", "build_coordinate_anomalies", "build_standalone_compact",
    "partition_all_years",
]


def _patch_derived(monkeypatch):
    mocks = {}
    for name in _DERIVED:
        m = mock.Mock(name=name)
        monkeypatch.setattr(pipe, name, m)
        mocks[name] = m
    return mocks


def test_run_aborts_on_empty_unify(monkeypatch):
    monkeypatch.setattr(pipe, "unify_datasets", lambda: pd.DataFrame())
    monkeypatch.setattr(pipe, "verify_mappings", mock.Mock())
    monkeypatch.setattr(pipe, "filter_invalid_incidents", mock.Mock())
    monkeypatch.setattr(pipe, "deduplicate_incidents", mock.Mock())
    monkeypatch.setattr(pipe, "assign_crime_group", mock.Mock())
    mocks = _patch_derived(monkeypatch)

    pipe.run()

    # With no data, nothing past unify runs and no derived product is built.
    pipe.filter_invalid_incidents.assert_not_called()
    for m in mocks.values():
        m.assert_not_called()


def test_run_threads_transform_then_builds_derived(tmp_path, monkeypatch):
    df = pd.DataFrame({"source_identifier": ["A"], "region": ["Toronto"]})
    monkeypatch.setattr(pipe, "_project_root", str(tmp_path))
    monkeypatch.setattr(pipe, "unify_datasets", lambda: df)
    monkeypatch.setattr(pipe, "verify_mappings", mock.Mock())
    monkeypatch.setattr(pipe, "filter_invalid_incidents", lambda d, verbose=True: d)
    monkeypatch.setattr(pipe, "deduplicate_incidents", lambda d, verbose=True: d)
    monkeypatch.setattr(pipe, "assign_crime_group", lambda d: d)
    mocks = _patch_derived(monkeypatch)

    pipe.run()

    # Phase 1 wrote the unified CSV (the hand-off to phase 2).
    out = tmp_path / "data" / "02_transformed" / "unified_data.csv"
    assert out.exists()
    assert list(pd.read_csv(out)["source_identifier"]) == ["A"]
    # verify ran on the frame; every derived product ran exactly once.
    pipe.verify_mappings.assert_called_once()
    for m in mocks.values():
        m.assert_called_once()
