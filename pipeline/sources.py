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
    {"name": "microsoft", "employer": "Microsoft", "ats": "eightfold", "host": "apply.careers.microsoft.com",
     "domain": "microsoft.com", "board": "microsoft"},
    {"name": "amd", "employer": "AMD", "ats": "jibe", "host": "careers.amd.com", "board": "amd"},
    {"name": "servicenow", "employer": "ServiceNow", "ats": "smartrecruiters", "board": "ServiceNow"},
    _wd("fidelity", "Fidelity Investments", "fmr.wd1.myworkdayjobs.com", "fmr", "FidelityCareers"),
    _wd("mastercard", "Mastercard", "mastercard.wd1.myworkdayjobs.com", "mastercard", "CorporateCareers"),
    _wd("capitalone", "Capital One", "capitalone.wd12.myworkdayjobs.com", "capitalone", "Capital_One"),
    _wd("sony", "Sony", "sonyglobal.wd1.myworkdayjobs.com", "sonyglobal", "SonyGlobalCareers"),
    _wd("intel", "Intel", "intel.wd1.myworkdayjobs.com", "intel", "External"),
    _wd("nvidia", "NVIDIA", "nvidia.wd5.myworkdayjobs.com", "nvidia", "NVIDIAExternalCareerSite"),
]

# A board with more than 5,000 postings must be requested with a search term (none is today).
SEARCH_TERMS: dict[str, str] = {}

# Large free-text fields that are not needed; dropped so the committed raw files stay small.
DROP_KEYS = {"descriptionHtml", "descriptionPlain", "description", "descriptionBody",
             "descriptionBodyPlain", "additional", "additionalPlain", "lists", "opening",
             "openingPlain", "responsibilities", "qualifications"}


def _request(url, data=None, retries=3, backoff=2):
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
            time.sleep(backoff * (attempt + 1))
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


def _throttled(url, attempts=60, wait=1.5):
    """GET that waits a short, fixed time after each 429 (Eightfold throttles in short bursts)."""
    for _ in range(attempts):
        try:
            return _request(url, retries=1)
        except urllib.error.HTTPError as exc:
            if exc.code != 429:
                raise
            time.sleep(wait)
    raise RuntimeError(f"still throttled after {attempts} attempts: {url}")


def fetch_eightfold(src):
    """Eightfold career sites (Microsoft): 10 positions per page."""
    positions, start, total = [], 0, None
    while total is None or start < total:
        page = _throttled(f"https://{src['host']}/api/pcsx/search?domain={src['domain']}&query=&start={start}")["data"]
        total = page["count"]
        if not page["positions"]:
            break
        positions.extend(page["positions"])
        start += len(page["positions"])
    return {"count": total, "positions": positions}


def fetch_jibe(src):
    """Jibe career sites (AMD): 100 jobs per page; the facet counts in the reply are not kept."""
    jobs, page_no, total = [], 1, None
    while total is None or len(jobs) < total:
        page = _request(f"https://{src['host']}/api/jobs?limit=100&page={page_no}")
        total = page["totalCount"]
        if not page["jobs"]:
            break
        jobs.extend(page["jobs"])
        page_no += 1
    return {"totalCount": total, "jobs": jobs}


FETCHERS = {
    "greenhouse": fetch_greenhouse,
    "lever": fetch_lever,
    "ashby": fetch_ashby,
    "smartrecruiters": fetch_smartrecruiters,
    "workday": fetch_workday,
    "eightfold": fetch_eightfold,
    "jibe": fetch_jibe,
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
