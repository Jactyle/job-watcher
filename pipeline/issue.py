"""Daily GitHub Issue: lists every new and removed posting, closes the previous day's issue.

GitHub allows 65,536 characters in an issue body or a comment. A big day does not fit in one body, so the list continues in
comments on the same issue (marked with MARK so a second run on the same day can replace them) until every posting is listed.
"""
from __future__ import annotations

import json
import re
import subprocess

LABEL = "daily-digest"
MAX_PART = 60000          # characters per issue body or comment, safely under GitHub's 65,536
MARK = "<!-- daily-digest-continued -->"
DATE_TITLE = re.compile(r"^\d{4}-\d{2}-\d{2}$")   # a digest issue is titled with its date


def _link_text(title: str) -> str:
    """Brackets in a title would end the Markdown link early."""
    return title.replace("[", "\\[").replace("]", "\\]")


def _lines(rows: list[dict]) -> list[str]:
    rows = sorted(rows, key=lambda r: (not r["in_role"], r["employer"], r["title"]))
    return [f"- {'**[in role]** ' if r['in_role'] else ''}{r['employer']}: [{_link_text(r['title'])}]({r['url']})"
            f" ({r['location'] or 'no location'})" for r in rows]


def build_parts(date: str, rows: list[dict]) -> list[str]:
    """The digest as one or more texts: the first is the issue body, the rest are continuation comments. Every posting is listed."""
    new = [r for r in rows if r["first_seen"] == date and not r["first_run"]]
    removed = [r for r in rows if r["removed_date"] == date]
    parts: list[str] = []
    cur: list[str] = [f"Job watcher digest for **{date}** (UTC).", ""]
    size = sum(len(x) + 1 for x in cur)

    def start_continuation(section: str | None) -> None:
        nonlocal cur, size
        parts.append("\n".join(cur).rstrip() + "\n")
        cur = [MARK, f"Digest for **{date}**, continued.", ""] + ([f"## {section} (continued)", ""] if section else [])
        size = sum(len(x) + 1 for x in cur)

    def add(line: str, section: str | None) -> None:
        nonlocal size
        if size + len(line) + 1 > MAX_PART:
            start_continuation(section)
        cur.append(line)
        size += len(line) + 1

    for heading, items in ((f"New postings ({len(new)})", new), (f"Removed postings ({len(removed)})", removed)):
        name = heading.split(" (")[0]
        if size + 1000 > MAX_PART:          # never leave a heading alone at the end of a part
            start_continuation(None)
        add(f"## {heading}", None); add("", None)
        lines = _lines(items)
        if not lines:
            add("None.", name)
        for line in lines:
            add(line, name)
        add("", name)
    parts.append("\n".join(cur).rstrip() + "\n")
    if len(parts) > 1:
        parts[0] += f"\n_This day is too big for one issue, so the list continues in {len(parts) - 1} comment{'s' if len(parts) > 2 else ''} below._\n"
    return parts


def build_body(date: str, rows: list[dict]) -> str:
    """The issue body: the first part of the digest."""
    return build_parts(date, rows)[0]


def _gh(*args: str) -> str:
    return subprocess.run(["gh", *args], check=True, capture_output=True, text=True).stdout


def _replace_continuations(number: int, extra: list[str]) -> None:
    """Delete the continuation comments left by an earlier run today, then post the current ones in order."""
    ids = _gh("api", "--paginate", f"repos/{{owner}}/{{repo}}/issues/{number}/comments",
              "--jq", f'.[] | select(.body | startswith("{MARK}")) | .id').split()
    for comment_id in ids:
        _gh("api", "-X", "DELETE", f"repos/{{owner}}/{{repo}}/issues/comments/{comment_id}")
    for text in extra:
        _gh("issue", "comment", str(number), "--body", text)


def publish(date: str, rows: list[dict]) -> None:
    """Create or update today's issue, close every other open digest issue, and post any continuation comments."""
    parts = build_parts(date, rows)
    body, extra = parts[0], parts[1:]
    _gh("label", "create", LABEL, "--color", "0e8a16", "--force")
    # Digest issues are found by their date title, not by label: GitHub's label-filtered listing can come back empty (it did for every
    # issue here once), and an empty answer would open a duplicate issue and leave yesterday's open. The plain listing is reliable.
    issues = [i for i in json.loads(_gh("issue", "list", "--state", "all", "--limit", "200", "--json", "number,title,state"))
              if DATE_TITLE.match(i["title"])]
    today = next((i for i in issues if i["title"] == date), None)
    number = None
    if today is None:
        created = _gh("issue", "create", "--title", date, "--body", body, "--label", LABEL)
        if extra:
            number = int(created.strip().rsplit("/", 1)[-1])
    else:
        number = today["number"]
        _gh("issue", "edit", str(number), "--body", body)
        if today["state"] == "CLOSED":
            _gh("issue", "reopen", str(number))
    for i in issues:
        if i["title"] != date and i["state"] == "OPEN":
            _gh("issue", "close", str(i["number"]), "--comment", f"Superseded by the {date} digest.")
    if number is not None:
        _replace_continuations(number, extra)
