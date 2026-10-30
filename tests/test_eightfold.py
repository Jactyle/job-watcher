from pipeline import sources


def test_second_pass_recovers_postings_skipped_by_a_shifting_list(monkeypatch):
    passes = iter([([{"id": 1}, {"id": 3}], 3), ([{"id": 1}, {"id": 2}, {"id": 3}], 3)])
    monkeypatch.setattr(sources, "_eightfold_pass", lambda src: next(passes))
    out = sources.fetch_eightfold({})
    assert sorted(p["id"] for p in out["positions"]) == [1, 2, 3]


def test_no_second_pass_when_the_first_is_complete(monkeypatch):
    calls = []
    monkeypatch.setattr(sources, "_eightfold_pass", lambda src: (calls.append(1) or [{"id": 1}, {"id": 2}], 2))
    sources.fetch_eightfold({})
    assert len(calls) == 1


def _http_error(code):
    import urllib.error
    return urllib.error.HTTPError("https://x", code, "err", {}, None)


def test_a_brief_403_block_is_waited_out_and_the_crawl_continues(monkeypatch):
    replies = iter([{"data": {"count": 2, "positions": [{"id": 1}]}}, _http_error(403), _http_error(403),
                    {"data": {"count": 2, "positions": [{"id": 2}]}}])
    def fake(url, **kw):
        r = next(replies)
        if isinstance(r, Exception):
            raise r
        return r
    slept = []
    monkeypatch.setattr(sources, "_request", fake)
    monkeypatch.setattr(sources.time, "sleep", slept.append)
    positions, total = sources._eightfold_pass({"host": "h", "domain": "d"}, blocks=5, block_wait=7)
    assert [p["id"] for p in positions] == [1, 2] and slept == [7, 7]


def test_a_board_that_stays_blocked_fails_after_the_block_budget(monkeypatch):
    import pytest, urllib.error
    slept = []
    monkeypatch.setattr(sources, "_request", lambda url, **kw: (_ for _ in ()).throw(_http_error(403)))
    monkeypatch.setattr(sources.time, "sleep", slept.append)
    with pytest.raises(urllib.error.HTTPError):
        sources._eightfold_pass({"host": "h", "domain": "d"}, blocks=3, block_wait=7)
    assert slept == [7, 7, 7]


def test_other_errors_are_not_waited_out(monkeypatch):
    import pytest, urllib.error
    monkeypatch.setattr(sources, "_request", lambda url, **kw: (_ for _ in ()).throw(_http_error(500)))
    monkeypatch.setattr(sources.time, "sleep", lambda s: pytest.fail("slept"))
    with pytest.raises(urllib.error.HTTPError):
        sources._eightfold_pass({"host": "h", "domain": "d"})
