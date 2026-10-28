"""Data access. Routes depend on the `Repository` protocol, never on Databricks directly,
so tests can inject fakes and demo mode can run without credentials."""
from __future__ import annotations

import logging
import threading
from pathlib import Path
from typing import Optional, Protocol

from backend.config import Settings
from backend.errors import ServiceNotConfigured
from backend.models import (
    Capabilities,
    NearbyResponse,
    Point,
    QualityMeasurement,
    QualityParameterSummary,
    QualityResponse,
    SummaryResponse,
    Units,
    Well,
    WellDetails,
)
from backend.services import queries as Q
from backend.services import statistics as st
from backend.services.cache import TTLCache
from backend.services.databricks import DatabricksClient
from backend.services.demo_data import demo_quality, demo_wells
from backend.services.quality import GuidelineSet, evaluate, load_guidelines
from backend.services.spatial import haversine_km
from backend.services.summary_builder import Aggregates, aggregates_from_rows, build_summary

log = logging.getLogger(__name__)
DEMO_GUIDELINES = Path(__file__).resolve().parent.parent / "data" / "guidelines.demo.json"
QUALITY_ROW_LIMIT = 300


class Repository(Protocol):
    mode: str  # "live" | "demo" | "unconfigured"

    def capabilities(self) -> Capabilities: ...
    def nearby(self, lat: float, lon: float, radius_km: float, limit: int) -> NearbyResponse: ...
    def summary(self, lat: float, lon: float, radius_km: float) -> SummaryResponse: ...
    def well_details(self, well_id: str) -> Optional[WellDetails]: ...
    def water_quality(self, lat: float, lon: float, radius_km: float) -> QualityResponse: ...
    def ping(self) -> dict: ...


def _well(row: dict) -> Well:
    f = lambda k: float(row[k]) if row.get(k) is not None else None  # noqa: E731
    return Well(
        well_id=str(row["well_id"]),
        latitude=float(row["latitude"]),
        longitude=float(row["longitude"]),
        distance_km=round(float(row["distance_km"]), 3),
        depth=f("depth"), well_yield=f("well_yield"), static_water_level=f("static_water_level"),
        drilling_date=str(row["drilling_date"])[:10] if row.get("drilling_date") else None,
        status=row.get("status"),
    )


def _measurement(row: dict, guidelines: GuidelineSet) -> QualityMeasurement:
    m = QualityMeasurement(
        well_id=str(row.get("well_id", "")),
        distance_km=round(float(row["distance_km"]), 3) if row.get("distance_km") is not None else None,
        parameter=str(row["parameter"]),
        value=float(row["value"]) if row.get("value") is not None else None,
        value_raw=row.get("value_raw"),
        unit=row.get("unit"),
        sample_date=str(row["sample_date"])[:10] if row.get("sample_date") else None,
    )
    return evaluate(m, guidelines)


