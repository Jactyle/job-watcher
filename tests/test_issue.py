from pipeline.issue import build_body

def row(pid, **kw):
    base = {"posting_id": pid, "employer": "Acme", "title": pid, "url": f"https://x/{pid}", "location": "NYC",
            "in_role": False, "first_run": False, "first_seen": "2026-01-02", "removed_date": ""}
    return {**base, **kw}

def test_body_lists_new_and_removed_with_links():
    body = build_body("2026-01-02", [
        row("a"), row("b", first_seen="2026-01-01", removed_date="2026-01-02"),
        row("c", first_run=True, first_seen="2026-01-02")])
    assert "New postings (1)" in body and "https://x/a" in body
    assert "Removed postings (1)" in body and "https://x/b" in body
    assert "https://x/c" not in body

def test_body_on_quiet_day():
    assert "None." in build_body("2026-01-02", [])


def _fake_gh(monkeypatch, issues):
    import json
    from pipeline import issue
    calls = []

    def fake(*args):
        calls.append(args)
        return json.dumps(issues) if args[:2] == ("issue", "list") else ""

    monkeypatch.setattr(issue, "_gh", fake)
    return calls


def test_publish_opens_today_and_closes_the_previous_day(monkeypatch):
    from pipeline import issue
    calls = _fake_gh(monkeypatch, [{"number": 1, "title": "2026-01-01", "state": "OPEN"}])
    issue.publish("2026-01-02", [])
    creates = [c for c in calls if c[:2] == ("issue", "create")]
    closes = [c for c in calls if c[:2] == ("issue", "close")]
    assert len(creates) == 1 and creates[0][creates[0].index("--title") + 1] == "2026-01-02"
    assert len(closes) == 1 and closes[0][2] == "1"


def test_publish_on_the_same_day_updates_instead_of_duplicating(monkeypatch):
    from pipeline import issue
    calls = _fake_gh(monkeypatch, [{"number": 7, "title": "2026-01-02", "state": "OPEN"}])
    issue.publish("2026-01-02", [])
    assert not [c for c in calls if c[:2] == ("issue", "create")]
    assert [c for c in calls if c[:2] == ("issue", "edit")] and not [c for c in calls if c[:2] == ("issue", "close")]
