import app as app_module
import pytest


TEST_SECRET = "test-secret"


@pytest.fixture()
def client(monkeypatch):
    monkeypatch.setattr(app_module, "API_SECRET", TEST_SECRET)
    app_module.app.config.update(TESTING=True)
    with app_module.app.test_client() as test_client:
        yield test_client


def auth_headers():
    return {"X-API-Secret": TEST_SECRET}


def test_health_ok(client):
    res = client.get("/health")
    assert res.status_code == 200
    payload = res.get_json()
    assert payload["status"] == "ok"
    assert payload["service"] == "all_fetching"


def test_sources_requires_auth(client):
    unauthorized = client.get("/sources")
    assert unauthorized.status_code == 401

    authorized = client.get("/sources", headers=auth_headers())
    assert authorized.status_code == 200
    payload = authorized.get_json()
    assert "available_sources" in payload


def test_webhook_single_requires_auth(client):
    res = client.post("/webhook/single", json={"isin": "INE002A01018"})
    assert res.status_code == 401


def test_webhook_single_success(client, monkeypatch):
    fake_result = {"isin": "INE002A01018", "company": "Reliance", "total_fields_updated": 3, "sources": {}}
    monkeypatch.setattr(app_module, "run_single_stock", lambda isin, sources=None: fake_result)

    res = client.post(
        "/webhook/single",
        json={"isin": "INE002A01018"},
        headers=auth_headers(),
    )
    assert res.status_code == 200
    payload = res.get_json()
    assert payload["status"] == "completed"
    assert payload["result"]["isin"] == "INE002A01018"


def test_job_status_requires_auth(client):
    app_module._running_jobs["job_test"] = {"status": "running"}
    res = client.get("/job/job_test")
    assert res.status_code == 401

    res_ok = client.get("/job/job_test", headers=auth_headers())
    assert res_ok.status_code == 200
    assert res_ok.get_json()["job_id"] == "job_test"
