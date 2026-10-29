"""Convert each source's raw JSON into the common columns."""
from __future__ import annotations

import re
from datetime import datetime, timezone

from .rules import in_role

COLUMNS = [
    "posting_id", "source", "source_id", "employer", "title", "location", "department",
    "posted_date", "url", "in_role", "first_run", "first_seen", "last_seen", "status",
    "removed_date",
]


def _clean(value) -> str:
    if value is None:
        return ""
    return " ".join(str(value).split())


def _date_from_iso(value) -> str:
    """'2026-08-19T12:29:00-04:00' -> '2026-08-19' (the date as written, in UTC when it has an offset)."""
    if not value:
        return ""
    text = re.sub(r"([+-]\d{2})(\d{2})$", r"\1:\2", str(value).replace("Z", "+00:00"))  # "+0000" -> "+00:00"
    try:
        dt = datetime.fromisoformat(text)
    except ValueError:
        return ""
    if dt.tzinfo is not None:
        dt = dt.astimezone(timezone.utc)
    return dt.strftime("%Y-%m-%d")


def _date_from_ms(value) -> str:
    if not value:
        return ""
    return datetime.fromtimestamp(int(value) / 1000, tz=timezone.utc).strftime("%Y-%m-%d")


def _row(src: dict, source_id, title, location, department, posted_date, url) -> dict:
    source_id = _clean(source_id)
    title = _clean(title)
    return {
        "posting_id": f"{src['name']}:{source_id}",
        "source": src["name"],
        "source_id": source_id,
        "employer": src["employer"],
        "title": title,
        "location": _clean(location),
        "department": _clean(department),
        "posted_date": posted_date,
        "url": _clean(url),
        "in_role": in_role(title),
    }


def greenhouse(raw: dict, src: dict) -> list[dict]:
    rows = []
    for j in raw.get("jobs", []):
        rows.append(_row(
            src, j["id"], j.get("title"), (j.get("location") or {}).get("name"), "",
            _date_from_iso(j.get("first_published")), j.get("absolute_url"),
        ))
    return rows


def lever(raw: list, src: dict) -> list[dict]:
    rows = []
    for j in raw:
        cats = j.get("categories") or {}
        rows.append(_row(
            src, j["id"], j.get("text"), cats.get("location"),
            cats.get("department") or cats.get("team"),
            _date_from_ms(j.get("createdAt")), j.get("hostedUrl"),
        ))
    return rows


def ashby(raw: dict, src: dict) -> list[dict]:
    rows = []
    for j in raw.get("jobs", []):
        if j.get("isListed") is False:
            continue
        rows.append(_row(
            src, j["id"], j.get("title"), j.get("location"), j.get("department"),
            _date_from_iso(j.get("publishedAt")), j.get("jobUrl"),
        ))
    return rows


def smartrecruiters(raw: dict, src: dict) -> list[dict]:
    rows = []
    for j in raw.get("content", []):
        loc = j.get("location") or {}
        location = loc.get("fullLocation") or ", ".join(
            p for p in (loc.get("city"), loc.get("region"), loc.get("country")) if p
        )
        rows.append(_row(
            src, j["id"], j.get("name"), location, (j.get("department") or {}).get("label"),
            _date_from_iso(j.get("releasedDate")),
            f"https://jobs.smartrecruiters.com/{src['board']}/{j['id']}",
        ))
    return rows


def workday(raw: dict, src: dict) -> list[dict]:
    rows = []
    for j in raw.get("jobPostings", []):
        path = j.get("externalPath") or ""
        bullets = j.get("bulletFields") or []
        source_id = bullets[0] if bullets else path.rsplit("_", 1)[-1]
        # postedOn is relative text ("Posted 3 Days Ago"), so posted_date stays empty.
        rows.append(_row(
            src, source_id, j.get("title"), j.get("locationsText"), "", "",
            f"https://{src['host']}/{src['site']}{path}",
        ))
    return rows


def eightfold(raw: dict, src: dict) -> list[dict]:
    rows = []
    for j in raw.get("positions", []):
        locs = j.get("standardizedLocations") or j.get("locations") or []
        rows.append(_row(
            src, j["id"], j.get("name"), "; ".join(locs[:3]), j.get("department"),
            _date_from_ms(int(j["postedTs"]) * 1000) if j.get("postedTs") else "",
            f"https://{src['host']}{j.get('positionUrl') or ''}",
        ))
    return rows


def jibe(raw: dict, src: dict) -> list[dict]:
    rows = []
    for item in raw.get("jobs", []):
        j = item.get("data", item)
        cats = j.get("categories") or []
        rows.append(_row(
            src, j.get("req_id") or j.get("slug"), j.get("title"),
            j.get("full_location") or j.get("location_name"),
            (cats[0].get("name") if cats and isinstance(cats[0], dict) else j.get("department")),
            _date_from_iso(j.get("posted_date")),
            f"https://{src['host']}/careers-home/jobs/{j.get('slug') or j.get('req_id')}",
        ))
    return rows


CONVERTERS = {
    "greenhouse": greenhouse,
    "lever": lever,
    "ashby": ashby,
    "smartrecruiters": smartrecruiters,
    "workday": workday,
    "eightfold": eightfold,
    "jibe": jibe,
}


def convert(raw, src: dict) -> list[dict]:
    """Convert one source's raw payload; duplicate IDs inside one payload keep the first."""
    seen, rows = set(), []
    for row in CONVERTERS[src["ats"]](raw, src):
        if row["source_id"] and row["posting_id"] not in seen:
            seen.add(row["posting_id"])
            rows.append(row)
    return rows
