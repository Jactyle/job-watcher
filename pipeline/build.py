"""Build data/history.csv from the raw files alone.

    python -m pipeline.build
"""
from __future__ import annotations

import csv
import json
from pathlib import Path

from .normalize import COLUMNS, convert
from .sources import SOURCES, read_raw

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "data"
RAW = DATA / "raw"


def apply_day(history: dict, date: str, src: dict, rows: list[dict], first_date: str,
              open_ids: set | None = None) -> None:
    """Fold one source's listing for one day into the history (mutates `history`).

    `open_ids` is the set of this source's open posting ids; the build passes one per source so a day
    costs the size of that source, not of the whole history. Without it the history is scanned.
    """
    if open_ids is None:
        open_ids = {pid for pid, old in history.items() if old["source"] == src["name"] and old["status"] == "open"}
    listed = set()
    for row in rows:
        pid = row["posting_id"]
        listed.add(pid)
        old = history.get(pid)
        if old is None:
            history[pid] = {**row, "first_run": date == first_date, "first_seen": date,
                            "last_seen": date, "status": "open", "removed_date": ""}
        else:
            keep = {k: old[k] for k in ("first_run", "first_seen")}
            old.update(row)
            old.update(keep)
            old["last_seen"] = date
            old["status"] = "open"
            old["removed_date"] = ""
        open_ids.add(pid)
    for pid in open_ids - listed:
        history[pid]["status"] = "removed"
        history[pid]["removed_date"] = date
    open_ids &= listed


def raw_dates(raw_dir: Path = RAW) -> list[str]:
    return sorted(p.name for p in raw_dir.iterdir() if p.is_dir()) if raw_dir.exists() else []


def build_history(raw_dir: Path = RAW, sources: list[dict] = SOURCES) -> list[dict]:
    dates = raw_dates(raw_dir)
    first_date = {}
    for date in dates:
        for src in sources:
            if (raw_dir / date / f"{src['name']}.json.gz").exists():
                first_date.setdefault(src["name"], date)
    history: dict[str, dict] = {}
    open_ids = {src["name"]: set() for src in sources}
    for date in dates:
        for src in sources:
            path = raw_dir / date / f"{src['name']}.json.gz"
            if path.exists():
                apply_day(history, date, src, convert(read_raw(path), src), first_date[src["name"]],
                          open_ids[src["name"]])
    return [history[k] for k in sorted(history)]


def write_history(rows: list[dict], path: Path = DATA / "history.csv") -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=COLUMNS, lineterminator="\n")
        w.writeheader()
        for r in rows:
            w.writerow({**r, "in_role": str(r["in_role"]).lower(),
                        "first_run": str(r["first_run"]).lower()})


def compute_status(rows: list[dict], run_time: str, results: list[dict], raw_dir: Path = RAW) -> dict:
    dates = raw_dates(raw_dir)
    latest = dates[-1] if dates else ""
    return {
        "run_time": run_time,
        "first_run_date": dates[0] if dates else "",
        "days_with_success": len(dates),
        "open": sum(r["status"] == "open" for r in rows),
        "new_today": sum(r["first_seen"] == latest and not r["first_run"] for r in rows),
        "removed_today": sum(r["removed_date"] == latest for r in rows),
        "sources": results,
    }


def write_status(status: dict, path: Path = DATA / "status.json") -> None:
    path.write_text(json.dumps(status, indent=2) + "\n", encoding="utf-8")


if __name__ == "__main__":
    write_history(build_history())
    print(f"wrote {DATA / 'history.csv'}")
