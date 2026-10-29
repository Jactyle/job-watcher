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
