"""SYNTHETIC demo fixtures.

These wells are randomly generated (fixed seed) for UI development and demos only.
They are NOT Alberta Water Well Information Database records and must never be
presented as findings. Every demo response is tagged data_source="demo" and the UI
shows a persistent banner.
"""
from __future__ import annotations

import random
from datetime import date, timedelta
from functools import lru_cache

# (lat, lon, spread in degrees latitude, well count) — arbitrary cluster centres across Alberta
CLUSTERS = [
    (51.19, -114.47, 0.14, 1600),
    (50.73, -113.98, 0.14, 1600),
    (52.27, -113.81, 0.14, 1200),
    (53.55, -113.49, 0.16, 1500),
    (49.69, -112.83, 0.14, 900),
    (55.17, -118.80, 0.14, 600),
]
PARAMETERS = [
    ("Iron", 0.2, 1.0),
    ("Nitrate", 2.0, 1.0),
    ("Total dissolved solids", 450.0, 0.6),
    ("Manganese", 0.05, 1.0),
    ("Arsenic", 0.003, 1.0),
]
STATUSES = ["Active", "Active", "Active", "Abandoned", "Unknown"]


@lru_cache(maxsize=1)
def demo_wells() -> list[dict]:
    rnd = random.Random(20260428)
    wells: list[dict] = []
    n = 0
    for clat, clon, spread, count in CLUSTERS:
        for _ in range(count):
            n += 1
            lat = rnd.gauss(clat, spread)
            lon = rnd.gauss(clon, spread * 1.6)  # wider in longitude: degrees are shorter there
            depth = None if rnd.random() < 0.08 else round(min(250.0, max(8.0, rnd.lognormvariate(4.25, 0.45))), 1)
            yld = None if rnd.random() < 0.15 else (0.0 if rnd.random() < 0.02 else round(rnd.lognormvariate(2.1, 0.8), 1))
            swl = None if depth is None or rnd.random() < 0.2 else round(depth * rnd.uniform(0.1, 0.6), 1)
            drilled = date(1950, 1, 1) + timedelta(days=rnd.randint(0, (date(2023, 12, 31) - date(1950, 1, 1)).days))
            wells.append({
                "well_id": f"DEMO-{n:05d}",
                "latitude": round(lat, 6),
                "longitude": round(lon, 6),
                "depth": depth,
                "well_yield": yld,
                "static_water_level": swl,
                "drilling_date": drilled.isoformat() if rnd.random() > 0.05 else None,
                "status": rnd.choice(STATUSES),
            })
    return wells


@lru_cache(maxsize=1)
def demo_quality() -> dict[str, list[dict]]:
    rnd = random.Random(7)
    out: dict[str, list[dict]] = {}
    for w in demo_wells():
        if rnd.random() > 0.12:
            continue
        rows = []
        for name, median, sigma in rnd.sample(PARAMETERS, rnd.randint(1, 4)):
            sample = date(1990, 1, 1) + timedelta(days=rnd.randint(0, 12000))
            if name == "Arsenic" and rnd.random() < 0.3:
                rows.append({"parameter": name, "value": None, "value_raw": "<0.001", "unit": "mg/L",
                             "sample_date": sample.isoformat()})
                continue
            value = round(rnd.lognormvariate(__import__("math").log(median), sigma), 4)
            rows.append({"parameter": name, "value": value, "value_raw": str(value), "unit": "mg/L",
                         "sample_date": sample.isoformat()})
        out[w["well_id"]] = rows
    return out
