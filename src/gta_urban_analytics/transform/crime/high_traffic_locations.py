"""
High-Traffic GTA Locations
==========================
A curated reference list of well-known high-foot-traffic destinations across the
Greater Toronto Area — shopping malls, hospitals, major attractions, and transit
hubs.

Police services routinely snap an incident to a venue's address centroid, so a
coordinate anomaly (many incidents piled on one identical lat/lon — see
``build_coordinate_anomalies``) that sits on top of one of these venues is at
least partly *organic*: a mall genuinely sees a lot of theft, a hospital a lot of
assaults. An anomaly with **no** nearby venue is more likely a pure
placeholder / geocoding artifact (e.g. a station address or a 0,0-style centroid).

``build_coordinate_anomalies`` uses :func:`classify_coordinate` to tag each
flagged coordinate as ``"high_traffic_area"`` (near a known venue) or
``"unexplained"`` (no nearby venue), so the visualization can render the two
classes distinctly.

Coordinates are WGS84 (EPSG:4326) lat/lon, accurate to ~100 m — comfortably
within the default 500 m match radius. This list is intentionally separate from
``analyze.py``'s York-only ``ANOMALY_LOCATIONS`` (UTM Zone 17N), which drives a
different, York-scoped 500 m filtering pass.
"""

from __future__ import annotations

import math
from typing import NamedTuple


class HighTrafficLocation(NamedTuple):
    """A named high-foot-traffic venue (WGS84 lat/lon)."""

    name: str
    category: str  # "mall" | "hospital" | "attraction" | "transit"
    lat: float
    lon: float


# A coordinate within this many metres of any venue below is classified as
# "high_traffic_area". 500 m matches analyze.py's FILTER_RADIUS_M convention and
# is generous enough to catch a venue-centroid snap.
DEFAULT_MATCH_RADIUS_M = 500.0

HIGH_TRAFFIC_LOCATIONS: list[HighTrafficLocation] = [
    # --- Shopping malls ---
    HighTrafficLocation("CF Toronto Eaton Centre", "mall", 43.6544, -79.3807),
    HighTrafficLocation("Yorkdale Shopping Centre", "mall", 43.7254, -79.4522),
    HighTrafficLocation("CF Sherway Gardens", "mall", 43.6113, -79.5572),
    HighTrafficLocation("Scarborough Town Centre", "mall", 43.7756, -79.2578),
    HighTrafficLocation("CF Fairview Mall", "mall", 43.7779, -79.3447),
    HighTrafficLocation("Square One Shopping Centre", "mall", 43.5934, -79.6442),
    HighTrafficLocation("Erin Mills Town Centre", "mall", 43.5510, -79.7170),
    HighTrafficLocation("Bramalea City Centre", "mall", 43.7180, -79.7170),
    HighTrafficLocation("Vaughan Mills", "mall", 43.8253, -79.5381),
    HighTrafficLocation("Promenade Mall", "mall", 43.8079, -79.4520),
    HighTrafficLocation("Hillcrest Mall", "mall", 43.8694, -79.4279),
    HighTrafficLocation("CF Markville", "mall", 43.8678, -79.2862),
    HighTrafficLocation("Pacific Mall", "mall", 43.8268, -79.3049),
    HighTrafficLocation("Upper Canada Mall", "mall", 44.0561, -79.4815),
    HighTrafficLocation("Pickering Town Centre", "mall", 43.8350, -79.0888),
    HighTrafficLocation("Oshawa Centre", "mall", 43.8979, -78.8776),
    HighTrafficLocation("Oakville Place", "mall", 43.4630, -79.6960),
    # --- Hospitals ---
    HighTrafficLocation("Toronto General Hospital", "hospital", 43.6587, -79.3884),
    HighTrafficLocation("Mount Sinai Hospital", "hospital", 43.6575, -79.3905),
    HighTrafficLocation("St. Michael's Hospital", "hospital", 43.6531, -79.3776),
    HighTrafficLocation("Toronto Western Hospital", "hospital", 43.6537, -79.4051),
    HighTrafficLocation("Sunnybrook Health Sciences Centre", "hospital", 43.7227, -79.3762),
    HighTrafficLocation("North York General Hospital", "hospital", 43.7681, -79.3640),
    HighTrafficLocation("Scarborough Health Network – General", "hospital", 43.7710, -79.2330),
    HighTrafficLocation("Mackenzie Health (Richmond Hill)", "hospital", 43.8783, -79.4360),
    HighTrafficLocation("Cortellucci Vaughan Hospital", "hospital", 43.8403, -79.5318),
    HighTrafficLocation("Markham Stouffville Hospital", "hospital", 43.8869, -79.2533),
    HighTrafficLocation("Southlake Regional Health Centre", "hospital", 44.0487, -79.4570),
    HighTrafficLocation("Trillium Health Partners – Mississauga", "hospital", 43.5520, -79.6090),
    HighTrafficLocation("Trillium Health Partners – Credit Valley", "hospital", 43.5470, -79.7140),
    HighTrafficLocation("William Osler – Brampton Civic", "hospital", 43.7510, -79.7290),
    HighTrafficLocation("Oakville Trafalgar Memorial Hospital", "hospital", 43.4470, -79.7170),
    HighTrafficLocation("Joseph Brant Hospital", "hospital", 43.3263, -79.7960),
    HighTrafficLocation("Lakeridge Health Oshawa", "hospital", 43.9120, -78.8520),
    # --- Attractions ---
    HighTrafficLocation("Canada's Wonderland", "attraction", 43.8430, -79.5390),
    HighTrafficLocation("Toronto Zoo", "attraction", 43.8205, -79.1810),
    HighTrafficLocation("Rogers Centre / CN Tower", "attraction", 43.6418, -79.3891),
    HighTrafficLocation("Exhibition Place / Ontario Place", "attraction", 43.6320, -79.4150),
    # --- Major transit hubs ---
    HighTrafficLocation("Union Station", "transit", 43.6453, -79.3806),
    HighTrafficLocation("Newmarket GO", "transit", 44.0490, -79.4640),
    HighTrafficLocation("Aurora GO", "transit", 43.9968, -79.4700),
]


def _haversine_m(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Great-circle distance in metres between two WGS84 points."""
    r = 6_371_000.0  # mean Earth radius, metres
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlmb = math.radians(lon2 - lon1)
    a = math.sin(dphi / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dlmb / 2) ** 2
    return 2 * r * math.asin(math.sqrt(a))


def classify_coordinate(
    lat: float, lon: float, radius_m: float = DEFAULT_MATCH_RADIUS_M
) -> tuple[HighTrafficLocation, float] | None:
    """Return the nearest high-traffic venue within ``radius_m``, else ``None``.

    Parameters:
        lat, lon: WGS84 coordinate to classify.
        radius_m: Match radius in metres (default 500 m).

    Returns:
        ``(HighTrafficLocation, distance_m)`` for the closest venue inside the
        radius, or ``None`` when no venue is near (or the coordinate is missing).
    """
    # NaN-safe (NaN != NaN) and None-safe guard.
    if lat is None or lon is None or lat != lat or lon != lon:
        return None

    best: HighTrafficLocation | None = None
    best_d = radius_m
    for loc in HIGH_TRAFFIC_LOCATIONS:
        d = _haversine_m(lat, lon, loc.lat, loc.lon)
        if d <= best_d:
            best, best_d = loc, d
    return (best, best_d) if best is not None else None
