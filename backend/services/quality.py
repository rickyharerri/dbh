"""Water-quality guideline evaluation.

Guidelines are NEVER built in. They are evaluated only if a versioned reference
file is configured (QUALITY_GUIDELINES_FILE). Without one every measurement is
reported as "not_evaluated" (or "no_data" when there is no usable number).
"""
from __future__ import annotations

import json
import logging
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

from backend.models import GuidelineInfo, QualityMeasurement

log = logging.getLogger(__name__)


@dataclass(frozen=True)
class ParameterGuideline:
    limit: float
    unit: str
    comparison: str  # only "max" is supported: above the limit = above guideline


@dataclass(frozen=True)
class GuidelineSet:
    reference: Optional[str]
    version: Optional[str]
    parameters: dict[str, ParameterGuideline]

    @property
    def configured(self) -> bool:
        return bool(self.parameters)

    def info(self) -> GuidelineInfo:
        return GuidelineInfo(configured=self.configured, reference=self.reference, version=self.version)


EMPTY = GuidelineSet(reference=None, version=None, parameters={})


def _norm_name(name: str) -> str:
    return " ".join(name.lower().split())


def _norm_unit(unit: Optional[str]) -> Optional[str]:
    return unit.strip().lower().replace(" ", "") if unit else None


def load_guidelines(path: Optional[str]) -> GuidelineSet:
    if not path:
        return EMPTY
    try:
        raw = json.loads(Path(path).read_text(encoding="utf-8"))
        params: dict[str, ParameterGuideline] = {}
        for name, spec in raw.get("parameters", {}).items():
            params[_norm_name(name)] = ParameterGuideline(
                limit=float(spec["limit"]), unit=str(spec["unit"]), comparison=str(spec.get("comparison", "max"))
            )
        return GuidelineSet(raw.get("reference"), raw.get("version"), params)
    except Exception:  # a broken reference file must degrade to "not evaluated", never crash
        log.exception("Could not load quality guidelines from %s", path)
        return EMPTY


def evaluate(m: QualityMeasurement, guidelines: GuidelineSet) -> QualityMeasurement:
    """Return a copy of the measurement with guideline fields and a status."""
    if m.value is None:
        return m.model_copy(update={"status": "no_data"})
    g = guidelines.parameters.get(_norm_name(m.parameter))
    if g is None or g.comparison != "max" or _norm_unit(m.unit) != _norm_unit(g.unit):
        # unknown parameter, unsupported comparison, or units that don't match: do not guess
        return m.model_copy(update={"status": "not_evaluated"})
    status = "above_guideline" if m.value > g.limit else "within_guideline"
    return m.model_copy(
        update={
            "status": status,
            "guideline_value": g.limit,
            "guideline_unit": g.unit,
            "guideline_reference": " ".join(x for x in (guidelines.reference, guidelines.version) if x) or None,
        }
    )
