from pipeline.sources import _strip, read_raw, write_raw


def test_strip_drops_descriptions_but_keeps_posting_lists():
    raw = {"content": [{"id": "1", "descriptionHtml": "<p>x</p>", "name": "A"}], "jobs": [{"id": "2"}]}
    assert _strip(raw) == {"content": [{"id": "1", "name": "A"}], "jobs": [{"id": "2"}]}


def test_raw_roundtrip_is_deterministic(tmp_path):
    write_raw(tmp_path / "a.json.gz", {"b": 1, "a": [1, 2]})
    write_raw(tmp_path / "b.json.gz", {"a": [1, 2], "b": 1})
    assert read_raw(tmp_path / "a.json.gz") == {"a": [1, 2], "b": 1}
    assert (tmp_path / "a.json.gz").read_bytes() == (tmp_path / "b.json.gz").read_bytes()


def test_429_is_waited_out_not_counted_as_a_failure(monkeypatch):
    import io, json, urllib.error
    from pipeline import sources
    calls = {"n": 0}

    class Resp(io.BytesIO):
        def __enter__(self): return self
        def __exit__(self, *a): pass

    def fake_urlopen(req, timeout=0):
        calls["n"] += 1
        if calls["n"] <= 5:  # more 429s than `retries`
            raise urllib.error.HTTPError(req.full_url, 429, "Too Many Requests", {"Retry-After": "1"}, None)
        return Resp(json.dumps({"ok": 1}).encode())

    slept = []
    monkeypatch.setattr(sources.urllib.request, "urlopen", fake_urlopen)
    monkeypatch.setattr(sources.time, "sleep", slept.append)
    assert sources._request("https://x", retries=1) == {"ok": 1}
    assert slept == [1.0] * 5


def test_other_errors_still_fail_after_retries(monkeypatch):
    import urllib.error
    import pytest
    from pipeline import sources
    monkeypatch.setattr(sources.time, "sleep", lambda s: None)
    monkeypatch.setattr(sources.urllib.request, "urlopen",
                        lambda req, timeout=0: (_ for _ in ()).throw(urllib.error.HTTPError(req.full_url, 500, "boom", {}, None)))
    with pytest.raises(urllib.error.HTTPError):
        sources._request("https://x", retries=2)
