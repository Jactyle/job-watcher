"""One daily run: fetch every source, build history, write status, open the issue.

    python -m pipeline.run [--no-issue]
The workflow commits the changed files afterwards.
"""
from __future__ import annotations

import shutil
import sys
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
from pathlib import Path

from . import build, issue
from .normalize import convert
from .sources import SOURCES, fetch, write_raw


def run_source(src: dict, day_dir: Path, fetcher=fetch) -> dict:
    """Fetch one source and save its raw file. A failure writes no file and is reported, never raised."""
    try:
        payload = fetcher(src)
        count = len(convert(payload, src))
        write_raw(day_dir / f"{src['name']}.json.gz", payload)
        return {"name": src["name"], "ok": True, "count": count}
    except Exception as exc:  # noqa: BLE001 - one source failing must not stop the run
        print(f"FAILED {src['name']}: {exc}", file=sys.stderr, flush=True)
        return {"name": src["name"], "ok": False, "count": 0}


def run_sources(sources: list[dict], day_dir: Path, fetcher=fetch) -> list[dict]:
    """Fetch all sources in parallel (they are different hosts); results keep the watch-list order."""
    with ThreadPoolExecutor(max_workers=6) as pool:
        results = list(pool.map(lambda s: run_source(s, day_dir, fetcher), sources))
    for r in results:
        print(r, flush=True)
    return results


def main(argv: list[str]) -> int:
    now = datetime.now(timezone.utc)
    date = now.strftime("%Y-%m-%d")
    day_dir = build.RAW / date
    if day_dir.exists():  # a second run on the same day replaces that day's raw files
        shutil.rmtree(day_dir)

    results = run_sources(SOURCES, day_dir)
    rows = build.build_history()
    build.write_history(rows)
    build.write_status(build.compute_status(rows, now.strftime("%Y-%m-%dT%H:%M:%SZ"), results))
    if "--no-issue" not in argv:
        try:
            issue.publish(date, rows)
        except Exception as exc:  # noqa: BLE001 - the data must still be committed
            print(f"ISSUE FAILED: {exc}", file=sys.stderr, flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
