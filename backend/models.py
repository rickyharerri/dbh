"""Pydantic request/response models — the API contract."""
from __future__ import annotations

import math
import re
from typing import Literal, Optional, Union

from pydantic import BaseModel, Field, field_validator

from backend.config import ALLOWED_RADII_KM

DataSource = Literal["databricks", "demo"]
QualityStatus = Literal["no_data", "not_evaluated", "within_guideline", "above_guideline"]

DISCLAIMER_HISTORICAL = "Historical records — not a water safety certification."
DISCLAIMER_QUALITY = (
    "Historical nearby records do not establish whether water at this property is safe to drink. "
    "Test your own water."
)
LIMITED_DATA_MESSAGE = (
    "Limited historical information is available for this location. "
    "Results may not represent current groundwater conditions."
)


def validate_radius(value: float) -> float:
    if not math.isfinite(value) or float(value) not in {float(r) for r in ALLOWED_RADII_KM}:
        allowed = ", ".join(f"{r:g}" for r in ALLOWED_RADII_KM)
        raise ValueError(f"radius_km must be one of: {allowed}")
    return float(value)


class Point(BaseModel):
    latitude: float = Field(ge=-90, le=90, allow_inf_nan=False)
    longitude: float = Field(ge=-180, le=180, allow_inf_nan=False)


class Units(BaseModel):
    depth: Optional[str] = None
    well_yield: Optional[str] = None
    static_water_level: Optional[str] = None


class Capabilities(BaseModel):
    """What the connected data source can actually provide."""

    depth: bool = False
    well_yield: bool = False
    static_water_level: bool = False
    drilling_date: bool = False
    status: bool = False
    quality: bool = False
    units: Units = Units()
    low_yield_threshold: Optional[float] = None
    source_dataset: Optional[str] = None


# ------------------------------------------------------------------ wells
class Well(BaseModel):
    well_id: str
    latitude: float
    longitude: float
    distance_km: float
    depth: Optional[float] = None
    well_yield: Optional[float] = None
    static_water_level: Optional[float] = None
    drilling_date: Optional[str] = None
    status: Optional[str] = None


class NearbyResponse(BaseModel):
    location: Point
    radius_km: float
    total_wells: int
    returned_wells: int
    limit: int
    truncated: bool
    units: Units
    capabilities: Capabilities
    wells: list[Well]
    data_source: DataSource
    disclaimer: str = DISCLAIMER_HISTORICAL


class QualityMeasurement(BaseModel):
    well_id: str
    distance_km: Optional[float] = None
    parameter: str
    value: Optional[float] = None
    value_raw: Optional[str] = None
    unit: Optional[str] = None
    sample_date: Optional[str] = None
    guideline_value: Optional[float] = None
    guideline_unit: Optional[str] = None
    guideline_reference: Optional[str] = None
    status: QualityStatus = "not_evaluated"


class WellDetails(BaseModel):
    well_id: str
    latitude: float
    longitude: float
    depth: Optional[float] = None
    well_yield: Optional[float] = None
    static_water_level: Optional[float] = None
    drilling_date: Optional[str] = None
    status: Optional[str] = None
    units: Units
    capabilities: Capabilities
    quality: list[QualityMeasurement] = []
    source_dataset: Optional[str] = None
    data_source: DataSource
    disclaimer: str = DISCLAIMER_HISTORICAL


# ------------------------------------------------------------------ summary
class Metric(BaseModel):
    available: bool
    median: Optional[float] = None
    sample_count: int = 0
    unit: Optional[str] = None


class HistogramBin(BaseModel):
    label: str
    start: float
    end: Optional[float] = None  # None = open-ended last bin
    count: int


class Histogram(BaseModel):
    unit: Optional[str] = None
    sample_count: int = 0
    bins: list[HistogramBin] = []


class QualityCoverage(BaseModel):
    available: bool
    wells_with_quality: int = 0
    observation_count: int = 0


class LowYield(BaseModel):
    threshold: float
    unit: Optional[str] = None
    count: int
    sample_count: int


class SummaryResponse(BaseModel):
    location: Point
    radius_km: float
    total_wells: int
    depth: Metric
    well_yield: Metric
    static_water_level: Metric
    quality: QualityCoverage
    low_yield: Optional[LowYield] = None
    latest_record_date: Optional[str] = None
    histograms: dict[str, Histogram]
    limited_data: bool
    notes: list[str]
    data_source: DataSource
    disclaimer: str = DISCLAIMER_HISTORICAL


# ------------------------------------------------------------------ water quality
class QualityParameterSummary(BaseModel):
    parameter: str
    observations: int
    wells: int
    latest_sample_date: Optional[str] = None


class GuidelineInfo(BaseModel):
    configured: bool
    reference: Optional[str] = None
    version: Optional[str] = None


class QualityResponse(BaseModel):
    location: Point
    radius_km: float
    available: bool
    total_records: int
    returned_records: int
    parameters: list[QualityParameterSummary]
    measurements: list[QualityMeasurement]
    guideline: GuidelineInfo
    explanation: Optional[str] = None
    data_source: DataSource
    disclaimer: str = DISCLAIMER_QUALITY


# ------------------------------------------------------------------ compare
class CompareRequest(BaseModel):
    property_a: Point
    property_b: Point
    radius_km: float = 5

    @field_validator("radius_km")
    @classmethod
    def _radius(cls, v: float) -> float:
        return validate_radius(v)


class CompareRow(BaseModel):
    key: str
    label: str
    a: Union[float, int, str, None] = None
    b: Union[float, int, str, None] = None
    unit: Optional[str] = None
    a_samples: Optional[int] = None
    b_samples: Optional[int] = None
    available: bool = True


class CompareResponse(BaseModel):
    radius_km: float
    property_a: SummaryResponse
    property_b: SummaryResponse
    rows: list[CompareRow]
    summary_text: str
    data_source: DataSource
    disclaimer: str = DISCLAIMER_HISTORICAL


# ------------------------------------------------------------------ genie
class GenieContext(BaseModel):
    latitude: float = Field(ge=-90, le=90, allow_inf_nan=False)
    longitude: float = Field(ge=-180, le=180, allow_inf_nan=False)
    radius_km: float = 5

    @field_validator("radius_km")
    @classmethod
    def _radius(cls, v: float) -> float:
        return validate_radius(v)


_ID = re.compile(r"^[A-Za-z0-9_-]{1,128}$")
MAX_QUESTION_CHARS = 1000


class GenieChatRequest(BaseModel):
    message: str = Field(min_length=1, max_length=MAX_QUESTION_CHARS)
    conversation_id: Optional[str] = None
    context: Optional[GenieContext] = None

    @field_validator("message")
    @classmethod
    def _strip(cls, v: str) -> str:
        v = v.strip()
        if not v:
            raise ValueError("message must not be empty")
        return v

    @field_validator("conversation_id")
    @classmethod
    def _conv(cls, v: Optional[str]) -> Optional[str]:
        if v is not None and not _ID.match(v):
            raise ValueError("conversation_id is not valid")
        return v


class GenieTable(BaseModel):
    columns: list[str]
    rows: list[list[Optional[str]]]
    row_count: int
    truncated: bool = False


class GenieQuery(BaseModel):
    description: Optional[str] = None
    sql: Optional[str] = None


GenieStatus = Literal["completed", "failed", "timeout", "cancelled"]


class GenieChatResponse(BaseModel):
    conversation_id: Optional[str] = None
    message_id: Optional[str] = None
    status: GenieStatus
    answer: Optional[str] = None
    query: Optional[GenieQuery] = None
    data: Optional[GenieTable] = None
    error: Optional[str] = None
