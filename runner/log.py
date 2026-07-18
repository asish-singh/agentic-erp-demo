"""
JSONL run logging. One file per task attempt, one JSON object per line, so
findings can be reconstructed later by analyze.py without re-running anything.
"""

from __future__ import annotations

import json
import os
from datetime import datetime, timezone


class RunLogger:
    def __init__(self, task_id: str, runs_dir: str, dry_run: bool):
        os.makedirs(runs_dir, exist_ok=True)
        timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
        suffix = "-dryrun" if dry_run else ""
        self.path = os.path.join(runs_dir, f"{timestamp}-{task_id}{suffix}.jsonl")
        self._fh = open(self.path, "a", encoding="utf-8")

    def write(self, record: dict) -> None:
        record = dict(record)
        record.setdefault("ts", datetime.now(timezone.utc).isoformat())
        self._fh.write(json.dumps(record, default=str) + "\n")
        self._fh.flush()

    def close(self) -> None:
        self._fh.close()
