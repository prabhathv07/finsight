import datetime as dt

import pytest
from fastapi.testclient import TestClient

from api.main import app, get_commentator, require_api_token
from core import db
from core.models import Base
from core.pipeline import run
from tests.conftest import FakeProvider

RUN_DATE = dt.date(2026, 1, 6)


class FakeCommentator:
    model = "fake-model"

    def __call__(self, summary_text):
        return "Futures firm, VIX easing."


@pytest.fixture
def client(tmp_path):
    url = f"sqlite:///{tmp_path/'api.db'}"
    engine = db.reset_engine_for_tests(url)
    Base.metadata.create_all(engine)

    # Seed one day of data so the analysis has something to summarize.
    session = db.get_session_factory()()
    run(session, run_date=RUN_DATE, provider=FakeProvider())
    session.commit()
    session.close()

    app.dependency_overrides[get_commentator] = lambda: FakeCommentator()
    app.dependency_overrides[require_api_token] = lambda: None
    yield TestClient(app)
    app.dependency_overrides.clear()


def test_health(client):
    resp = client.get("/health")
    assert resp.status_code == 200
    assert resp.json() == {"status": "ok"}


def test_run_then_read_latest(client):
    resp = client.post(f"/briefings/run?run_date={RUN_DATE.isoformat()}")
    assert resp.status_code == 200
    body = resp.json()
    assert body["status"] == "ok"
    assert body["model_name"] == "fake-model"
    assert "VIX" in body["commentary"]

    latest = client.get("/briefings/latest")
    assert latest.status_code == 200
    assert latest.json()["run_date"] == RUN_DATE.isoformat()


def test_get_specific_day(client):
    client.post(f"/briefings/run?run_date={RUN_DATE.isoformat()}")
    resp = client.get(f"/briefings/{RUN_DATE.isoformat()}")
    assert resp.status_code == 200
    assert resp.json()["run_date"] == RUN_DATE.isoformat()


def test_missing_day_is_404(client):
    resp = client.get("/briefings/2020-01-01")
    assert resp.status_code == 404


# ---- Auth on quota-spending endpoints -------------------------------------

@pytest.fixture
def auth_client(tmp_path, monkeypatch):
    """Client with the real token check active and a known token configured."""
    from core import config

    url = f"sqlite:///{tmp_path/'auth.db'}"
    engine = db.reset_engine_for_tests(url)
    Base.metadata.create_all(engine)

    monkeypatch.setenv("FINSIGHT_API_TOKEN", "test-token")
    config.get_settings.cache_clear()

    app.dependency_overrides[get_commentator] = lambda: FakeCommentator()
    yield TestClient(app)
    app.dependency_overrides.clear()
    config.get_settings.cache_clear()


def test_privileged_endpoints_require_token(auth_client):
    assert auth_client.post("/briefings/run").status_code == 401
    assert auth_client.post("/rag/reindex").status_code == 401
    assert auth_client.post("/ask", json={"question": "hi"}).status_code == 401


def test_wrong_token_rejected(auth_client):
    resp = auth_client.post("/briefings/run", headers={"X-API-Token": "nope"})
    assert resp.status_code == 401


def test_correct_token_accepted(auth_client):
    resp = auth_client.post(
        f"/briefings/run?run_date={RUN_DATE.isoformat()}",
        headers={"X-API-Token": "test-token"},
    )
    assert resp.status_code == 200


def test_unconfigured_token_disables_endpoints(tmp_path, monkeypatch):
    from core import config

    url = f"sqlite:///{tmp_path/'noauth.db'}"
    engine = db.reset_engine_for_tests(url)
    Base.metadata.create_all(engine)

    monkeypatch.delenv("FINSIGHT_API_TOKEN", raising=False)
    config.get_settings.cache_clear()
    try:
        client = TestClient(app)
        assert client.post("/briefings/run").status_code == 503
    finally:
        config.get_settings.cache_clear()