# ============================================================ Databricks (live)
class DatabricksRepository:
    mode = "live"

    def __init__(self, settings: Settings, client: DatabricksClient | None = None):
        self.s = settings
        self.db = client or DatabricksClient(settings)
        self.cache = TTLCache(settings.cache_ttl_s)
        self.guidelines = load_guidelines(settings.quality_guidelines_file)
        self._verified = False
        self._lock = threading.Lock()

    # -- capabilities derive purely from the env mapping (never guessed)
    def capabilities(self) -> Capabilities:
        s = self.s
        has = lambda k: k in s.well_columns  # noqa: E731
        return Capabilities(
            depth=has("depth"), well_yield=has("well_yield"),
            static_water_level=has("static_water_level"), drilling_date=has("drilling_date"),
            status=has("status"), quality=s.quality_enabled,
            units=Units(depth=s.depth_unit, well_yield=s.yield_unit, static_water_level=s.static_water_level_unit),
            low_yield_threshold=s.low_yield_threshold if has("well_yield") else None,
            source_dataset=f"{s.catalog}.{s.schema}.{s.wells_table}" if s.wells_table else None,
        )

    def _ready(self) -> None:
        s = self.s
        missing = s.missing_mapping()
        if missing:
            raise ServiceNotConfigured("The well table mapping is incomplete", missing)
        bad = s.mapping_errors()
        if bad:
            raise ServiceNotConfigured("The table mapping contains unsafe identifiers", bad)
        self._verify_mapping()

    def _verify_mapping(self) -> None:
        """Confirm every mapped table/column really exists (allowlist check against Unity Catalog)."""
        if self._verified:
            return
        with self._lock:
            if self._verified:
                return
            s, problems = self.s, []
            targets = [(s.wells_table, s.well_columns)]
            if s.quality_table:
                targets.append((s.quality_table, s.quality_columns))
            for table, mapping in targets:
                rows = self.db.query(Q.mapped_columns_check(s, table))
                actual = {str(r["column_name"]).lower() for r in rows}
                if not actual:
                    problems.append(f"table {table} not found or not readable")
                    continue
                problems += [f"column {c} not in {table}" for c in mapping.values() if c.lower() not in actual]
            if problems:
                raise ServiceNotConfigured("Mapped tables/columns were not found in Unity Catalog", problems)
            self._verified = True

    # -- endpoints
    def nearby(self, lat, lon, radius_km, limit) -> NearbyResponse:
        self._ready()
        return self.cache.get_or_set(("nearby", lat, lon, radius_km, limit), lambda: self._nearby(lat, lon, radius_km, limit))

    def _nearby(self, lat, lon, radius_km, limit) -> NearbyResponse:
        rows = self.db.query(Q.nearby_wells(self.s, lat, lon, radius_km, limit))
        total = int(rows[0]["total_wells"]) if rows else 0
        wells = [_well(r) for r in rows]
        caps = self.capabilities()
        return NearbyResponse(
            location=Point(latitude=lat, longitude=lon), radius_km=radius_km, total_wells=total,
            returned_wells=len(wells), limit=limit, truncated=total > len(wells),
            units=caps.units, capabilities=caps, wells=wells, data_source="databricks",
        )

    def summary(self, lat, lon, radius_km) -> SummaryResponse:
        self._ready()
        return self.cache.get_or_set(("summary", lat, lon, radius_km), lambda: self._summary(lat, lon, radius_km))

    def _summary(self, lat, lon, radius_km) -> SummaryResponse:
        stats, hist = self.db.query_many(
            [Q.summary_stats(self.s, lat, lon, radius_km), Q.histograms(self.s, lat, lon, radius_km)]
        )
        agg = aggregates_from_rows(stats[0] if stats else None, hist)
        return build_summary(self.s, self.capabilities(), lat, lon, radius_km, agg, "databricks")

    def well_details(self, well_id: str) -> Optional[WellDetails]:
        self._ready()
        return self.cache.get_or_set(("well", well_id), lambda: self._well_details(well_id))

    def _well_details(self, well_id: str) -> Optional[WellDetails]:
        queries = [Q.well_by_id(self.s, well_id)]
        if self.s.quality_enabled:
            queries.append(Q.quality_for_well(self.s, well_id))
        results = self.db.query_many(queries)
        if not results[0]:
            return None
        r, caps = results[0][0], self.capabilities()
        quality = [_measurement({**q, "well_id": well_id}, self.guidelines) for q in results[1]] if len(results) > 1 else []
        f = lambda k: float(r[k]) if r.get(k) is not None else None  # noqa: E731
        return WellDetails(
            well_id=str(r["well_id"]), latitude=float(r["latitude"]), longitude=float(r["longitude"]),
            depth=f("depth"), well_yield=f("well_yield"), static_water_level=f("static_water_level"),
            drilling_date=str(r["drilling_date"])[:10] if r.get("drilling_date") else None,
            status=r.get("status"), units=caps.units, capabilities=caps, quality=quality,
            source_dataset=caps.source_dataset, data_source="databricks",
        )

    def water_quality(self, lat, lon, radius_km) -> QualityResponse:
        self._ready()
        if not self.s.quality_enabled:
            return _quality_unavailable(lat, lon, radius_km, "databricks", self.guidelines,
                                        "No water-quality table is mapped for this dataset (set QUALITY_TABLE and QUALITY_COL_* variables).")
        return self.cache.get_or_set(("quality", lat, lon, radius_km), lambda: self._quality(lat, lon, radius_km))

    def _quality(self, lat, lon, radius_km) -> QualityResponse:
        rows, params = self.db.query_many(
            [Q.quality_measurements(self.s, lat, lon, radius_km, QUALITY_ROW_LIMIT),
             Q.quality_parameters(self.s, lat, lon, radius_km)]
        )
        total = int(rows[0]["total_records"]) if rows else 0
        measurements = [_measurement(r, self.guidelines) for r in rows]
        return QualityResponse(
            location=Point(latitude=lat, longitude=lon), radius_km=radius_km, available=True,
            total_records=total, returned_records=len(measurements),
            parameters=[QualityParameterSummary(
                parameter=str(p["parameter"]), observations=int(p["observations"]), wells=int(p["wells"]),
                latest_sample_date=str(p["latest_sample_date"])[:10] if p.get("latest_sample_date") else None,
            ) for p in params],
            measurements=measurements, guideline=self.guidelines.info(),
            explanation=None if total else "No water-quality measurements are available for this selection.",
            data_source="databricks",
        )

    def ping(self) -> dict:
        out: dict = {"reachable": False, "mapping_problems": []}
        try:
            out["reachable"] = self.db.ping()
            self._ready()
        except ServiceNotConfigured as exc:
            out["mapping_problems"] = exc.missing or [exc.what]
        except Exception:  # noqa: BLE001
            pass
        return out


