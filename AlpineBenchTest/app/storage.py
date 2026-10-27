"""Durable per-job records; Excel files are derived from these records."""
import json
import os
import re
import tempfile
import uuid
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def load_config(name):
    return json.loads((ROOT / "config" / name).read_text(encoding="utf-8"))


def now():
    return datetime.now(timezone.utc).isoformat()


def validate_identifier(value, label):
    value = value.strip()
    if not value or len(value) > 80 or not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9 _.-]*", value):
        raise ValueError(label + " must start with a letter or number and contain only letters, numbers, spaces, _, . or - (80 characters maximum).")
    if value.endswith((".", " ")) or value.split(".")[0].upper() in {"CON", "PRN", "AUX", "NUL", *["COM" + str(i) for i in range(1, 10)], *["LPT" + str(i) for i in range(1, 10)]}:
        raise ValueError(label + " is not a portable Windows filename.")
    return value


class Store:
    def __init__(self, destination=None):
        self.export_error: str | None = None
        setting = destination or load_config("settings.json")["results_directory"]
        self.root = Path(setting).expanduser()
        if not self.root.is_absolute():
            self.root = ROOT / self.root

    def job_path(self, job):
        return self.root / validate_identifier(job, "Job number")

    def load(self, job):
        path = self.job_path(job) / "records.json"
        if not path.exists():
            return {"schema_version": 1, "job": job, "runs": []}
        data = json.loads(path.read_text(encoding="utf-8"))
        if data.get("schema_version") != 1 or data.get("job") != job:
            raise ValueError("Job record does not match the expected format. Contact support.")
        return data

    def save(self, data):
        path = self.job_path(data["job"])
        path.mkdir(parents=True, exist_ok=True)
        descriptor, temporary = tempfile.mkstemp(prefix="records-", suffix=".tmp", dir=path)
        try:
            with os.fdopen(descriptor, "w", encoding="utf-8") as stream:
                json.dump(data, stream, indent=2, allow_nan=False)
                stream.flush()
                os.fsync(stream.fileno())
            os.replace(temporary, path / "records.json")
        finally:
            if os.path.exists(temporary):
                os.unlink(temporary)
        # Export failure must not roll back already committed test records.
        self.export_error = None
        try:
            from .outputs import export_analytics
            export_analytics(data, load_config("test_steps.json"), path)
        except Exception as error:
            self.export_error = str(error)

    def new_run(self, data, serial, date):
        serial = validate_identifier(serial, "Serial number")
        count = sum(r["serial"].casefold() == serial.casefold() for r in data["runs"]) + 1
        run = {"id": str(uuid.uuid4()), "serial": serial, "date": date,
               "test_number": count, "started_at": now(), "status": "In progress",
               "decision": "", "step_index": 0, "attempts": [], "notes": [],
               "pending_failure": False, "zero_confirmations": []}
        if count > 1:
            run["notes"].append(f"Test {count} for this unit (re-test).")
        data["runs"].append(run)
        self.save(data)
        return run
