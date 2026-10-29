from pipeline.sources import _strip, read_raw, write_raw


def test_strip_drops_descriptions_but_keeps_posting_lists():
    raw = {"content": [{"id": "1", "descriptionHtml": "<p>x</p>", "name": "A"}], "jobs": [{"id": "2"}]}
    assert _strip(raw) == {"content": [{"id": "1", "name": "A"}], "jobs": [{"id": "2"}]}


def test_raw_roundtrip_is_deterministic(tmp_path):
    write_raw(tmp_path / "a.json.gz", {"b": 1, "a": [1, 2]})
    write_raw(tmp_path / "b.json.gz", {"a": [1, 2], "b": 1})
    assert read_raw(tmp_path / "a.json.gz") == {"a": [1, 2], "b": 1}
    assert (tmp_path / "a.json.gz").read_bytes() == (tmp_path / "b.json.gz").read_bytes()
