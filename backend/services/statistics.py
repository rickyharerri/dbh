"""Statistics + deterministic comparison text.

Definitions (shared by every endpoint so Property A and B always match):
  * median ignores missing values; missing is never treated as zero;
  * every figure is reported together with its sample size;
  * depth <= 0 is treated as missing; yield >= 0 is kept (0 = recorded no yield).
"""
from __future__ import annotations

import math
from typing import Iterable, Optional

from backend.models import (
    Capabilities,
    CompareRow,
    Histogram,
    HistogramBin,
    LIMITED_DATA_MESSAGE,
)


def median(values: Iterable[Optional[float]]) -> Optional[float]:
    xs = sorted(v for v in values if v is not None and not (isinstance(v, float) and math.isnan(v)))
    if not xs:
        return None
    mid = len(xs) // 2
    return float(xs[mid]) if len(xs) % 2 else (xs[mid - 1] + xs[mid]) / 2


def bin_index(value: float, width: float, n_bins: int) -> int:
    return min(int(math.floor(value / width)), n_bins - 1)


def count_bins(values: Iterable[Optional[float]], width: float, n_bins: int) -> dict[int, int]:
    counts: dict[int, int] = {}
    for v in values:
        if v is None or v < 0:
            continue
        i = bin_index(v, width, n_bins)
        counts[i] = counts.get(i, 0) + 1
    return counts


def build_histogram(counts: dict[int, int], width: float, n_bins: int, unit: Optional[str]) -> Histogram:
    total = sum(counts.values())
    if total == 0:
        return Histogram(unit=unit, sample_count=0, bins=[])
    bins: list[HistogramBin] = []
    for i in range(n_bins):
        start = i * width
        last = i == n_bins - 1
        end = None if last else (i + 1) * width
        label = f"{start:g}+" if last else f"{start:g}–{end:g}"
        bins.append(HistogramBin(label=label, start=start, end=end, count=int(counts.get(i, 0))))
    return Histogram(unit=unit, sample_count=total, bins=bins)


def assess_sufficiency(total: int, depth_n: int, yield_n: int, min_sample: int) -> tuple[bool, list[str]]:
    """Return (limited?, notes). Never a score — only an honest coverage statement."""
    notes: list[str] = []
    limited = total < min_sample or (depth_n < min_sample and yield_n < min_sample)
    if limited:
        notes.append(LIMITED_DATA_MESSAGE)
    return limited, notes


# ------------------------------------------------------------------ comparison
SIMILAR_TOLERANCE = 0.10  # medians within 10 % are described as "similar"


def _direction(a: float, b: float) -> str:
    if a == b:
        return "similar"
    base = max(abs(a), abs(b))
    if base == 0 or abs(a - b) / base <= SIMILAR_TOLERANCE:
        return "similar"
    return "higher" if a > b else "lower"


def _fmt(v: float, unit: Optional[str]) -> str:
    text = f"{v:,.1f}".rstrip("0").rstrip(".")
    return f"{text} {unit}" if unit else text


