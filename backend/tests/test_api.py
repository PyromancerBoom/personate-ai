from fastapi.testclient import TestClient

from app.config import Settings
from app.main import create_app
from app.storage import RunStorage
from tests.conftest import StubProvider


def _client(tmp_settings, provider=None):
    storage = RunStorage(tmp_settings.runs_dir)
    provider = provider or StubProvider()
    app = create_app(settings=tmp_settings, storage=storage, provider=provider)
    return TestClient(app), storage, provider


def test_create_run_returns_persona(tmp_settings):
    client, _, _ = _client(tmp_settings)
    resp = client.post(
        "/api/runs",
        json={"url": "http://localhost:3000", "goal": "test onboarding"},
    )
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["status"] == "draft"
    assert body["persona"]["name"] == "Maya Tester"
    assert "experienceLevel" in body["persona"]
    assert "createdAt" in body
    assert "error" not in body


def test_create_run_rejects_file_url(tmp_settings):
    client, _, _ = _client(tmp_settings)
    resp = client.post(
        "/api/runs", json={"url": "file:///etc/passwd", "goal": "x"}
    )
    assert resp.status_code == 400


def test_create_run_rejects_empty_goal(tmp_settings):
    client, _, _ = _client(tmp_settings)
    resp = client.post(
        "/api/runs", json={"url": "http://localhost:3000", "goal": "  "}
    )
    assert resp.status_code == 400


def test_create_run_missing_api_key(tmp_path):
    cfg = Settings(
        gemini_api_key="",
        runs_dir=tmp_path / "runs",
        max_journey_steps=4,
    )
    client, _, _ = _client(cfg)
    resp = client.post(
        "/api/runs", json={"url": "http://localhost:3000", "goal": "x"}
    )
    assert resp.status_code == 500


def test_get_missing_run_404(tmp_settings):
    client, _, _ = _client(tmp_settings)
    resp = client.get("/api/runs/nope")
    assert resp.status_code == 404


def test_screenshot_route_rejects_traversal(tmp_settings):
    client, storage, _ = _client(tmp_settings)
    rid = storage.new_run_id()
    storage.ensure_run_dirs(rid)
    resp = client.get(f"/api/runs/{rid}/screenshots/..%2F..%2Fetc%2Fpasswd")
    assert resp.status_code in (400, 404)


def test_screenshot_route_serves_png(tmp_settings):
    client, storage, _ = _client(tmp_settings)
    rid = storage.new_run_id()
    storage.ensure_run_dirs(rid)
    p = storage.screenshots_dir(rid) / "step_001.png"
    p.write_bytes(b"\x89PNG\r\n\x1a\n" + b"\x00" * 8)
    resp = client.get(f"/api/runs/{rid}/screenshots/step_001.png")
    assert resp.status_code == 200
    assert resp.headers["content-type"] == "image/png"


def test_start_already_completed_returns_409(tmp_settings):
    client, storage, _ = _client(tmp_settings)
    create = client.post(
        "/api/runs", json={"url": "http://localhost:3000", "goal": "x"}
    ).json()
    run = storage.load_run(create["id"])
    run.status = "completed"
    storage.save_run(run)
    resp = client.post(f"/api/runs/{create['id']}/start")
    assert resp.status_code == 409


def test_start_missing_run_404(tmp_settings):
    client, _, _ = _client(tmp_settings)
    # Use a syntactically valid run_id (12 hex) so we exercise the load path.
    resp = client.post("/api/runs/abcdef012345/start")
    assert resp.status_code == 404


def test_get_invalid_run_id_returns_404(tmp_settings):
    """Malformed IDs (not 12 hex chars) must return 404, not 500."""
    client, _, _ = _client(tmp_settings)
    for bad in ["nope", "../etc", "ABCDEF012345", "12345"]:
        resp = client.get(f"/api/runs/{bad}")
        assert resp.status_code == 404, f"{bad} returned {resp.status_code}"


def test_start_invalid_run_id_returns_404(tmp_settings):
    client, _, _ = _client(tmp_settings)
    resp = client.post("/api/runs/not-a-real-id/start")
    assert resp.status_code == 404


def test_start_run_happy_path_with_fake_simulation(tmp_settings, monkeypatch):
    """start_run should mark running, run the sim, and return the final run.

    We stub out run_simulation so the test doesn't need a real browser.
    """
    import app.main as main_mod
    from app.models import SimulationRun

    async def fake_run_simulation(*, run, settings, storage, provider):
        run.status = "completed"
        run.error = None
        storage.save_run(run)
        return run

    monkeypatch.setattr(main_mod, "run_simulation", fake_run_simulation)
    client, _, _ = _client(tmp_settings)
    create = client.post(
        "/api/runs", json={"url": "http://localhost:3000", "goal": "x"}
    ).json()
    resp = client.post(f"/api/runs/{create['id']}/start")
    assert resp.status_code == 200
    body = resp.json()
    assert body["status"] == "completed"
    assert "error" not in body


def test_start_run_failure_path_with_fake_simulation(tmp_settings, monkeypatch):
    import app.main as main_mod

    async def fake_run_simulation(*, run, settings, storage, provider):
        run.status = "failed"
        run.error = "browser launch/navigation failed: synthetic"
        storage.save_run(run)
        return run

    monkeypatch.setattr(main_mod, "run_simulation", fake_run_simulation)
    client, _, _ = _client(tmp_settings)
    create = client.post(
        "/api/runs", json={"url": "http://localhost:3000", "goal": "x"}
    ).json()
    resp = client.post(f"/api/runs/{create['id']}/start")
    assert resp.status_code == 200
    body = resp.json()
    assert body["status"] == "failed"
    assert "synthetic" in body["error"]


def test_orphan_sweep_resets_running_runs(tmp_settings):
    """Runs left as 'running' from a prior process must be reset on startup."""
    storage = RunStorage(tmp_settings.runs_dir)
    rid = storage.new_run_id()
    from app.models import SimulationRun
    storage.save_run(SimulationRun(id=rid, url="http://x", goal="g", status="running"))
    n = storage.sweep_orphaned_running()
    assert n == 1
    loaded = storage.load_run(rid)
    assert loaded.status == "failed"
    assert "orphaned" in (loaded.error or "")
