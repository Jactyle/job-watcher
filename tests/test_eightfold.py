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
