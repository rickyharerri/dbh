"""Builds API responses from raw aggregates.

Both the Databricks repository (SQL aggregates) and the demo repository (Python
aggregates over fixtures) produce the same `Aggregates`, so every metric is
defined exactly once.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Optional

from backend.config import Settings
from backend.models import (
    Capabilities,
    DataSource,
    LowYield,
    Metric,
    Point,
    QualityCoverage,
    SummaryResponse,
)
from backend.services import statistics as st


@dataclass
class Aggregates:
    total_wells: int = 0
    depth_n: int = 0
    depth_median: Optional[float] = None
    yield_n: int = 0
    yield_median: Optional[float] = None
    swl_n: int = 0
    swl_median: Optional[float] = None
    latest_record_date: Optional[str] = None
    low_yield_n: Optional[int] = None
    quality_wells: Optional[int] = None
    quality_obs: Optional[int] = None
    hist_counts: dict[str, dict[int, int]] = field(default_factory=dict)


def aggregates_from_rows(stats_row: dict[str, Any] | None, hist_rows: list[dict[str, Any]]) -> Aggregates:
    r = stats_row or {}

    def i(key: str) -> int:
        v = r.get(key)
        return int(v) if v is not None else 0

    def f(key: str) -> Optional[float]:
        v = r.get(key)
        return float(v) if v is not None else None

    low = r.get("low_yield_n")
    qw = r.get("quality_wells")
    qo = r.get("quality_obs")
    hist: dict[str, dict[int, int]] = {}
    for row in hist_rows:
        hist.setdefault(row["metric"], {})[int(row["bin"])] = int(row["n"])
    return Aggregates(
        total_wells=i("total_wells"),
        depth_n=i("depth_n"), depth_median=f("depth_median"),
        yield_n=i("yield_n"), yield_median=f("yield_median"),
        swl_n=i("swl_n"), swl_median=f("swl_median"),
        latest_record_date=str(r["latest_record_date"]) if r.get("latest_record_date") else None,
        low_yield_n=int(low) if low is not None else None,
        quality_wells=int(qw) if qw is not None else None,
        quality_obs=int(qo) if qo is not None else None,
        hist_counts=hist,
    )


def build_summary(
    s: Settings, caps: Capabilities, lat: float, lon: float, radius_km: float,
    agg: Aggregates, source: DataSource,
) -> SummaryResponse:
    u = caps.units
    limited, notes = st.assess_sufficiency(agg.total_wells, agg.depth_n, agg.yield_n, s.min_sample)
    low = None
    if caps.well_yield and caps.low_yield_threshold is not None and agg.low_yield_n is not None:
        low = LowYield(threshold=caps.low_yield_threshold, unit=u.well_yield,
                       count=agg.low_yield_n, sample_count=agg.yield_n)
    return SummaryResponse(
        location=Point(latitude=lat, longitude=lon),
        radius_km=radius_km,
        total_wells=agg.total_wells,
        depth=Metric(available=caps.depth, median=agg.depth_median, sample_count=agg.depth_n, unit=u.depth),
        well_yield=Metric(available=caps.well_yield, median=agg.yield_median, sample_count=agg.yield_n, unit=u.well_yield),
        static_water_level=Metric(available=caps.static_water_level, median=agg.swl_median,
                                  sample_count=agg.swl_n, unit=u.static_water_level),
        quality=QualityCoverage(available=caps.quality, wells_with_quality=agg.quality_wells or 0,
                                observation_count=agg.quality_obs or 0),
        low_yield=low,
        latest_record_date=agg.latest_record_date,
        histograms={
            "depth": st.build_histogram(agg.hist_counts.get("depth", {}), s.hist_depth_bin, s.hist_bins, u.depth),
            "well_yield": st.build_histogram(agg.hist_counts.get("well_yield", {}), s.hist_yield_bin, s.hist_bins, u.well_yield),
        },
        limited_data=limited,
        notes=notes,
        data_source=source,
    )
