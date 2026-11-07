"""The watch list and the fetchers. Every request is anonymous and returns JSON."""
from __future__ import annotations

import gzip
import json
import time
import urllib.error
import urllib.request

UA = "job-watcher-student-project (github.com/Jactyle/job-watcher)"
TIMEOUT = 40

def _gh(name, employer, token):
    return {"name": name, "employer": employer, "ats": "greenhouse", "board": token}

def _wd(name, employer, host, tenant, site):
    return {"name": name, "employer": employer, "ats": "workday", "host": host, "tenant": tenant,
            "site": site, "board": site}

SOURCES = [
    _gh("robinhood", "Robinhood", "robinhood"),
    _gh("coinbase", "Coinbase", "coinbase"),
    _gh("stripe", "Stripe", "stripe"),
    _gh("affirm", "Affirm", "affirm"),
    _gh("brex", "Brex", "brex"),
    _gh("mercury", "Mercury", "mercury"),
    _gh("chime", "Chime", "chime"),
    _gh("carta", "Carta", "carta"),
    _gh("toast", "Toast", "toast"),
    _gh("sofi", "SoFi", "sofi"),
    _gh("gusto", "Gusto", "gusto"),
    _gh("betterment", "Betterment", "betterment"),
    _gh("databricks", "Databricks", "databricks"),
    _gh("airbnb", "Airbnb", "airbnb"),
    {"name": "palantir", "employer": "Palantir", "ats": "lever", "board": "palantir"},
    {"name": "spotify", "employer": "Spotify", "ats": "lever", "board": "spotify"},
    {"name": "ramp", "employer": "Ramp", "ats": "ashby", "board": "ramp"},
    {"name": "notion", "employer": "Notion", "ats": "ashby", "board": "notion"},
    {"name": "openai", "employer": "OpenAI", "ats": "ashby", "board": "openai"},
    _gh("epicgames", "Epic Games", "epicgames"),
    _gh("riotgames", "Riot Games", "riotgames"),
    _gh("roblox", "Roblox", "roblox"),
    _gh("discord", "Discord", "discord"),
    _gh("taketwo", "Take-Two Interactive", "taketwo"),
    _gh("rockstargames", "Rockstar Games", "rockstargames"),
    _gh("bungie", "Bungie", "bungie"),
    _gh("scopely", "Scopely", "scopely"),
    _gh("twitch", "Twitch", "twitch"),
    _gh("cloudflare", "Cloudflare", "cloudflare"),
    {"name": "supercell", "employer": "Supercell", "ats": "ashby", "board": "supercell"},
    {"name": "ubisoft", "employer": "Ubisoft", "ats": "smartrecruiters", "board": "Ubisoft2"},
    {"name": "apple", "employer": "Apple", "ats": "apple", "board": "apple"},
    {"name": "amazon", "employer": "Amazon", "ats": "amazon", "board": "amazon"},
    {"name": "servicenow", "employer": "ServiceNow", "ats": "smartrecruiters", "board": "ServiceNow"},
    _wd("sony", "Sony", "sonyglobal.wd1.myworkdayjobs.com", "sonyglobal", "SonyGlobalCareers"),
]

# A board with more than 5,000 postings must be requested with a search term (none is today).
SEARCH_TERMS: dict[str, str] = {"apple": "analyst", "amazon": "analyst"}

# Large free-text fields that are not needed; dropped so the committed raw files stay small.
DROP_KEYS = {"descriptionHtml", "descriptionPlain", "description", "descriptionBody",
             "descriptionBodyPlain", "additional", "additionalPlain", "lists", "opening",
             "openingPlain", "responsibilities", "qualifications",
             "jobSummary", "job_description", "basic_qualifications", "preferred_qualifications",
             "description_short"}


def _request(url, data=None, retries=3, backoff=2, throttle_waits=40, throttle_wait=3):
    """GET (or POST JSON) and return parsed JSON.

    Errors are retried `retries` times. A 429 (too many requests) does not count as a failure: it
    waits (the server's Retry-After, else `throttle_wait` seconds) and tries again, up to `throttle_waits` times.
    """
    headers = {"User-Agent": UA, "Accept": "application/json"}
    if data is not None:
        headers["Content-Type"] = "application/json"
        data = json.dumps(data).encode()
    attempts = waits = 0
    while True:
        try:
            req = urllib.request.Request(url, data=data, headers=headers)
            with urllib.request.urlopen(req, timeout=TIMEOUT) as resp:
                return json.loads(resp.read().decode("utf-8"))
        except urllib.error.HTTPError as exc:
            if exc.code == 429 and waits < throttle_waits:
                waits += 1
                try:
                    delay = min(float(exc.headers.get("Retry-After")), 30)
                except (TypeError, ValueError):
                    delay = throttle_wait
                time.sleep(delay)
                continue
            error = exc
        except Exception as exc:  # noqa: BLE001 - retried, then re-raised
            error = exc
        attempts += 1
        if attempts >= retries:
            raise error
        time.sleep(backoff * attempts)


