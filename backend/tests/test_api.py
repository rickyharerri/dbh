import pytest

from backend.errors import DatabricksUnavailable, ServiceNotConfigured
from backend.services.genie import GenieService
from backend.services.repository import DemoRepository, UnconfiguredRepository
from backend.tests.conftest import FakeGenieApi, FakeRepo, genie_message, make_settings

Q = dict(latitude=51.19, longitude=-114.47, radius_km=5)


@pytest.fixture
def demo_client(client_factory):
    return client_factory(repo=DemoRepository(make_settings(demo_mode=True)))


# ---------------------------------------------------------------- validation
@pytest.mark.parametrize("params", [
    dict(latitude=91, longitude=0), dict(latitude=-91, longitude=0),
    dict(latitude=51, longitude=181), dict(latitude=51, longitude=-181),
    dict(latitude="abc", longitude=0), dict(latitude="nan", longitude=0), dict(latitude=51),
])
def test_invalid_coordinates_rejected(demo_client, params):
    for path in ("/api/wells/nearby", "/api/groundwater/summary", "/api/water-quality"):
        r = demo_client.get(path, params=params)
        assert r.status_code == 422, (path, params)
        assert r.json()["error"]["code"] == "invalid_request"


@pytest.mark.parametrize("radius", [0, 3, 7, 21, -5, "x"])
def test_invalid_radius_rejected(demo_client, radius):
    r = demo_client.get("/api/groundwater/summary", params={**Q, "radius_km": radius})
    assert r.status_code == 422


@pytest.mark.parametrize("radius", [1, 2, 5, 10, 20])
def test_allowed_radii_accepted(demo_client, radius):
    assert demo_client.get("/api/groundwater/summary", params={**Q, "radius_km": radius}).status_code == 200


def test_limit_bounds(demo_client):
    assert demo_client.get("/api/wells/nearby", params={**Q, "limit": 0}).status_code == 422
    assert demo_client.get("/api/wells/nearby", params={**Q, "limit": 5000}).status_code == 422
    assert demo_client.get("/api/wells/nearby", params={**Q, "limit": 7}).json()["returned_wells"] == 7


def test_default_radius_is_5km(demo_client):
    r = demo_client.get("/api/groundwater/summary", params=dict(latitude=51.19, longitude=-114.47))
    assert r.json()["radius_km"] == 5


# ---------------------------------------------------------------- endpoints
def test_nearby_contract(demo_client):
    body = demo_client.get("/api/wells/nearby", params={**Q, "limit": 3}).json()
    assert {"location", "radius_km", "total_wells", "returned_wells", "limit", "truncated", "wells", "units", "data_source"} <= body.keys()
    assert body["data_source"] == "demo" and body["returned_wells"] == 3 <= body["total_wells"]


def test_well_details_and_404(demo_client):
    first = demo_client.get("/api/wells/nearby", params={**Q, "limit": 1}).json()["wells"][0]["well_id"]
    ok = demo_client.get(f"/api/wells/{first}")
    assert ok.status_code == 200 and ok.json()["well_id"] == first and "SYNTHETIC" in ok.json()["source_dataset"]
    assert demo_client.get("/api/wells/does-not-exist").status_code == 404


def test_water_quality_returns_observed_rows_only(demo_client):
    body = demo_client.get("/api/water-quality", params={**Q, "radius_km": 20}).json()
    assert body["total_records"] >= body["returned_records"] > 0
    assert "Test your own water" in body["disclaimer"]
    assert {m["status"] for m in body["measurements"]} <= {"no_data", "not_evaluated", "within_guideline", "above_guideline"}


def test_compare_uses_identical_definitions_for_both(demo_client):
    body = demo_client.post("/api/properties/compare", json={
        "property_a": {"latitude": 51.19, "longitude": -114.47},
        "property_b": {"latitude": 50.73, "longitude": -113.98}, "radius_km": 5}).json()
    a, b = body["property_a"], body["property_b"]
    assert a["radius_km"] == b["radius_km"] == 5
    for key in ("depth", "well_yield"):
        assert a[key]["unit"] == b[key]["unit"]
    assert {r["key"] for r in body["rows"]} >= {"total_wells", "depth", "well_yield", "quality", "low_yield"}
    text = body["summary_text"].lower()
    assert "do not guarantee" in text and "test your own water" in text
    assert "safe water" not in text and "unsafe" not in text


def test_compare_validates_input(demo_client):
    bad = demo_client.post("/api/properties/compare", json={
        "property_a": {"latitude": 99, "longitude": -114}, "property_b": {"latitude": 50, "longitude": -114}})
    assert bad.status_code == 422
    bad = demo_client.post("/api/properties/compare", json={
        "property_a": {"latitude": 51, "longitude": -114}, "property_b": {"latitude": 50, "longitude": -114}, "radius_km": 3})
    assert bad.status_code == 422


def test_compare_with_empty_area_degrades_gracefully(demo_client):
    body = demo_client.post("/api/properties/compare", json={
        "property_a": {"latitude": 51.19, "longitude": -114.47},
        "property_b": {"latitude": 59.9, "longitude": -110.5}, "radius_km": 1}).json()
    assert "cannot be compared" in body["summary_text"]


