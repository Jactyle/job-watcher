# Job Watcher

[![tests](https://github.com/Jactyle/job-watcher/actions/workflows/tests.yml/badge.svg)](https://github.com/Jactyle/job-watcher/actions/workflows/tests.yml)
[![daily](https://github.com/Jactyle/job-watcher/actions/workflows/daily.yml/badge.svg)](https://github.com/Jactyle/job-watcher/actions/workflows/daily.yml)

Watches the open positions at 49 tech, video game and fintech employers for the roles **financial analyst** and **data analyst**. Every day GitHub Actions pulls each employer's job board (anonymous JSON, no HTML), records what is new and what is gone, opens a GitHub Issue with the changes, and publishes the result to GitHub Pages.

Live site: https://jactyle.github.io/job-watcher/

## Files

| File | What it does |
|---|---|
| `pipeline/sources.py` | The watch list, one fetcher per ATS, and reading/writing the compressed raw files. |
| `pipeline/normalize.py` | Converts each ATS's raw JSON into the common columns. |
| `pipeline/rules.py` | The title rule (`in_role`). |
| `pipeline/build.py` | Builds `data/history.csv` from the raw files alone and computes `data/status.json`. |
| `pipeline/issue.py` | Builds and publishes the daily GitHub Issue, closes the previous one. |
| `pipeline/run.py` | One daily run: fetch all sources in parallel, save raw, build, write status, open the issue. A failed source or issue step never stops the commit. |
| `tests/` | pytest suite: source conversion, title rule, first-seen/last-seen/removed logic, issue text. |
| `.github/workflows/daily.yml` | Runs the pipeline once a day (09:17 UTC) and commits `data/`. |
| `.github/workflows/tests.yml` | Runs pytest on every push; its badge is above. |
| `data/raw/<date>/<source>.json.gz` | What each source returned that day (descriptions removed to keep files small). A failed source writes no file. |
| `data/history.csv` | One row per posting ever seen. |
| `data/status.json` | Describes the latest run, including the result of every source. |
| `index.html` | Today page: last run, source status, the four counts, new and removed postings. |
| `browse.html` | Browse page: open postings with role switch, filters, title search, sort, apply links, starred shortlist (localStorage). |
| `market.html` | Market page: six sections computed in the browser from the history file. |
| `app.js`, `app.css` | Shared navigation, data loading, fonts and colors. |
| `sw.js`, `manifest.webmanifest`, `icon-*.png` | Make the site installable and usable offline (network first, cached data when offline). |
| `.nojekyll` | Tells GitHub Pages to serve the files as they are. |

## Sources

| Source | Employer | ATS |
|---|---|---|
| robinhood, coinbase, stripe, affirm, brex, mercury, chime, carta, toast, sofi, gusto, betterment, databricks, airbnb, cloudflare | same names | Greenhouse (`boards-api.greenhouse.io`) |
| epicgames, riotgames, roblox, discord, taketwo, rockstargames, bungie, scopely, twitch | Epic Games, Riot Games, Roblox, Discord, Take-Two Interactive, Rockstar Games, Bungie, Scopely, Twitch | Greenhouse |
| palantir, spotify | Palantir, Spotify | Lever (`api.lever.co`) |
| ramp, notion, openai, supercell | Ramp, Notion, OpenAI, Supercell | Ashby (`api.ashbyhq.com`) |
| servicenow, ubisoft | ServiceNow, Ubisoft | SmartRecruiters (`api.smartrecruiters.com`) |
| microsoft | Microsoft (includes Xbox, Activision, Blizzard) | Eightfold (`apply.careers.microsoft.com/api/pcsx/search`) |
| netflix | Netflix | Eightfold apply API (`explore.jobs.netflix.net/api/apply/v2/jobs`) |
| amd | AMD | Jibe (`careers.amd.com/api/jobs`) |
| apple | Apple | Apple's own search API (`jobs.apple.com/api/v1/search`) |
| amazon | Amazon | amazon.jobs search API (`amazon.jobs/en/search.json`) |
| fidelity, mastercard, capitalone, nvidia, sony, intel, samsung, adobe, cisco, salesforce, snap, hp | Fidelity Investments, Mastercard, Capital One, NVIDIA, Sony, Intel, Samsung, Adobe, Cisco, Salesforce, Snap, HP | Workday (`/wday/cxs/.../jobs`) |

Electronic Arts and Valve (Steam) have no job board the tool can read as JSON without a login (Valve's jobs page is HTML only), so they are not watched. Microsoft's API serves 10 postings per page and throttles with HTTP 429, so its fetch is slow (about 7 minutes) and retries after each 429. **Search term:** Apple (6,303 postings) and Amazon (over 5,000) return more than 5,000 postings, so both are requested with the search term **analyst**, set in `SEARCH_TERMS` in `pipeline/sources.py`. Every other board is read in full, and every posting a board returns is kept, not only ones in role. Workday serves at most 2,000 results per query, so a capped Workday board (NVIDIA, Capital One) is re-queried once per job family, then worker type and location, until every posting is collected. Workday gives only relative dates ("Posted 3 Days Ago"), so `posted_date` is empty for those rows, as is `department` for Greenhouse and Workday.

## Title rule

A title is **in role** when it contains the word *analyst*, plus a finance word (financ*, FP&A, accounting, treasury, credit, investment, revenue, pricing, budget*, forecast*, controller, audit*, equity, portfolio, valuation, capital markets, corporate development, business planning) or a data word (data but not data center, analytics, business intelligence, BI, insight(s), reporting, quantitative, product, game, gameplay, player), and does not contain *intern*, *sales*, *recruit*, *support*, or *engineer*. Matching ignores case. See `pipeline/rules.py`.

## Build the history from the raw files

```
python -m pipeline.build
```

This rewrites `data/history.csv` using only `data/raw/`; running it again produces the same file. `python -m pipeline.run` does a full daily run (add `--no-issue` to skip GitHub), and `python -m pytest` runs the tests.

## Rules for the history

- A posting seen for the first time gets that day as `first_seen`; every posting a source lists that day gets `last_seen` set to that day.
- An open posting is `removed` (with that day's date) when its source has a raw file that day and no longer lists it. A source with no raw file that day (it failed) changes nothing.
- A removed posting that is listed again becomes `open` with `removed_date` cleared and `first_seen` unchanged.
- `first_run` is true for postings listed in the first raw file of their source.
- A second run on the same UTC day deletes that day's raw files, fetches again, rebuilds, and updates that day's issue, so each day counts once.