def _strip(obj):
    if isinstance(obj, list):
        return [_strip(x) for x in obj]
    if isinstance(obj, dict):
        return {k: _strip(v) for k, v in obj.items() if k not in DROP_KEYS}
    return obj


def fetch_greenhouse(src):
    return _request(f"https://boards-api.greenhouse.io/v1/boards/{src['board']}/jobs")


def fetch_lever(src):
    return _request(f"https://api.lever.co/v0/postings/{src['board']}?mode=json")


def fetch_ashby(src):
    return _request(f"https://api.ashbyhq.com/posting-api/job-board/{src['board']}")


def fetch_smartrecruiters(src):
    content, offset, total = [], 0, None
    term = SEARCH_TERMS.get(src["name"], "")
    while total is None or offset < total:
        url = (f"https://api.smartrecruiters.com/v1/companies/{src['board']}/postings"
               f"?limit=100&offset={offset}" + (f"&q={term}" if term else ""))
        page = _request(url)
        total = page["totalFound"]
        if not page["content"]:
            break
        content.extend(page["content"])
        offset += len(page["content"])
    return {"totalFound": total, "content": content}


WORKDAY_CAP = 2000  # Workday serves at most 2,000 results per query
WORKDAY_SPLITS = ["jobFamilyGroup", "workerSubType", "locationMainGroup"]


def _workday_query(url, facets, term, seen, postings, splits):
    """Page through one query; if it hits the cap, re-query once per value of the next facet."""
    offset, total, first = 0, None, None
    while total is None or offset < min(total, WORKDAY_CAP):
        page = _request(url, {"appliedFacets": facets, "limit": 20, "offset": offset, "searchText": term})
        if total is None:  # Workday reports the total on the first page only
            total, first = page["total"], page
        items = page.get("jobPostings", [])
        if not items:
            break
        for item in items:
            path = item.get("externalPath")  # a few entries have no path (no page to link to): skip them
            if path and path not in seen:
                seen.add(path)
                postings.append(item)
        offset += len(items)
    if total >= WORKDAY_CAP and splits:
        facet = next((f for f in first.get("facets", []) if f["facetParameter"] == splits[0]), None)
        if facet is None:
            return total
        for value in facet.get("values", []):
            if "id" in value:
                _workday_query(url, {**facets, splits[0]: [value["id"]]}, term, seen, postings, splits[1:])
    return total


def fetch_workday(src):
    url = f"https://{src['host']}/wday/cxs/{src['tenant']}/{src['site']}/jobs"
    postings, seen = [], set()
    total = _workday_query(url, {}, SEARCH_TERMS.get(src["name"], ""), seen, postings, WORKDAY_SPLITS)
    if total and not postings:
        raise RuntimeError("workday returned a total but no postings")
    return {"total": len(postings), "jobPostings": postings}


def fetch_apple(src):
    """Apple's search API (POST, 20 per page). Apple has over 5,000 postings, so a search term is used."""
    results, page_no, total = [], 1, None
    while total is None or len(results) < total:
        page = _request("https://jobs.apple.com/api/v1/search", {
            "query": SEARCH_TERMS.get(src["name"], ""), "filters": {}, "page": page_no, "locale": "en-us",
            "sort": "", "format": {"longDate": "MMMM D, YYYY", "mediumDate": "MMM D, YYYY"}})["res"]
        total = page["totalRecords"]
        if not page["searchResults"]:
            break
        results.extend(page["searchResults"])
        page_no += 1
    return {"totalRecords": total, "searchResults": list({r["positionId"]: r for r in results}.values())}


def fetch_amazon(src):
    """amazon.jobs search.json (100 per page). Amazon has over 5,000 postings, so a search term is used."""
    jobs, offset, hits = [], 0, None
    term = SEARCH_TERMS.get(src["name"], "")
    while hits is None or offset < hits:
        page = _request(f"https://www.amazon.jobs/en/search.json?result_limit=100&offset={offset}&base_query={term}")
        hits = page["hits"]
        if not page["jobs"]:
            break
        jobs.extend(page["jobs"])
        offset += len(page["jobs"])
    return {"hits": hits, "jobs": list({j["id_icims"]: j for j in jobs}.values())}


FETCHERS = {
    "greenhouse": fetch_greenhouse,
    "lever": fetch_lever,
    "ashby": fetch_ashby,
    "smartrecruiters": fetch_smartrecruiters,
    "workday": fetch_workday,
    "apple": fetch_apple,
    "amazon": fetch_amazon,
}


def fetch(src):
    return _strip(FETCHERS[src["ats"]](src))


def write_raw(path, payload):
    path.parent.mkdir(parents=True, exist_ok=True)
    # mtime=0 keeps the gzip bytes identical for identical payloads
    with open(path, "wb") as out, gzip.GzipFile(filename="", fileobj=out, mode="wb", mtime=0) as f:
        f.write(json.dumps(payload, separators=(",", ":"), sort_keys=True).encode())


def read_raw(path):
    with gzip.open(path, "rb") as f:
        return json.loads(f.read().decode("utf-8"))
