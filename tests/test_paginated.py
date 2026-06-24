"""Regression tests for audit finding F-12: the paginated downloader must stop on
an empty page (no infinite loop) and build CSV headers from the UNION of every
feature's properties (not just the first feature's)."""

import pandas as pd

from gta_urban_analytics.extract.arcgis.paginated import (
    _paginate_features,
    _collect_headers,
    _feature_to_row,
    _write_features_csv,
)


def test_paginate_stops_on_empty_page_even_if_exceeded():
    # Server keeps claiming exceededTransferLimit but returns an empty 2nd page.
    pages = [
        {"features": [{"properties": {"a": 1}}], "properties": {"exceededTransferLimit": True}},
        {"features": [], "properties": {"exceededTransferLimit": True}},
    ]
    calls = {"n": 0}

    def fetch(offset, size):
        i = calls["n"]
        calls["n"] += 1
        return pages[i] if i < len(pages) else {"features": [], "properties": {}}

    feats = _paginate_features(fetch, page_size=1)
    assert len(feats) == 1
    assert calls["n"] == 2  # stopped right after the empty page, no infinite loop


def test_paginate_stops_when_not_exceeded():
    def fetch(offset, size):
        return {"features": [{"properties": {"a": 1}}], "properties": {"exceededTransferLimit": False}}

    assert len(_paginate_features(fetch, page_size=1)) == 1


def test_collect_headers_unions_all_feature_keys():
    feats = [
        {"properties": {"a": 1}},
        {"properties": {"b": 2, "c": 3}},  # keys missing from the first feature
    ]
    assert _collect_headers(feats) == ["a", "b", "c", "lat", "lon"]


def test_feature_to_row_extracts_point_coords():
    feat = {"properties": {"a": 1}, "geometry": {"type": "Point", "coordinates": [-79.4, 43.7]}}
    row = _feature_to_row(feat, _collect_headers([feat]))
    assert (row["lat"], row["lon"], row["a"]) == (43.7, -79.4, 1)


def test_write_features_csv_uses_union_headers(tmp_path):
    feats = [
        {"properties": {"a": 1}, "geometry": {"type": "Point", "coordinates": [-79.4, 43.7]}},
        {"properties": {"a": 2, "b": 9}, "geometry": None},
    ]
    out = tmp_path / "x.csv"
    _write_features_csv(feats, str(out))

    df = pd.read_csv(out)
    assert list(df.columns) == ["a", "b", "lat", "lon"]
    assert df.loc[0, "lat"] == 43.7
    assert df.loc[1, "a"] == 2
