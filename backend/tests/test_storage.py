import pytest

from app.models import SimulationRun
from app.storage import RunStorage


def test_storage_creates_layout(tmp_path):
    s = RunStorage(tmp_path / "runs")
    rid = s.new_run_id()
    s.ensure_run_dirs(rid)
    assert s.run_dir(rid).exists()
    assert s.screenshots_dir(rid).exists()


def test_save_and_load_run(tmp_path):
    s = RunStorage(tmp_path / "runs")
    rid = s.new_run_id()
    run = SimulationRun(id=rid, url="http://x", goal="g")
    s.save_run(run)
    loaded = s.load_run(rid)
    assert loaded is not None
    assert loaded.id == rid
    assert loaded.goal == "g"


def test_load_run_missing_returns_none(tmp_path):
    s = RunStorage(tmp_path / "runs")
    assert s.load_run("nonexistent") is None


def test_screenshot_path_rejects_traversal(tmp_path):
    s = RunStorage(tmp_path / "runs")
    rid = s.new_run_id()
    s.ensure_run_dirs(rid)
    with pytest.raises(ValueError):
        s.screenshot_path(rid, "../../etc/passwd")
    with pytest.raises(ValueError):
        s.screenshot_path(rid, "step.txt")
    with pytest.raises(ValueError):
        s.screenshot_path(rid, "sub/step.png")


def test_screenshot_path_accepts_valid(tmp_path):
    s = RunStorage(tmp_path / "runs")
    rid = s.new_run_id()
    s.ensure_run_dirs(rid)
    p = s.screenshot_path(rid, "step_001.png")
    assert p.name == "step_001.png"
