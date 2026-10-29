"""One daily run: fetch every source, build history, write status, open the issue.

    python -m pipeline.run [--no-issue]
The workflow commits the changed files afterwards.
"""
from __future__ import annotations

import shutil
import sys
from datetime import datetime, timezone

from . import build, issue
from .sources import SOURCES, fetch, write_raw
from .normalize import convert


def main(argv: list[str]) -> int:
    now = datetime.now(timezone.utc)
    date = now.strftime("%Y-%m-%d")
    day_dir = build.RAW / date
    if day_dir.exists():  # a second run on the same day replaces that day's raw files
        shutil.rmtree(day_dir)

    results = []
    for src in SOURCES:
        try:
            payload = fetch(src)
            count = len(convert(payload, src))
            write_raw(day_dir / f"{src['name']}.json.gz", payload)
            results.append({"name": src["name"], "ok": True, "count": count})
        except Exception as exc:  # noqa: BLE001 - one source failing must not stop the run
            print(f"FAILED {src['name']}: {exc}", file=sys.stderr)
            results.append({"name": src["name"], "ok": False, "count": 0})
        print(results[-1])

    rows = build.build_history()
    build.write_history(rows)
    build.write_status(build.compute_status(rows, now.strftime("%Y-%m-%dT%H:%M:%SZ"), results))
    if "--no-issue" not in argv:
        issue.publish(date, rows)
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
