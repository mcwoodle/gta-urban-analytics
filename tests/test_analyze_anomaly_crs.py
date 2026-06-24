"""Regression tests for audit finding F-02: the analyze.py anomaly filter must
reproject raw York x,y (EPSG:3857) to UTM 17N before the 500 m distance test."""

from pyproj import Transformer

from gta_urban_analytics.analyze.analyze import (
    is_near_anomaly,
    webmercator_to_utm17n,
    ANOMALY_LOCATIONS,
)

_UTM_TO_WM = Transformer.from_crs("EPSG:26917", "EPSG:3857", always_xy=True)


def test_webmercator_point_near_mall_is_flagged():
    ax, ay = ANOMALY_LOCATIONS["Vaughan Mills"]  # UTM 17N
    # Raw York-style coordinate (EPSG:3857) ~141 m from the mall.
    wm_x, wm_y = _UTM_TO_WM.transform(ax + 100, ay + 100)
    ux, uy = webmercator_to_utm17n(wm_x, wm_y)
    assert is_near_anomaly(ux, uy) is True


def test_far_point_is_not_flagged():
    ax, ay = ANOMALY_LOCATIONS["Vaughan Mills"]
    wm_x, wm_y = _UTM_TO_WM.transform(ax + 5000, ay + 5000)  # ~7 km away
    ux, uy = webmercator_to_utm17n(wm_x, wm_y)
    assert is_near_anomaly(ux, uy) is False


def test_raw_webmercator_coords_reproduce_the_old_no_op():
    # Feeding the un-reprojected Web Mercator coordinate (the pre-fix behaviour)
    # never matches a UTM anomaly — exactly why the old filter flagged nothing.
    ax, ay = ANOMALY_LOCATIONS["Vaughan Mills"]
    wm_x, wm_y = _UTM_TO_WM.transform(ax, ay)
    assert is_near_anomaly(wm_x, wm_y) is False
