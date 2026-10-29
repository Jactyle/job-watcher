from pipeline import build
from pipeline.run import run_sources

A = {"name": "a", "employer": "A", "ats": "lever", "board": "a"}
B = {"name": "b", "employer": "B", "ats": "lever", "board": "b"}


def fetcher(src):
    if src["name"] == "b":
        raise RuntimeError("blocked")
    return [{"id": "1", "text": "Financial Analyst", "categories": {}, "hostedUrl": "https://x/1"}]


def test_failed_source_is_recorded_and_writes_no_file(tmp_path):
    results = run_sources([A, B], tmp_path / "2026-01-01", fetcher)
    assert results == [{"name": "a", "ok": True, "count": 1}, {"name": "b", "ok": False, "count": 0}]
    assert (tmp_path / "2026-01-01" / "a.json.gz").exists()
    assert not (tmp_path / "2026-01-01" / "b.json.gz").exists()


def test_run_output_feeds_the_build(tmp_path):
    run_sources([A, B], tmp_path / "2026-01-01", fetcher)
    [row] = build.build_history(tmp_path, [A, B])
    assert row["posting_id"] == "a:1" and row["in_role"] is True
