from __future__ import annotations

import json
import os
import re
import tempfile
import uuid
from datetime import datetime, timezone
from pathlib import Path

from .models import SimulationRun, SimulationReport


_RUN_ID_RE = re.compile(r"^[a-f0-9]{12}$")


def is_valid_run_id(run_id: str) -> bool:
    return bool(_RUN_ID_RE.match(run_id or ""))


class RunStorage:
    def __init__(self, runs_dir: Path):
        self.runs_dir = Path(runs_dir).resolve()
        self.runs_dir.mkdir(parents=True, exist_ok=True)

    def new_run_id(self) -> str:
        return uuid.uuid4().hex[:12]

    def run_dir(self, run_id: str) -> Path:
        d = (self.runs_dir / run_id).resolve()
        if self.runs_dir not in d.parents and d != self.runs_dir:
            raise ValueError("invalid run_id")
        return d

    def screenshots_dir(self, run_id: str) -> Path:
        return self.run_dir(run_id) / "screenshots"

    def ensure_run_dirs(self, run_id: str) -> None:
        self.screenshots_dir(run_id).mkdir(parents=True, exist_ok=True)

    def screenshot_path(self, run_id: str, file_name: str) -> Path:
        if not file_name.endswith(".png"):
            raise ValueError("only .png screenshots are served")
        # Reject any path-traversal attempts.
        if "/" in file_name or "\\" in file_name or ".." in file_name:
            raise ValueError("invalid screenshot file name")
        sdir = self.screenshots_dir(run_id).resolve()
        path = (sdir / file_name).resolve()
        if sdir not in path.parents:
            raise ValueError("invalid screenshot path")
        return path

    def _atomic_write_json(self, path: Path, payload: dict) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        fd, tmp_path = tempfile.mkstemp(prefix=".tmp_", dir=str(path.parent))
        try:
            with os.fdopen(fd, "w", encoding="utf-8") as f:
                json.dump(payload, f, ensure_ascii=False, indent=2)
            os.replace(tmp_path, path)
        except Exception:
            try:
                os.unlink(tmp_path)
            except OSError:
                pass
            raise

    def save_run(self, run: SimulationRun) -> None:
        self.ensure_run_dirs(run.id)
        path = self.run_dir(run.id) / "run.json"
        self._atomic_write_json(path, run.model_dump(by_alias=True, exclude_none=True))

    def load_run(self, run_id: str) -> SimulationRun | None:
        path = self.run_dir(run_id) / "run.json"
        if not path.exists():
            return None
        with path.open("r", encoding="utf-8") as f:
            data = json.load(f)
        return SimulationRun.model_validate(data)

    def save_report(self, run_id: str, report: SimulationReport) -> None:
        path = self.run_dir(run_id) / "report.json"
        self._atomic_write_json(path, report.model_dump(by_alias=True, exclude_none=True))

    def sweep_orphaned_running(self) -> int:
        """Reset any runs left in `running` from a prior process to `failed`.

        Avoids permanent 409s on /start when uvicorn is killed mid-simulation.
        Returns the number of runs swept.
        """
        if not self.runs_dir.exists():
            return 0
        swept = 0
        for run_json in self.runs_dir.glob("*/run.json"):
            try:
                with run_json.open("r", encoding="utf-8") as f:
                    data = json.load(f)
                if data.get("status") != "running":
                    continue
                data["status"] = "failed"
                data["error"] = "orphaned: process restarted while running"
                data["updatedAt"] = datetime.now(timezone.utc).isoformat()
                self._atomic_write_json(run_json, data)
                swept += 1
            except Exception:
                continue
        return swept
