"""Daily GitHub Issue: lists new and removed postings, closes the previous day's issue."""
from __future__ import annotations

import json
import subprocess

LABEL = "daily-digest"
MAX_BODY = 60000


def _link_text(title: str) -> str:
    """Brackets in a title would end the Markdown link early."""
    return title.replace("[", "\\[").replace("]", "\\]")


def _lines(rows: list[dict]) -> list[str]:
    rows = sorted(rows, key=lambda r: (not r["in_role"], r["employer"], r["title"]))
    return [f"- {'**[in role]** ' if r['in_role'] else ''}{r['employer']}: [{_link_text(r['title'])}]({r['url']})"
            f" ({r['location'] or 'no location'})" for r in rows]


def build_body(date: str, rows: list[dict]) -> str:
    new = [r for r in rows if r["first_seen"] == date and not r["first_run"]]
    removed = [r for r in rows if r["removed_date"] == date]
    parts = [f"Job watcher digest for **{date}** (UTC).", ""]
    for heading, items in ((f"New postings ({len(new)})", new), (f"Removed postings ({len(removed)})", removed)):
        parts += [f"## {heading}", ""]
        lines = _lines(items)
        if not lines:
            parts.append("None.")
        budget = MAX_BODY - len("\n".join(parts)) - 2000
        used = 0
        for i, line in enumerate(lines):
            used += len(line) + 1
            if used > budget // 2:
                parts.append(f"…and {len(lines) - i} more (see data/history.csv).")
                break
            parts.append(line)
        parts.append("")
    return "\n".join(parts)


def _gh(*args: str) -> str:
    return subprocess.run(["gh", *args], check=True, capture_output=True, text=True).stdout


def publish(date: str, rows: list[dict]) -> None:
    """Create or update today's issue and close every other open digest issue."""
    body = build_body(date, rows)
    _gh("label", "create", LABEL, "--color", "0e8a16", "--force")
    issues = json.loads(_gh("issue", "list", "--label", LABEL, "--state", "all", "--limit", "200",
                            "--json", "number,title,state"))
    today = next((i for i in issues if i["title"] == date), None)
    if today is None:
        _gh("issue", "create", "--title", date, "--body", body, "--label", LABEL)
    else:
        _gh("issue", "edit", str(today["number"]), "--body", body)
        if today["state"] == "CLOSED":
            _gh("issue", "reopen", str(today["number"]))
    for i in issues:
        if i["title"] != date and i["state"] == "OPEN":
            _gh("issue", "close", str(i["number"]), "--comment", f"Superseded by the {date} digest.")
