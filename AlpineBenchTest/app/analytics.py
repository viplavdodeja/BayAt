"""Flatten recorded runs into stable, typed analytics rows."""
from datetime import date, datetime, timezone


def timestamp(value):
    if not value:
        return None
    return datetime.fromisoformat(value).astimezone(timezone.utc).replace(tzinfo=None)


def run_rows(data, steps):
    base = ["Job number", "Run ID", "Serial number", "Test date", "Test number",
            "Status", "Decision", "Started (UTC)", "Completed (UTC)",
            "Failed attempts", "Previously failed steps", "Notes"]
    specs = []
    for step in steps:
        keys = [f["id"] for f in step["fields"]]
        if step["kind"] == "decay":
            keys += ["elapsed_seconds"]
            keys += [s + suffix for s in step["sensors"] for suffix in ("_difference", "_decay", "_pass")]
        if step["id"] == "vac2":
            keys += [f["id"] + "_pass" for f in step["fields"] if f["type"] == "number"]
        specs.append((step, keys))
    headers = base[:]
    for step, keys in specs:
        headers += [step["title"] + " | " + key for key in ["Result", "Attempts", *keys]]
    rows = []
    for run_number, run in enumerate(data["runs"], start=1):
        failed = [a for a in run["attempts"] if not a["passed"]]
        row = [data["job"], run_number, run["serial"], date.fromisoformat(run["date"]),
               run["test_number"], run["status"], run["decision"], timestamp(run.get("started_at")),
               timestamp(run.get("completed_at")), len(failed),
               "; ".join(dict.fromkeys(a["title"] for a in failed)), "\n".join(run["notes"])]
        for step, keys in specs:
            attempts = [a for a in run["attempts"] if a["step"] == step["id"]]
            latest = attempts[-1] if attempts else None
            row += [("Pass" if latest["passed"] else "Fail") if latest else None, len(attempts)]
            row += [latest["values"].get(key) if latest else None for key in keys]
        rows.append(row)
    return headers, rows
