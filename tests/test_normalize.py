from pipeline.normalize import COLUMNS, convert

def src(ats, **kw):
    return {"name": "acme", "employer": "Acme", "ats": ats, "board": "acme", **kw}

def check(row):
    for col in ("posting_id", "source", "source_id", "employer", "title", "location",
                "department", "posted_date", "url", "in_role"):
        assert col in row
    assert set(row) <= set(COLUMNS)

def test_greenhouse():
    raw = {"jobs": [{"id": 7, "title": " Financial  Analyst ", "location": {"name": "NYC"},
                     "absolute_url": "https://x/7", "first_published": "2026-08-19T20:00:00-04:00"}]}
    [r] = convert(raw, src("greenhouse"))
    check(r)
    assert r["posting_id"] == "acme:7" and r["title"] == "Financial Analyst"
    assert r["location"] == "NYC" and r["department"] == ""
    assert r["posted_date"] == "2026-08-20"  # converted to UTC
    assert r["in_role"] is True

def test_lever():
    raw = [{"id": "abc", "text": "Chef", "categories": {"location": "Paris", "department": "Food"},
            "createdAt": 1790000000000, "hostedUrl": "https://l/abc"}]
    [r] = convert(raw, src("lever"))
    check(r)
    assert (r["location"], r["department"], r["url"]) == ("Paris", "Food", "https://l/abc")
    assert r["posted_date"] == "2026-09-21" and r["in_role"] is False

def test_ashby_skips_unlisted():
    raw = {"jobs": [
        {"id": "a", "title": "FP&A Analyst", "location": "Remote", "department": "Finance",
         "publishedAt": "2026-04-07T17:12:35.753+00:00", "jobUrl": "https://a/a", "isListed": True},
        {"id": "b", "title": "Hidden", "isListed": False}]}
    rows = convert(raw, src("ashby"))
    assert [r["source_id"] for r in rows] == ["a"]
    check(rows[0])
    assert rows[0]["posted_date"] == "2026-04-07" and rows[0]["department"] == "Finance"

def test_smartrecruiters():
    raw = {"content": [{"id": "9", "name": "Credit Analyst", "releasedDate": "2026-10-29T18:33:59.322Z",
                        "location": {"fullLocation": "Austin, Texas, United States"},
                        "department": {"label": "Risk"}}]}
    [r] = convert(raw, src("smartrecruiters", board="Acme"))
    check(r)
    assert r["url"] == "https://jobs.smartrecruiters.com/Acme/9"
    assert r["location"] == "Austin, Texas, United States" and r["department"] == "Risk"
    assert r["posted_date"] == "2026-10-29"

def test_workday():
    raw = {"jobPostings": [{"title": "Analyst", "externalPath": "/job/X/Analyst_R1",
                            "locationsText": "2 Locations", "postedOn": "Posted Today",
                            "bulletFields": ["R1"]}]}
    [r] = convert(raw, src("workday", host="h.example.com", site="Site"))
    check(r)
    assert r["source_id"] == "R1" and r["url"] == "https://h.example.com/Site/job/X/Analyst_R1"
    assert r["posted_date"] == "" and r["department"] == ""

def test_workday_id_falls_back_to_path():
    raw = {"jobPostings": [{"title": "A", "externalPath": "/job/X/A_R22"}]}
    [r] = convert(raw, src("workday", host="h", site="S"))
    assert r["source_id"] == "R22"

def test_duplicate_ids_collapse():
    raw = [{"id": "1", "text": "A"}, {"id": "1", "text": "A again"}]
    assert len(convert(raw, src("lever"))) == 1