def _quality_unavailable(lat, lon, radius_km, source, guidelines, why) -> QualityResponse:
    return QualityResponse(
        location=Point(latitude=lat, longitude=lon), radius_km=radius_km, available=False,
        total_records=0, returned_records=0, parameters=[], measurements=[],
        guideline=guidelines.info(), explanation=why, data_source=source,
    )


# ============================================================ Demo (synthetic fixtures)
class DemoRepository:
    mode = "demo"

    def __init__(self, settings: Settings):
        self.s = settings
        self.guidelines = load_guidelines(str(DEMO_GUIDELINES))

    def capabilities(self) -> Capabilities:
        return Capabilities(
            depth=True, well_yield=True, static_water_level=True, drilling_date=True, status=True,
            quality=True, units=Units(depth="m", well_yield="gpm", static_water_level="m"),
            low_yield_threshold=self.s.low_yield_threshold if self.s.low_yield_threshold is not None else 3.0,
            source_dataset="SYNTHETIC DEMO FIXTURE (not real Alberta records)",
        )

    def _within(self, lat, lon, radius_km) -> list[dict]:
        out = []
        for w in demo_wells():
            d = haversine_km(lat, lon, w["latitude"], w["longitude"])
            if d <= radius_km:
                out.append({**w, "distance_km": d})
        out.sort(key=lambda r: (r["distance_km"], r["well_id"]))
        return out

    def nearby(self, lat, lon, radius_km, limit) -> NearbyResponse:
        rows = self._within(lat, lon, radius_km)
        caps = self.capabilities()
        wells = [_well(r) for r in rows[:limit]]
        return NearbyResponse(
            location=Point(latitude=lat, longitude=lon), radius_km=radius_km, total_wells=len(rows),
            returned_wells=len(wells), limit=limit, truncated=len(rows) > len(wells),
            units=caps.units, capabilities=caps, wells=wells, data_source="demo",
        )

    def summary(self, lat, lon, radius_km) -> SummaryResponse:
        rows, caps, s = self._within(lat, lon, radius_km), self.capabilities(), self.s
        col = lambda k: [r[k] for r in rows if r[k] is not None]  # noqa: E731
        depth = [v for v in col("depth") if v > 0]
        yld = [v for v in col("well_yield") if v >= 0]
        swl = col("static_water_level")
        dates = col("drilling_date")
        qual_wells = [r["well_id"] for r in rows if demo_quality().get(r["well_id"])]
        thr = caps.low_yield_threshold
        agg = Aggregates(
            total_wells=len(rows),
            depth_n=len(depth), depth_median=st.median(depth),
            yield_n=len(yld), yield_median=st.median(yld),
            swl_n=len(swl), swl_median=st.median(swl),
            latest_record_date=max(dates) if dates else None,
            low_yield_n=sum(1 for v in yld if v < thr) if thr is not None else None,
            quality_wells=len(qual_wells),
            quality_obs=sum(1 for w in qual_wells for q in demo_quality()[w] if q["value_raw"] is not None),
            hist_counts={
                "depth": st.count_bins(depth, s.hist_depth_bin, s.hist_bins),
                "well_yield": st.count_bins(yld, s.hist_yield_bin, s.hist_bins),
            },
        )
        return build_summary(s, caps, lat, lon, radius_km, agg, "demo")

    def well_details(self, well_id: str) -> Optional[WellDetails]:
        w = next((x for x in demo_wells() if x["well_id"] == well_id), None)
        if not w:
            return None
        caps = self.capabilities()
        quality = [_measurement({**q, "well_id": well_id}, self.guidelines) for q in demo_quality().get(well_id, [])]
        return WellDetails(**{k: w[k] for k in ("well_id", "latitude", "longitude", "depth", "well_yield",
                                                 "static_water_level", "drilling_date", "status")},
                           units=caps.units, capabilities=caps, quality=quality,
                           source_dataset=caps.source_dataset, data_source="demo")

    def water_quality(self, lat, lon, radius_km) -> QualityResponse:
        rows = self._within(lat, lon, radius_km)
        meas: list[QualityMeasurement] = []
        for r in rows:
            for q in demo_quality().get(r["well_id"], []):
                meas.append(_measurement({**q, "well_id": r["well_id"], "distance_km": r["distance_km"]}, self.guidelines))
        meas.sort(key=lambda m: (m.sample_date or "", ), reverse=True)
        per: dict[str, dict] = {}
        for m in meas:
            p = per.setdefault(m.parameter, {"obs": 0, "wells": set(), "latest": None})
            p["obs"] += 1
            p["wells"].add(m.well_id)
            if m.sample_date and (p["latest"] is None or m.sample_date > p["latest"]):
                p["latest"] = m.sample_date
        shown = meas[:QUALITY_ROW_LIMIT]
        return QualityResponse(
            location=Point(latitude=lat, longitude=lon), radius_km=radius_km, available=True,
            total_records=len(meas), returned_records=len(shown),
            parameters=sorted(
                [QualityParameterSummary(parameter=k, observations=v["obs"], wells=len(v["wells"]),
                                         latest_sample_date=v["latest"]) for k, v in per.items()],
                key=lambda p: -p.observations),
            measurements=shown, guideline=self.guidelines.info(),
            explanation=None if meas else "No water-quality measurements are available for this selection.",
            data_source="demo",
        )

    def ping(self) -> dict:
        return {"reachable": True, "mapping_problems": []}


# ============================================================ Unconfigured
class UnconfiguredRepository:
    mode = "unconfigured"

    def __init__(self, settings: Settings):
        self.s = settings

    def missing(self) -> list[str]:
        out = []
        if not self.s.databricks_host:
            out.append("DATABRICKS_HOST")
        if not (self.s.warehouse_id or self.s.http_path):
            out.append("DATABRICKS_WAREHOUSE_ID")
        return out + self.s.missing_mapping()

    def capabilities(self) -> Capabilities:
        return Capabilities()

    def _fail(self, *_a, **_k):
        raise ServiceNotConfigured("Databricks is not configured", self.missing())

    nearby = summary = well_details = water_quality = _fail

    def ping(self) -> dict:
        return {"reachable": False, "mapping_problems": self.missing()}


def build_repository(settings: Settings) -> Repository:
    if settings.demo_mode:  # explicit opt-in always wins, so demos never touch a real workspace
        return DemoRepository(settings)
    if settings.databricks_configured:
        return DatabricksRepository(settings)
    return UnconfiguredRepository(settings)
