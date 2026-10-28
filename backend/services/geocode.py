"""Optional place-name search. Enabled only when GEOCODER_URL is set
(any Nominatim-compatible /search endpoint). Results are limited to Alberta."""
from __future__ import annotations

import httpx

from backend.config import Settings
from backend.errors import DatabricksUnavailable, ServiceNotConfigured

ALBERTA_BOX = {"min_lat": 48.99, "max_lat": 60.01, "min_lon": -120.01, "max_lon": -109.99}


def search_places(s: Settings, query: str) -> list[dict]:
    if not s.geocoder_url:
        raise ServiceNotConfigured("Place search is not configured", ["GEOCODER_URL"])
    params = {
        "q": query, "format": "jsonv2", "limit": 6, "countrycodes": "ca",
        "viewbox": f"{ALBERTA_BOX['min_lon']},{ALBERTA_BOX['max_lat']},{ALBERTA_BOX['max_lon']},{ALBERTA_BOX['min_lat']}",
        "bounded": 1,
    }
    try:
        r = httpx.get(s.geocoder_url, params=params, timeout=6.0, headers={"User-Agent": "aquawise-alberta/1.0"})
        r.raise_for_status()
        raw = r.json()
    except Exception as exc:  # noqa: BLE001
        raise DatabricksUnavailable("geocoder failed") from exc
    out = []
    for item in raw if isinstance(raw, list) else []:
        try:
            lat, lon = float(item["lat"]), float(item["lon"])
        except (KeyError, TypeError, ValueError):
            continue
        if ALBERTA_BOX["min_lat"] <= lat <= ALBERTA_BOX["max_lat"] and ALBERTA_BOX["min_lon"] <= lon <= ALBERTA_BOX["max_lon"]:
            out.append({"name": str(item.get("display_name", ""))[:200], "latitude": lat, "longitude": lon})
    return out
