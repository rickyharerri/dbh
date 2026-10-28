import pytest

from backend.errors import ServiceNotConfigured
from backend.services import statistics as st
from backend.services.demo_data import demo_wells
from backend.services.repository import DatabricksRepository, DemoRepository, UnconfiguredRepository, build_repository
from backend.services.spatial import haversine_km
from backend.tests.conftest import FakeDb, make_settings

LAT, LON = 51.19, -114.47


# ---------------------------------------------------------------- demo repository (brute-force checks)
@pytest.mark.parametrize("radius", [1, 2, 5, 10, 20])
def test_distance_filtering_matches_brute_force(radius):
    repo = DemoRepository(make_settings())
    res = repo.nearby(LAT, LON, radius, 1000)
    expected = {w["well_id"] for w in demo_wells() if haversine_km(LAT, LON, w["latitude"], w["longitude"]) <= radius}
    got = {w.well_id for w in res.wells}
    assert res.total_wells == len(expected)
    if not res.truncated:
        assert got == expected
    assert all(w.distance_km <= radius + 1e-6 for w in res.wells)
    assert [w.distance_km for w in res.wells] == sorted(w.distance_km for w in res.wells)


def test_total_vs_returned_when_limited():
    res = DemoRepository(make_settings()).nearby(LAT, LON, 20, 10)
    assert res.returned_wells == 10 and res.total_wells > 10 and res.truncated


def test_well_ids_are_distinct():
    ids = [w["well_id"] for w in demo_wells()]
    assert len(ids) == len(set(ids))


def test_summary_matches_independent_calculation():
    s = make_settings()
    repo = DemoRepository(s)
    res = repo.summary(LAT, LON, 5)
    rows = [w for w in demo_wells() if haversine_km(LAT, LON, w["latitude"], w["longitude"]) <= 5]
    depths = [w["depth"] for w in rows if w["depth"] is not None]
    assert res.total_wells == len(rows)
    assert res.depth.sample_count == len(depths)
    assert res.depth.median == st.median(depths)
    assert res.depth.sample_count < res.total_wells  # missing depths are excluded, not zero
    assert res.histograms["depth"].sample_count == len(depths)
    assert res.data_source == "demo"


def test_summary_with_no_wells_is_safe():
    res = DemoRepository(make_settings()).summary(60.0, -110.0, 1)
    assert res.total_wells == 0 and res.depth.median is None and res.limited_data
    assert res.histograms["depth"].bins == []


# ---------------------------------------------------------------- Databricks repository with a mocked client
def stats_row(**over):
    row = dict(total_wells=42, depth_n=38, depth_median=82.0, yield_n=35, yield_median=12.0, swl_n=20,
               swl_median=24.6, date_n=40, latest_record_date="2021-05-04", low_yield_n=7,
               quality_wells=14, quality_obs=30)
    row.update(over)
    return row


def test_databricks_summary_from_mocked_rows(settings):
    db = FakeDb({"stats AS": [stats_row()], "UNION ALL": [
        {"metric": "depth", "bin": 2, "n": 30}, {"metric": "depth", "bin": 9, "n": 8},
        {"metric": "well_yield", "bin": 1, "n": 35}]})
    repo = DatabricksRepository(settings, client=db)
    res = repo.summary(LAT, LON, 5)
    assert res.total_wells == 42 and res.depth.median == 82.0 and res.depth.sample_count == 38
    assert res.depth.unit == "m" and res.well_yield.unit == "gpm"
    assert res.quality.wells_with_quality == 14
    assert res.low_yield.count == 7 and res.low_yield.sample_count == 35
    assert res.histograms["depth"].bins[2].count == 30 and res.histograms["depth"].bins[-1].count == 8
    assert res.data_source == "databricks"


def test_null_medians_stay_null(settings):
    db = FakeDb({"stats AS": [stats_row(depth_median=None, depth_n=0, yield_median=None, yield_n=0, low_yield_n=0)]})
    res = DatabricksRepository(settings, client=db).summary(LAT, LON, 5)
    assert res.depth.median is None and res.depth.sample_count == 0
    assert res.well_yield.median is None


def test_nearby_reads_total_from_window_column(settings):
    rows = [dict(well_id="W1", latitude=51.2, longitude=-114.4, distance_km=0.31234, depth=82, well_yield=None,
                 static_water_level=None, drilling_date="2020-01-02", status=None, total_wells=42)]
    repo = DatabricksRepository(settings, client=FakeDb({"FROM nearby": rows}))
    res = repo.nearby(LAT, LON, 5, 1)
    assert res.total_wells == 42 and res.returned_wells == 1 and res.truncated
    assert res.wells[0].well_yield is None  # null stays null
    assert res.wells[0].distance_km == 0.312


def test_results_are_cached(settings):
    db = FakeDb({"stats AS": [stats_row()]})
    repo = DatabricksRepository(settings, client=db)
    repo.summary(LAT, LON, 5)
    n = len(db.calls)
    repo.summary(LAT, LON, 5)
    assert len(db.calls) == n  # second call served from cache, no warehouse round-trip


def test_mapping_is_verified_against_real_columns():
    s = make_settings()
    repo = DatabricksRepository(s, client=FakeDb(columns=["well_id_col", "lat_col"]))  # others missing
    with pytest.raises(ServiceNotConfigured) as exc:
        repo.summary(LAT, LON, 5)
    assert any("lon_col" in m for m in exc.value.missing)


def test_incomplete_mapping_lists_missing_env_vars():
    s = make_settings(wells_table=None, well_columns={})
    with pytest.raises(ServiceNotConfigured) as exc:
        DatabricksRepository(s, client=FakeDb()).summary(LAT, LON, 5)
    assert "WELLS_TABLE" in exc.value.missing and "WELLS_COL_LATITUDE" in exc.value.missing


def test_quality_without_table_is_explained_not_faked():
    s = make_settings(quality_table=None, quality_columns={})
    res = DatabricksRepository(s, client=FakeDb()).water_quality(LAT, LON, 5)
    assert not res.available and res.measurements == [] and "QUALITY_TABLE" in res.explanation


def test_quality_statuses_without_guidelines(settings):
    rows = [dict(well_id="W1", distance_km=1.0, parameter="Nitrate", value=3.2, value_raw="3.2", unit="mg/L",
                 sample_date="2019-06-15", total_records=1)]
    res = DatabricksRepository(settings, client=FakeDb({"total_records": rows})).water_quality(LAT, LON, 5)
    assert res.measurements[0].status == "not_evaluated"  # no guideline configured -> never "within"
    assert not res.guideline.configured


def test_build_repository_selection():
    assert isinstance(build_repository(make_settings(demo_mode=True)), DemoRepository)
    assert isinstance(build_repository(make_settings(databricks_host=None, warehouse_id=None)), UnconfiguredRepository)
    assert isinstance(build_repository(make_settings()), DatabricksRepository)
