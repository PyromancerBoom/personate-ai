import pytest

from app.models import FrictionMoment, SimulationReport, SimulationRun
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


def test_list_runs_returns_newest_summaries_and_skips_corrupt_files(tmp_path):
    s = RunStorage(tmp_path / "runs")
    older = SimulationRun(
        id=s.new_run_id(),
        url="http://older.test",
        goal="older goal",
        status="draft",
        updated_at="2026-01-01T00:00:00+00:00",
    )
    newer = SimulationRun(
        id=s.new_run_id(),
        url="http://newer.test",
        goal="newer goal",
        status="completed",
        updated_at="2026-01-02T00:00:00+00:00",
        report=SimulationReport(
            outcome="partial",
            summary="summary",
            persona_narrative="narrative",
            friction_moments=[
                FrictionMoment(
                    step=1,
                    severity="medium",
                    finding="finding",
                    screenshot="step_001.png",
                    recommendation="recommendation",
                )
            ],
        ),
    )
    s.save_run(older)
    s.save_run(newer)
    bad_dir = s.runs_dir / "badbadbadbad"
    bad_dir.mkdir(parents=True)
    (bad_dir / "run.json").write_text("{not valid json", encoding="utf-8")

    summaries = s.list_runs()

    assert [summary.id for summary in summaries] == [newer.id, older.id]
    assert summaries[0].findings == 1
    assert summaries[0].outcome == "partial"
    assert summaries[1].findings == 0
