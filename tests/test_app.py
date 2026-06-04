import pytest
from starlette.testclient import TestClient
from concorde_policy_mapper_web.app import create_app


@pytest.fixture
def app_with_runs(tmp_runs, tmp_policies):
    app = create_app(runs_dir=tmp_runs, examples_dir=tmp_policies)
    return app


def test_landing_page(app_with_runs):
    client = TestClient(app_with_runs)
    resp = client.get("/")
    assert resp.status_code == 200
    assert "run-alpha" in resp.text
    assert "run-beta" in resp.text


def test_landing_page_empty(tmp_path, tmp_policies):
    app = create_app(runs_dir=tmp_path, examples_dir=tmp_policies)
    client = TestClient(app)
    resp = client.get("/")
    assert resp.status_code == 200
    assert "No runs" in resp.text


def test_run_detail_page(app_with_runs):
    client = TestClient(app_with_runs)
    resp = client.get("/runs/run-alpha")
    assert resp.status_code == 200
    assert "run-alpha" in resp.text
    assert "Risk 0" in resp.text


def test_run_detail_not_found(app_with_runs):
    client = TestClient(app_with_runs)
    resp = client.get("/runs/nonexistent")
    assert resp.status_code == 404


def test_risk_detail_page(app_with_runs):
    client = TestClient(app_with_runs)
    resp = client.get("/runs/run-alpha/risk/atlas-risk-0")
    assert resp.status_code == 200
    assert "Risk 0" in resp.text
    assert "Threat for risk 0" in resp.text


def test_risk_detail_not_found(app_with_runs):
    client = TestClient(app_with_runs)
    resp = client.get("/runs/run-alpha/risk/nonexistent-risk")
    assert resp.status_code == 404


def test_compare_page(app_with_runs):
    client = TestClient(app_with_runs)
    resp = client.get("/compare?runs=run-alpha,run-beta")
    assert resp.status_code == 200
    assert "run-alpha" in resp.text
    assert "run-beta" in resp.text


def test_compare_single_run(app_with_runs):
    client = TestClient(app_with_runs)
    resp = client.get("/compare?runs=run-alpha")
    assert resp.status_code == 400


def test_new_run_page(app_with_runs):
    client = TestClient(app_with_runs)
    resp = client.get("/run")
    assert resp.status_code == 200
    assert "New Run" in resp.text
