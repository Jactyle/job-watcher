"""The watch list and the fetchers. Every request is anonymous and returns JSON."""
from __future__ import annotations

import gzip
import json
import time
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
    {"name": "servicenow", "employer": "ServiceNow", "ats": "smartrecruiters", "board": "ServiceNow"},
    _wd("fidelity", "Fidelity Investments", "fmr.wd1.myworkdayjobs.com", "fmr", "FidelityCareers"),
    _wd("mastercard", "Mastercard", "mastercard.wd1.myworkdayjobs.com", "mastercard", "CorporateCareers"),
    _wd("capitalone", "Capital One", "capitalone.wd12.myworkdayjobs.com", "capitalone", "Capital_One"),
    _wd("nvidia", "NVIDIA", "nvidia.wd5.myworkdayjobs.com", "nvidia", "NVIDIAExternalCareerSite"),
]

# A board with more than 5,000 postings must be requested with a search term (none is today).
SEARCH_TERMS: dict[str, str] = {}

# Large free-text fields that are not needed; dropped so the committed raw files stay small.
DROP_KEYS = {"descriptionHtml", "descriptionPlain", "description", "descriptionBody",
             "descriptionBodyPlain", "additional", "additionalPlain", "lists", "opening",
             "openingPlain"}


def _request(url, data=None, retries=3):
    headers = {"User-Agent": UA, "Accept": "application/json"}
    if data is not None:
        headers["Content-Type"] = "application/json"
        data = json.dumps(data).encode()
    last = None
    for attempt in range(retries):
        try:
            req = urllib.request.Request(url, data=data, headers=headers)
            with urllib.request.urlopen(req, timeout=TIMEOUT) as resp:
                return json.loads(resp.read().decode("utf-8"))
        except Exception as exc:  # noqa: BLE001 - retried, then re-raised
            last = exc
            time.sleep(2 * (attempt + 1))
    raise last


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
            if item["externalPath"] not in seen:
                seen.add(item["externalPath"])
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


FETCHERS = {
    "greenhouse": fetch_greenhouse,
    "lever": fetch_lever,
    "ashby": fetch_ashby,
    "smartrecruiters": fetch_smartrecruiters,
    "workday": fetch_workday,
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
