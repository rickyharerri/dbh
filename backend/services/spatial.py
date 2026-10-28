"""Distance helpers. Distances are great-circle kilometres; coordinate order is (lat, lon)."""
from __future__ import annotations

import math

EARTH_RADIUS_KM = 6371.0088


def haversine_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dphi = p2 - p1
    dlmb = math.radians(lon2 - lon1)
    a = math.sin(dphi / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dlmb / 2) ** 2
    return 2 * EARTH_RADIUS_KM * math.asin(min(1.0, math.sqrt(a)))


def bounding_box(lat: float, lon: float, radius_km: float) -> dict[str, float]:
    """A cheap pre-filter box that fully contains the search circle.

    Lets the warehouse prune rows before evaluating the haversine expression.
    """
    dlat = math.degrees(radius_km / EARTH_RADIUS_KM)
    cos_lat = max(math.cos(math.radians(lat)), 1e-6)
    dlon = math.degrees(radius_km / (EARTH_RADIUS_KM * cos_lat))
    # small safety margin so the box can never clip a point inside the circle
    dlat *= 1.01
    dlon *= 1.01
    return {
        "min_lat": lat - dlat,
        "max_lat": lat + dlat,
        "min_lon": lon - dlon,
        "max_lon": lon + dlon,
    }


def haversine_sql(lat_col: str, lon_col: str) -> str:
    """Spark SQL great-circle distance (km) from columns to the :lat/:lon parameters."""
    return (
        f"2 * {EARTH_RADIUS_KM} * asin(sqrt("
        f"pow(sin(radians(({lat_col} - :lat) / 2)), 2) + "
        f"cos(radians(:lat)) * cos(radians({lat_col})) * "
        f"pow(sin(radians(({lon_col} - :lon) / 2)), 2)))"
    )


def valid_coordinate(lat: float | None, lon: float | None) -> bool:
    if lat is None or lon is None:
        return False
    if not (math.isfinite(lat) and math.isfinite(lon)):
        return False
    if not (-90 <= lat <= 90 and -180 <= lon <= 180):
        return False
    return not (lat == 0 and lon == 0)  # (0,0) is a classic placeholder for "no location"
