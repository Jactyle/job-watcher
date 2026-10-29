import csv
import json

from pipeline import build
from pipeline.sources import write_raw

SRC = {"name": "acme", "employer": "Acme", "ats": "lever", "board": "acme"}
OTHER = {"name": "other", "employer": "Other", "ats": "lever", "board": "other"}

def job(i, title="Financial Analyst"):
    return {"id": str(i), "text": title, "categories": {}, "hostedUrl": f"https://x/{i}"}

def put(raw_dir, date, src, ids):
    write_raw(raw_dir / date / f"{src['name']}.json.gz", [job(i) for i in ids])

def history(raw_dir, sources=(SRC,)):
    return {r["source_id"]: r for r in build.build_history(raw_dir, list(sources))}

def test_first_seen_last_seen_and_first_run(tmp_path):
    put(tmp_path, "2026-01-01", SRC, [1, 2])
    put(tmp_path, "2026-01-02", SRC, [1, 2, 3])
    h = history(tmp_path)
    assert h["1"]["first_run"] is True and h["3"]["first_run"] is False
    assert (h["1"]["first_seen"], h["1"]["last_seen"]) == ("2026-01-01", "2026-01-02")
    assert (h["3"]["first_seen"], h["3"]["last_seen"]) == ("2026-01-02", "2026-01-02")
    assert all(r["status"] == "open" and r["removed_date"] == "" for r in h.values())

def test_removed_when_no_longer_listed(tmp_path):
    put(tmp_path, "2026-01-01", SRC, [1, 2])
    put(tmp_path, "2026-01-02", SRC, [1])
    h = history(tmp_path)
    assert (h["2"]["status"], h["2"]["removed_date"], h["2"]["last_seen"]) == ("removed", "2026-01-02", "2026-01-01")
    assert h["1"]["status"] == "open"

def test_reappearing_posting_reopens(tmp_path):
    put(tmp_path, "2026-01-01", SRC, [1])
    put(tmp_path, "2026-01-02", SRC, [])
    put(tmp_path, "2026-01-03", SRC, [1])
    h = history(tmp_path)["1"]
    assert (h["status"], h["removed_date"], h["first_seen"], h["last_seen"]) == ("open", "", "2026-01-01", "2026-01-03")
    assert h["first_run"] is True

def test_failed_source_day_does_not_remove(tmp_path):
    put(tmp_path, "2026-01-01", SRC, [1])
    put(tmp_path, "2026-01-01", OTHER, [9])
    put(tmp_path, "2026-01-02", OTHER, [9])  # SRC has no raw file on day 2
    h = history(tmp_path, (SRC, OTHER))
    assert h["1"]["status"] == "open" and h["1"]["last_seen"] == "2026-01-01"

def test_first_run_is_per_source(tmp_path):
    put(tmp_path, "2026-01-01", SRC, [1])
    put(tmp_path, "2026-01-02", SRC, [1])
    put(tmp_path, "2026-01-02", OTHER, [9])  # OTHER's first raw file is day 2
    h = history(tmp_path, (SRC, OTHER))
    assert h["9"]["first_run"] is True

def test_rows_sorted_and_rebuild_is_identical(tmp_path):
    put(tmp_path, "2026-01-01", OTHER, [2, 1])
    put(tmp_path, "2026-01-01", SRC, [3])
    rows = build.build_history(tmp_path, [SRC, OTHER])
    assert [r["posting_id"] for r in rows] == sorted(r["posting_id"] for r in rows)
    build.write_history(rows, tmp_path / "a.csv")
    build.write_history(build.build_history(tmp_path, [SRC, OTHER]), tmp_path / "b.csv")
    assert (tmp_path / "a.csv").read_bytes() == (tmp_path / "b.csv").read_bytes()

def test_csv_columns_and_booleans(tmp_path):
    put(tmp_path, "2026-01-01", SRC, [1])
    build.write_history(build.build_history(tmp_path, [SRC]), tmp_path / "h.csv")
    [row] = list(csv.DictReader(open(tmp_path / "h.csv")))
    assert list(row) == build.COLUMNS
    assert row["in_role"] == "true" and row["first_run"] == "true"

def test_status_counts(tmp_path):
    put(tmp_path, "2026-01-01", SRC, [1, 2])
    put(tmp_path, "2026-01-02", SRC, [1, 3])
    rows = build.build_history(tmp_path, [SRC])
    st = build.compute_status(rows, "2026-01-02T05:00:00Z", [{"name": "acme", "ok": True, "count": 2}], tmp_path)
    assert (st["first_run_date"], st["days_with_success"]) == ("2026-01-01", 2)
    assert (st["open"], st["new_today"], st["removed_today"]) == (2, 1, 1)
    json.dumps(st)