def build_rows(a, b, caps: Capabilities) -> list[CompareRow]:
    """Same metric definitions for both properties. `a` / `b` are SummaryResponse."""
    rows = [
        CompareRow(key="total_wells", label="Nearby wells", a=a.total_wells, b=b.total_wells),
        CompareRow(
            key="depth", label="Typical well depth (median)", a=a.depth.median, b=b.depth.median,
            unit=caps.units.depth, a_samples=a.depth.sample_count, b_samples=b.depth.sample_count,
            available=caps.depth,
        ),
        CompareRow(
            key="well_yield", label="Typical well yield (median)", a=a.well_yield.median,
            b=b.well_yield.median, unit=caps.units.well_yield, a_samples=a.well_yield.sample_count,
            b_samples=b.well_yield.sample_count, available=caps.well_yield,
        ),
        CompareRow(
            key="static_water_level", label="Typical recorded water level (median)",
            a=a.static_water_level.median, b=b.static_water_level.median,
            unit=caps.units.static_water_level, a_samples=a.static_water_level.sample_count,
            b_samples=b.static_water_level.sample_count, available=caps.static_water_level,
        ),
        CompareRow(
            key="quality", label="Wells with water-quality records",
            a=a.quality.wells_with_quality, b=b.quality.wells_with_quality, available=caps.quality,
        ),
    ]
    thr = caps.low_yield_threshold
    rows.append(
        CompareRow(
            key="low_yield",
            label=f"Low-yield records (below {thr:g} {caps.units.well_yield or ''})".strip()
            if thr is not None else "Low-yield records",
            a=a.low_yield.count if a.low_yield else None,
            b=b.low_yield.count if b.low_yield else None,
            a_samples=a.low_yield.sample_count if a.low_yield else None,
            b_samples=b.low_yield.sample_count if b.low_yield else None,
            available=caps.well_yield and thr is not None,
        )
    )
    rows.append(
        CompareRow(key="latest_record_date", label="Latest record date",
                   a=a.latest_record_date, b=b.latest_record_date, available=caps.drilling_date)
    )
    rows.append(
        CompareRow(
            key="coverage", label="Data coverage",
            a=f"depth {a.depth.sample_count} · yield {a.well_yield.sample_count} of {a.total_wells} wells",
            b=f"depth {b.depth.sample_count} · yield {b.well_yield.sample_count} of {b.total_wells} wells",
        )
    )
    return rows


def _metric_sentence(name: str, a_metric, b_metric, unit: Optional[str], min_sample: int) -> str:
    if a_metric.median is None or b_metric.median is None:
        return f"{name.capitalize()} cannot be compared because at least one property has no recorded values."
    if a_metric.sample_count < min_sample or b_metric.sample_count < min_sample:
        return (
            f"Too few {name} measurements to compare reliably "
            f"(Property A: {a_metric.sample_count}, Property B: {b_metric.sample_count})."
        )
    direction = _direction(a_metric.median, b_metric.median)
    figures = (
        f"{_fmt(a_metric.median, unit)} near Property A and {_fmt(b_metric.median, unit)} near Property B "
        f"(based on {a_metric.sample_count} and {b_metric.sample_count} wells)"
    )
    if direction == "similar":
        return f"Typical recorded {name} is similar: {figures}."
    word = "higher" if direction == "higher" else "lower"
    return f"Typical recorded {name} is {word} near Property A than near Property B: {figures}."


CAVEAT = (
    "These figures describe neighbouring historical wells. They do not show current conditions "
    "and do not guarantee the performance or safety of either property's water supply. "
    "Test your own water."
)


def build_comparison_text(a, b, caps: Capabilities, radius_km: float, min_sample: int) -> str:
    """Deterministic, template-based summary computed only from the returned numbers."""
    parts = [
        f"Within {radius_km:g} km, Property A has {a.total_wells} historical "
        f"well{'s' if a.total_wells != 1 else ''} on record and Property B has {b.total_wells}."
    ]
    if a.total_wells == 0 or b.total_wells == 0:
        parts.append("At least one location has no wells in the selected radius, so measurements cannot be compared.")
    else:
        if caps.depth:
            parts.append(_metric_sentence("well depth", a.depth, b.depth, caps.units.depth, min_sample))
        if caps.well_yield:
            parts.append(_metric_sentence("well yield", a.well_yield, b.well_yield, caps.units.well_yield, min_sample))
        if caps.quality:
            parts.append(
                f"Water-quality records exist for {a.quality.wells_with_quality} well(s) near Property A "
                f"and {b.quality.wells_with_quality} near Property B."
            )
    if a.limited_data or b.limited_data:
        parts.append(LIMITED_DATA_MESSAGE)
    parts.append(CAVEAT)
    return " ".join(parts)
