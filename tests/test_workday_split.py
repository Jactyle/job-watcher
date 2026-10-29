from pipeline import sources


def test_capped_workday_query_is_split_by_facet(monkeypatch):
    monkeypatch.setattr(sources, "WORKDAY_CAP", 4)
    data = {"A": ["a1", "a2", "a3"], "B": ["b1", "b2"], None: ["a1", "a2", "a3", "b1"]}  # None = unfiltered, capped at 4

    def fake(url, body):
        group = (body["appliedFacets"].get("jobFamilyGroup") or [None])[0]
        ids = data[group]
        page = {"total": 5 if group is None else len(ids),
                "jobPostings": [{"externalPath": f"/job/{i}"} for i in ids[body["offset"]:body["offset"] + body["limit"]]]}
        page["facets"] = [{"facetParameter": "jobFamilyGroup", "values": [{"id": "A"}, {"id": "B"}]}]
        return page

    monkeypatch.setattr(sources, "_request", fake)
    src = {"name": "x", "host": "h", "tenant": "t", "site": "s"}
    out = sources.fetch_workday(src)
    assert out["total"] == 5
    assert sorted(p["externalPath"] for p in out["jobPostings"]) == [f"/job/{i}" for i in ("a1", "a2", "a3", "b1", "b2")]


def test_entries_without_a_path_are_skipped(monkeypatch):
    page = {"total": 2, "jobPostings": [{"title": "no path"}, {"title": "ok", "externalPath": "/job/1"}], "facets": []}
    monkeypatch.setattr(sources, "_request", lambda url, body: page)
    out = sources.fetch_workday({"name": "x", "host": "h", "tenant": "t", "site": "s"})
    assert [p["externalPath"] for p in out["jobPostings"]] == ["/job/1"]
