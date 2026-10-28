import json

from backend.models import QualityMeasurement
from backend.services.quality import EMPTY, evaluate, load_guidelines


def m(**kw):
    base = dict(well_id="W1", parameter="Nitrate", value=5.0, value_raw="5", unit="mg/L")
    base.update(kw)
    return QualityMeasurement(**base)


def gl(tmp_path):
    p = tmp_path / "g.json"
    p.write_text(json.dumps({"reference": "Test ref", "version": "v1",
                             "parameters": {"Nitrate": {"limit": 10, "unit": "mg/L", "comparison": "max"}}}))
    return load_guidelines(str(p))


def test_four_statuses(tmp_path):
    g = gl(tmp_path)
    assert evaluate(m(value=5), g).status == "within_guideline"
    assert evaluate(m(value=12), g).status == "above_guideline"
    assert evaluate(m(value=None, value_raw="<0.5"), g).status == "no_data"
    assert evaluate(m(parameter="Unknown"), g).status == "not_evaluated"


def test_unit_mismatch_is_not_evaluated(tmp_path):
    assert evaluate(m(unit="ug/L"), gl(tmp_path)).status == "not_evaluated"
    assert evaluate(m(unit=None), gl(tmp_path)).status == "not_evaluated"


def test_guideline_reference_is_attached(tmp_path):
    out = evaluate(m(value=12), gl(tmp_path))
    assert out.guideline_value == 10 and out.guideline_reference == "Test ref v1"


def test_no_guideline_file_means_not_evaluated():
    assert evaluate(m(), EMPTY).status == "not_evaluated"


def test_broken_guideline_file_degrades_safely(tmp_path):
    p = tmp_path / "bad.json"
    p.write_text("{not json")
    assert not load_guidelines(str(p)).configured
    assert not load_guidelines("/nonexistent.json").configured


# ---------------------------------------------------------------- schema discovery helper
def test_schema_inventory_renderer_suggests_but_does_not_assume():
    import importlib.util
    from pathlib import Path

    spec = importlib.util.spec_from_file_location("discover", Path(__file__).resolve().parents[2] / "scripts" / "discover_schema.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    cols = [
        {"table_name": "wells", "column_name": "GIC_Well_ID", "data_type": "string", "ordinal_position": 1},
        {"table_name": "wells", "column_name": "Latitude", "data_type": "double", "ordinal_position": 2},
        {"table_name": "wells", "column_name": "Total_Depth", "data_type": "double", "ordinal_position": 3},
        {"table_name": "water_chemistry", "column_name": "Result_Value", "data_type": "double", "ordinal_position": 1},
    ]
    md = mod.render_inventory("c", "s", cols, generated="test")
    assert "`wells.GIC_Well_ID`" in md and "`wells.Latitude`" in md
    assert "possible water-quality table" in md          # water_chemistry flagged
    assert "`water_chemistry.Result_Value`" in md        # quality value candidate
    assert "none found" in md                             # e.g. yield: nothing guessed
    assert "confirm" in md.lower()
