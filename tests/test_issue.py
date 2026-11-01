from pipeline.issue import MARK, build_body, build_parts

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

def test_brackets_in_a_title_do_not_break_the_link():
    body = build_body("2026-01-02", [row("a", title="Analyst [Remote] II")])
    assert "[Analyst \\[Remote\\] II](https://x/a)" in body

def test_body_on_quiet_day():
    assert "None." in build_body("2026-01-02", [])


def _fake_gh(monkeypatch, issues, old_comment_ids=""):
    import json
    from pipeline import issue
    calls = []

    def fake(*args):
        calls.append(args)
        if args[:2] == ("issue", "list"):
            return json.dumps(issues)
        if args[:2] == ("issue", "create"):
            return "https://github.com/o/r/issues/42\n"
        if args[:1] == ("api",) and "DELETE" not in args:
            return old_comment_ids
        return ""

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


def _big_day(n_new=900, n_removed=900):
    rows = [row(f"new{i}", title="A long job title " + "x" * 60 + f" {i}", employer="Employer", in_role=i % 10 == 0) for i in range(n_new)]
    rows += [row(f"old{i}", title="Another long job title " + "y" * 60 + f" {i}", first_seen="2026-01-01", removed_date="2026-01-02") for i in range(n_removed)]
    return rows


def test_every_posting_is_listed_even_when_one_issue_body_cannot_hold_the_day():
    rows = _big_day()
    parts = build_parts("2026-01-02", rows)
    assert len(parts) > 1 and all(len(p) <= 65536 for p in parts)
    text = "\n".join(parts)
    assert text.count("](https://x/new") == 900 and text.count("](https://x/old") == 900   # nothing is dropped
    assert "more (see" not in text
    assert parts[0].startswith("Job watcher digest") and "New postings (900)" in parts[0]
    assert "comment" in parts[0].splitlines()[-2] or "comment" in parts[0]
    assert all(p.startswith(MARK) for p in parts[1:])


def test_a_continuation_names_the_section_it_continues():
    parts = build_parts("2026-01-02", _big_day(n_new=10, n_removed=1500))
    assert any("## Removed postings (continued)" in p for p in parts[1:])
    assert "Removed postings (1500)" in "\n".join(parts)


def test_a_small_day_is_one_issue_body_with_no_comments():
    assert len(build_parts("2026-01-02", [row("a"), row("b", first_seen="2026-01-01", removed_date="2026-01-02")])) == 1


def test_publish_posts_the_continuation_comments_in_order(monkeypatch):
    from pipeline import issue
    calls = _fake_gh(monkeypatch, [])
    rows = _big_day()
    issue.publish("2026-01-02", rows)
    comments = [c for c in calls if c[:2] == ("issue", "comment")]
    assert len(comments) == len(build_parts("2026-01-02", rows)) - 1 and all(c[2] == "42" for c in comments)


def test_a_second_run_today_replaces_the_old_continuation_comments(monkeypatch):
    from pipeline import issue
    calls = _fake_gh(monkeypatch, [{"number": 7, "title": "2026-01-02", "state": "OPEN"}], old_comment_ids="11\n12\n")
    issue.publish("2026-01-02", _big_day())
    deletes = [c for c in calls if c[:3] == ("api", "-X", "DELETE")]
    assert [c[3] for c in deletes] == ["repos/{owner}/{repo}/issues/comments/11", "repos/{owner}/{repo}/issues/comments/12"]
    first_delete = calls.index(deletes[0]); first_comment = next(i for i, c in enumerate(calls) if c[:2] == ("issue", "comment"))
    assert first_delete < first_comment                                     # old comments go before the new ones are posted
    assert not [c for c in calls if c[:2] == ("issue", "create")]


def test_a_second_run_with_a_smaller_day_still_clears_old_comments(monkeypatch):
    from pipeline import issue
    calls = _fake_gh(monkeypatch, [{"number": 7, "title": "2026-01-02", "state": "OPEN"}], old_comment_ids="11\n")
    issue.publish("2026-01-02", [])
    assert [c for c in calls if c[:3] == ("api", "-X", "DELETE")] and not [c for c in calls if c[:2] == ("issue", "comment")]


def test_digest_issues_are_found_by_their_date_title_not_by_the_label_filter(monkeypatch):
    """GitHub's label-filtered listing can come back empty, so the lookup must not use it."""
    from pipeline import issue
    calls = _fake_gh(monkeypatch, [{"number": 7, "title": "2026-01-02", "state": "OPEN"}])
    issue.publish("2026-01-02", [])
    listing = [c for c in calls if c[:2] == ("issue", "list")]
    assert len(listing) == 1 and "--label" not in listing[0]
    assert not [c for c in calls if c[:2] == ("issue", "create")]            # today's issue was found, so none is created


def test_only_digest_issues_are_ever_closed(monkeypatch):
    from pipeline import issue
    calls = _fake_gh(monkeypatch, [{"number": 3, "title": "Bug: the site is slow", "state": "OPEN"},
                                   {"number": 2, "title": "2026-01-01", "state": "OPEN"}])
    issue.publish("2026-01-02", [])
    closes = [c[2] for c in calls if c[:2] == ("issue", "close")]
    assert closes == ["2"]                                                    # the person's own issue is left alone
