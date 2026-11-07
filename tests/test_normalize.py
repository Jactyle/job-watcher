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

def test_workday_multi_location_uses_first_location_from_path():
    def loc(text, path):
        raw = {"jobPostings": [{"title": "A", "externalPath": path, "locationsText": text, "bulletFields": ["R1"]}]}
        return convert(raw, src("workday", host="h", site="S"))[0]["location"]
    assert loc("2 Locations", "/job/US-CA-Santa-Clara/A_R1") == "US, CA, Santa Clara"
    assert loc("2 Locations", "/job/McLean-VA/A_R1") == "McLean, VA"
    assert loc("2 Locations", "/job/Intel-Oregon-Hillsboro/A_R1") == "Intel Oregon Hillsboro"
    assert loc("3 Locations", "/job/California---San-Francisco/A_R1") == "California, San Francisco"
    assert loc("Austin, TX", "/job/Other-Place/A_R1") == "Austin, TX"

def test_blank_placeholders_are_dropped_from_a_location():
    raw = {"jobs": [{"id": 1, "title": "A", "location": {"name": "BLANK,BLANK,Multiple Locations"}, "absolute_url": "u"},
                    {"id": 2, "title": "B", "location": {"name": "Austin,TX"}, "absolute_url": "u"}]}
    rows = convert(raw, src("greenhouse"))
    assert [r["location"] for r in rows] == ["Multiple Locations", "Austin,TX"]

def test_workday_id_falls_back_to_path():
    raw = {"jobPostings": [{"title": "A", "externalPath": "/job/X/A_R22"}]}
    [r] = convert(raw, src("workday", host="h", site="S"))
    assert r["source_id"] == "R22"

def test_duplicate_ids_collapse():
    raw = [{"id": "1", "text": "A"}, {"id": "1", "text": "A again"}]
    assert len(convert(raw, src("lever"))) == 1


def test_apple():
    raw = {"searchResults": [{"positionId": "200692348", "postingTitle": "Data Analyst, Maps",
                              "transformedPostingTitle": "data-analyst-maps", "team": {"teamName": "Software"},
                              "locations": [{"name": "Cupertino"}, {"name": "Austin"}],
                              "postDateInGMT": "2026-10-29T21:40:52.612787842Z"}]}
    [r] = convert(raw, src("apple"))
    check(r)
    assert r["location"] == "Cupertino; Austin" and r["department"] == "Software"
    assert r["url"] == "https://jobs.apple.com/en-us/details/200692348/data-analyst-maps"
    assert r["posted_date"] == "2026-10-29"


def test_amazon():
    raw = {"jobs": [{"id_icims": "10500379", "title": "Business Analyst", "normalized_location": "Seattle, Washington, USA",
                     "job_category": "Finance", "posted_date": "August 12, 2026", "job_path": "/en/jobs/10500379/ba"}]}
    [r] = convert(raw, src("amazon"))
    check(r)
    assert r["posted_date"] == "2026-08-12" and r["url"] == "https://www.amazon.jobs/en/jobs/10500379/ba"
    assert (r["location"], r["department"]) == ("Seattle, Washington, USA", "Finance")