# ---------------------------------------------------------------- error handling
def test_databricks_failure_is_friendly_and_hides_details(client_factory):
    c = client_factory(repo=FakeRepo(raises=DatabricksUnavailable("secret internal detail")))
    r = c.get("/api/groundwater/summary", params=Q)
    assert r.status_code == 502
    assert "couldn't retrieve groundwater information" in r.json()["error"]["message"]
    assert "secret" not in r.text


def test_unconfigured_lists_missing_env_vars_only(client_factory):
    repo = UnconfiguredRepository(make_settings(databricks_host=None, warehouse_id=None, wells_table=None, well_columns={}))
    r = client_factory(repo=repo).get("/api/groundwater/summary", params=Q)
    assert r.status_code == 503
    assert "DATABRICKS_HOST" in r.json()["error"]["missing"] and "WELLS_TABLE" in r.json()["error"]["missing"]


def test_unexpected_error_does_not_leak(client_factory):
    r = client_factory(repo=FakeRepo(raises=RuntimeError("token=abc123"))).get("/api/groundwater/summary", params=Q)
    assert r.status_code == 500 and "abc123" not in r.text


def test_health_is_fast_and_non_secret(client_factory):
    s = make_settings()
    body = client_factory(repo=FakeRepo(), settings=s).get("/api/health").json()
    assert body["status"] == "healthy" and body["mode"] == "live"
    flat = str(body)
    assert "example.cloud.databricks.com" not in flat and "wh123" not in flat and "space1" not in flat


def test_unknown_api_route_is_json_404(demo_client):
    r = demo_client.get("/api/nothing")
    assert r.status_code == 404 and r.json()["error"]["code"] == "not_found"


# ---------------------------------------------------------------- Genie
def genie_client(client_factory, api, settings=None):
    s = settings or make_settings()
    return client_factory(genie=GenieService(s, client=type("W", (), {"genie": api})()))


def test_genie_new_conversation_with_answer_and_table(client_factory):
    api = FakeGenieApi(message=genie_message())
    r = genie_client(client_factory, api).post("/api/genie/chat", json={"message": "How many wells?"})
    body = r.json()
    assert r.status_code == 200 and body["status"] == "completed"
    assert body["conversation_id"] == "conv-1" and body["message_id"] == "msg-1"
    assert "42 wells" in body["answer"]
    assert body["data"] == {"columns": ["wells"], "rows": [["42"]], "row_count": 1, "truncated": False}
    assert body["query"]["sql"] == "SELECT COUNT(*) FROM wells"
    assert api.calls[0][:2] == ("start", "space1")


def test_genie_follow_up_continues_conversation(client_factory):
    api = FakeGenieApi(message=genie_message(with_query=False))
    r = genie_client(client_factory, api).post("/api/genie/chat", json={"message": "And deeper?", "conversation_id": "conv-1"})
    assert r.json()["conversation_id"] == "conv-1"
    assert api.calls[0][0] == "continue" and api.calls[0][2] == "conv-1"


def test_genie_location_is_only_sent_when_explicit(client_factory):
    api = FakeGenieApi(message=genie_message())
    c = genie_client(client_factory, api)
    c.post("/api/genie/chat", json={"message": "Typical depth?"})
    assert "latitude" not in api.calls[-1][-1]
    c.post("/api/genie/chat", json={"message": "Typical depth?", "context": {"latitude": 51.19, "longitude": -114.47, "radius_km": 5}})
    sent = api.calls[-1][-1]
    assert "latitude 51.19000" in sent and "longitude -114.47000" in sent and "5 km" in sent


def test_genie_timeout_is_reported(client_factory):
    api = FakeGenieApi(exc=TimeoutError())
    body = genie_client(client_factory, api).post("/api/genie/chat", json={"message": "hi"}).json()
    assert body["status"] == "timeout" and body["conversation_id"] == "conv-1"


def test_genie_failure_is_friendly(client_factory):
    api = FakeGenieApi(exc=RuntimeError("boom: token xyz"))
    r = genie_client(client_factory, api).post("/api/genie/chat", json={"message": "hi"})
    assert r.json()["status"] == "failed" and "xyz" not in r.text
    assert "rephrasing" in r.json()["error"]


def test_genie_not_configured(client_factory):
    s = make_settings(genie_space_id=None)
    r = genie_client(client_factory, FakeGenieApi(), s).post("/api/genie/chat", json={"message": "hi"})
    assert r.status_code == 503 and "GENIE_SPACE_ID" in r.json()["error"]["missing"]
    assert "AI assistant" in r.json()["error"]["message"]


@pytest.mark.parametrize("payload", [
    {"message": ""}, {"message": "   "}, {"message": "x" * 1001},
    {"message": "ok", "conversation_id": "../etc/passwd"},
    {"message": "ok", "context": {"latitude": 200, "longitude": 0, "radius_km": 5}},
    {"message": "ok", "context": {"latitude": 50, "longitude": 0, "radius_km": 4}},
])
def test_genie_input_validation(client_factory, payload):
    api = FakeGenieApi(message=genie_message())
    assert genie_client(client_factory, api).post("/api/genie/chat", json=payload).status_code == 422
    assert api.calls == []
