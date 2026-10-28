import pytest
import sqlglot

from backend.config import quote_ident
from backend.services import queries as Q
from backend.tests.conftest import make_settings

LAT, LON, R = 51.19, -114.47, 5.0
EVIL = "x'; DROP TABLE wells; --"


def all_queries(s):
    out = {
        "nearby": Q.nearby_wells(s, LAT, LON, R, 500),
        "summary": Q.summary_stats(s, LAT, LON, R),
        "hist": Q.histograms(s, LAT, LON, R),
        "well": Q.well_by_id(s, EVIL),
        "quality": Q.quality_measurements(s, LAT, LON, R, 300),
        "quality_params": Q.quality_parameters(s, LAT, LON, R),
        "quality_well": Q.quality_for_well(s, EVIL),
        "columns": Q.mapped_columns_check(s, "wells"),
    }
    return {k: v for k, v in out.items() if v is not None}


def test_every_statement_parses_as_databricks_sql(settings):
    for name, q in all_queries(settings).items():
        sqlglot.parse_one(q.sql, read="databricks")  # raises on syntax errors


def test_user_values_are_bound_never_interpolated(settings):
    for name, q in all_queries(settings).items():
        assert EVIL not in q.sql, name
        assert "DROP TABLE" not in q.sql, name
        assert "51.19" not in q.sql and "-114.47" not in q.sql, name
    assert Q.well_by_id(settings, EVIL).params == {"well_id": EVIL}
    p = Q.nearby_wells(settings, LAT, LON, R, 500).params
    assert p["lat"] == LAT and p["lon"] == LON and p["radius_km"] == R
    assert p["min_lat"] < LAT < p["max_lat"]


def test_unsafe_identifiers_are_rejected():
    for bad in ("a b", "x`; DROP", "1abc", "a-b", "", "a.b"):
        with pytest.raises(ValueError):
            quote_ident(bad)
    s = make_settings(well_columns={"id": "ok", "latitude": "bad name", "longitude": "lon"})
    assert any("not a plain identifier" in e for e in s.mapping_errors())


def test_wells_are_deduplicated_and_coordinates_validated(settings):
    sql = Q.nearby_wells(settings, LAT, LON, R, 10).sql
    assert "QUALIFY ROW_NUMBER() OVER (PARTITION BY well_id" in sql
    assert "BETWEEN -90 AND 90" in sql and "BETWEEN -180 AND 180" in sql
    assert "COUNT(*) OVER () AS total_wells" in sql  # total before LIMIT
    assert "LIMIT 10" in sql


def test_summary_counts_distinct_wells_for_quality_join(settings):
    sql = Q.summary_stats(settings, LAT, LON, R).sql
    assert "COUNT(DISTINCT n.well_id)" in sql
    assert "percentile(depth, 0.5)" in sql  # percentile ignores NULLs
    assert "COUNT(depth)" in sql  # sample size counts non-null only


def test_missing_optional_columns_become_typed_nulls_not_zeros():
    s = make_settings(well_columns={"id": "i", "latitude": "la", "longitude": "lo"}, quality_table=None, quality_columns={})
    q = Q.nearby_wells(s, LAT, LON, R, 5)
    assert "CAST(NULL AS DOUBLE) AS depth" in q.sql
    assert "CAST(NULL AS DOUBLE) AS well_yield" in q.sql
    assert Q.histograms(s, LAT, LON, R) is None
    assert "quality_wells" in Q.summary_stats(s, LAT, LON, R).sql  # still well-formed
    sqlglot.parse_one(q.sql, read="databricks")


def test_low_yield_threshold_is_a_bound_parameter(settings):
    q = Q.summary_stats(settings, LAT, LON, R)
    assert q.params["low_yield"] == 3.0 and ":low_yield" in q.sql


def test_depth_nonpositive_is_missing_but_zero_yield_is_kept(settings):
    sql = Q.nearby_wells(settings, LAT, LON, R, 5).sql
    assert "> 0 THEN" in sql and ">= 0 THEN" in sql
