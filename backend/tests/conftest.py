from __future__ import annotations

from types import SimpleNamespace

import pytest
from fastapi.testclient import TestClient

from backend.config import Settings
from backend.deps import get_genie, get_repository, get_settings
from backend.models import Capabilities, Units


def make_settings(**over) -> Settings:
    base = dict(
        databricks_host="https://example.cloud.databricks.com", warehouse_id="wh123", http_path=None,
        genie_space_id="space1", catalog="cat", schema="sch", demo_mode=False,
        wells_table="wells",
        well_columns={"id": "well_id_col", "latitude": "lat_col", "longitude": "lon_col",
                      "depth": "depth_col", "well_yield": "yield_col", "static_water_level": "swl_col",
                      "drilling_date": "date_col", "status": "status_col"},
        quality_table="quality",
        quality_columns={"well_id": "qw", "parameter": "qp", "value": "qv", "unit": "qu", "sample_date": "qd"},
        depth_unit="m", yield_unit="gpm", static_water_level_unit="m", low_yield_threshold=3.0,
        cache_ttl_s=60,
    )
    base.update(over)
    return Settings(**base)


@pytest.fixture
def settings() -> Settings:
    return make_settings()


class FakeDb:
    """Stands in for DatabricksClient; records statements and returns canned rows."""

    def __init__(self, rows_by_marker=None, columns=None):
        self.calls = []
        self.rows_by_marker = rows_by_marker or {}
        self.columns = columns

    def _rows(self, q):
        if "information_schema" in q.sql:
            cols = self.columns if self.columns is not None else [
                "well_id_col", "lat_col", "lon_col", "depth_col", "yield_col", "swl_col", "date_col",
                "status_col", "qw", "qp", "qv", "qu", "qd"]
            return [{"column_name": c} for c in cols]
        for marker, rows in self.rows_by_marker.items():
            if marker in q.sql:
                return rows
        return []

    def query(self, q):
        self.calls.append(q)
        return self._rows(q)

    def query_many(self, qs):
        return [self.query(q) if q is not None else [] for q in qs]

    def ping(self):
        return True


@pytest.fixture
def fake_db():
    return FakeDb()


class FakeRepo:
    mode = "live"

    def __init__(self, raises=None):
        self.raises = raises
        self.summary_calls = []

    def capabilities(self):
        return Capabilities(depth=True, well_yield=True, static_water_level=False, quality=True,
                            units=Units(depth="m", well_yield="gpm"), low_yield_threshold=3.0)

    def _maybe(self):
        if self.raises:
            raise self.raises

    def nearby(self, *a, **k):
        self._maybe()
        raise AssertionError("not used")

    def summary(self, lat, lon, r):
        self._maybe()
        from backend.services.repository import DemoRepository
        from backend.tests.conftest import make_settings
        self.summary_calls.append((lat, lon, r))
        return DemoRepository(make_settings()).summary(lat, lon, r)

    def well_details(self, well_id):
        self._maybe()
        return None

    def water_quality(self, *a):
        self._maybe()

    def ping(self):
        return {"reachable": True, "mapping_problems": []}


@pytest.fixture
def client_factory():
    from backend.main import app

    def make(repo=None, genie=None, settings=None):
        app.dependency_overrides.clear()
        if repo is not None:
            app.dependency_overrides[get_repository] = lambda: repo
        if genie is not None:
            app.dependency_overrides[get_genie] = lambda: genie
        if settings is not None:
            app.dependency_overrides[get_settings] = lambda: settings
        return TestClient(app, raise_server_exceptions=False)

    yield make
    app.dependency_overrides.clear()


class FakeWait:
    def __init__(self, conv, msg, message=None, exc=None):
        self.response = SimpleNamespace(conversation_id=conv, message_id=msg)
        self._message, self._exc = message, exc

    def result(self, timeout=None):
        self.timeout = timeout
        if self._exc:
            raise self._exc
        return self._message


class FakeGenieApi:
    def __init__(self, message=None, exc=None):
        self.message, self.exc, self.calls = message, exc, []

    def start_conversation(self, space_id, content):
        self.calls.append(("start", space_id, content))
        return FakeWait("conv-1", "msg-1", self.message, self.exc)

    def create_message(self, space_id, conversation_id, content):
        self.calls.append(("continue", space_id, conversation_id, content))
        return FakeWait(conversation_id, "msg-2", self.message, self.exc)

    def get_message(self, **k):
        return SimpleNamespace(status="FAILED")

    def get_message_attachment_query_result(self, **k):
        return SimpleNamespace(statement_response=SimpleNamespace(
            manifest=SimpleNamespace(schema=SimpleNamespace(columns=[SimpleNamespace(name="wells")]), total_row_count=1),
            result=SimpleNamespace(data_array=[["42"]])))


def genie_message(text="There are 42 wells.", with_query=True):
    atts = [SimpleNamespace(text=SimpleNamespace(content=text), query=None, attachment_id="t1")]
    if with_query:
        atts.append(SimpleNamespace(text=None, attachment_id="q1",
                                    query=SimpleNamespace(description="Count wells", query="SELECT COUNT(*) FROM wells")))
    return SimpleNamespace(conversation_id="conv-1", message_id="msg-1", error=None, attachments=atts)
