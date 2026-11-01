# Job Watcher

[![tests](https://github.com/Jactyle/job-watcher/actions/workflows/tests.yml/badge.svg)](https://github.com/Jactyle/job-watcher/actions/workflows/tests.yml)
[![daily](https://github.com/Jactyle/job-watcher/actions/workflows/daily.yml/badge.svg)](https://github.com/Jactyle/job-watcher/actions/workflows/daily.yml)

Watches the open positions at 49 tech, video game and fintech employers for the roles **financial analyst** and **data analyst**. Every day GitHub Actions pulls each employer's job board (anonymous JSON, no HTML), records what is new and what is gone, opens a GitHub Issue with the changes, and publishes the result to GitHub Pages.

Live site: https://jactyle.github.io/job-watcher/

## Files

| File | What it does |
|---|---|
| `README.md` | This file. |
| `pipeline/sources.py` | The watch list, one fetcher per ATS, and reading/writing the compressed raw files. |
| `pipeline/normalize.py` | Converts each ATS's raw JSON into the common columns. |
| `pipeline/rules.py` | The title rule (`in_role`). |
| `pipeline/build.py` | Builds `data/history.csv` from the raw files alone and computes `data/status.json`. |
| `pipeline/issue.py` | Builds and publishes the daily GitHub Issue, closes the previous one. It lists every new and removed posting with a link; a day too big for one issue body (GitHub allows 65,536 characters) continues in comments on the same issue, which a second run on the same day replaces. |
| `pipeline/logos.py` | Downloads each employer's icon into `logos/` (`python -m pipeline.logos`). Run by hand when an employer is added; the daily run does not use it. |
| `pipeline/run.py` | One daily run: fetch all sources in parallel, save raw, build, write status, open the issue. A failed source or issue step never stops the commit. |
| `pipeline/__init__.py` | Marks `pipeline` as a Python package. |
| `tests/test_normalize.py` | Conversion of every source type to the common columns. |
| `tests/test_rules.py` | The title rule. |
| `tests/test_build.py` | First-seen, last-seen, removed and reopened logic, `first_run`, sorting, reproducible rebuild, status counts. |
| `tests/test_run.py` | A failed source is recorded and writes no raw file. |
| `tests/test_sources.py`, `tests/test_workday_split.py`, `tests/test_eightfold.py` | Fetch helpers: raw file writing, Workday 2,000-result splitting, Microsoft second pass. |
| `tests/test_issue.py` | The daily issue text: every posting is listed, a large day continues in comments and nothing is cut, and a second run on the same day updates the issue and replaces those comments. |
| `tests/test_logos.py` | Every watched employer has a logo domain and a PNG file in `logos/`. |
| `tests/test_globe_data.py` | The Globe has a place for every country `country.js` can return, the service worker only caches files that exist and lists every page, every page loads `sfx.js` before `app.js`, the nav links are the four pages, and every manifest icon exists. |
| `tests/test_country_js.py` | `country.js` run with node: country codes, US states, mixed postings, unknown locations (skipped where node is not installed). |
| `requirements.txt` | Python dependency (pytest); the pipeline itself uses only the standard library. |
| `.gitignore` | Keeps caches out of the repository. |
| `.github/workflows/daily.yml` | Runs the pipeline once a day (09:17 UTC) and commits `data/`. |
| `.github/workflows/tests.yml` | Runs pytest on every push; its badge is above. |
| `data/raw/<date>/<source>.json.gz` | What each source returned that day (descriptions removed to keep files small). A failed source writes no file. |
| `data/history.csv` | One row per posting ever seen. |
| `data/status.json` | Describes the latest run, including the result of every source. |
| `index.html` | Today page: last run, source status, the four counts, new and removed postings as tiles (every posting is in the page; long lists show their first rows until "Show all", with an All / In role switch). |
| `browse.html` | Browse page, laid out like a job board: title/company and location search, role switch, employer and days-open filters, sort, a results list with a detail pane, an apply link on every posting, a Remote quick filter, and a saved shortlist (localStorage) that keeps postings after they are removed. The search and filters are kept in the URL hash, so a search can be bookmarked or shared. Arrow keys move through the results; filters fold into a button on phones. |
| `market.html` | Market page: the six required sections plus an extra chart of open postings outside the US, all computed in the browser from the history file. |
| `globe.html`, `globe.js` | Globe page (an extra): an interactive 3D globe of the open postings by country. Drag to rotate, zoom with the buttons, a pinch or ctrl/⌘ + scroll, hover or click a bubble for the country, its top employers and a link into Browse; an All / In role switch and a ranked list sit beside it. It is drawn on a canvas with no libraries. Each bubble sits at the middle of a country, so it shows the general location only; `globe.js` holds the table of country positions. |
| `land-110m.json` | The world land outline the globe is drawn from (Natural Earth, public domain, as packaged in the `world-atlas` npm package). Kept in the repository so the globe works offline. |
| `country.js` | Reads a posting's country from its location text (the history file has no country column) for the extra Market chart, the Globe page and the Browse country filter. A posting that also lists a US location counts as US; one with no country, like Hybrid, is left out. |
| `logos/<source>.png` | The employer icons shown next to postings (the employers' own, used only to identify them). A missing one falls back to a letter tile. The Cisco and Ubisoft files were supplied by hand (their sites publish only tiny icons) and cleaned up to a transparent 256 px PNG; the download tool only replaces a logo with a larger one, so it will not overwrite them. |
| `app.js`, `app.css` | Shared navigation, data loading, fonts and colors, the screen effects (text jitter, a rolling refresh band, random glitches with a red/blue split, big numbers that scramble and then lock on, a looping background behind each terminal (a radar sweep with pulsing rings on Today, film strips advancing and a scan bar on Browse, turning lens rings and a scanning line on Market, drifting particles on Globe), a startup screen (a dead black monitor with one dim hairline, in the look of the Wallace Corporation screens: pure black and warm gold-white light; a click shoots a bright line across, opens the picture from it in a flash of light, and the page rolls and locks in; once per browser session; skipped for reduced motion, with FX off, on a deep link and in automated browsers; it waits for a click, or Enter or Space, and never switches itself on), a power-down between pages (the page collapses to a bright line at the middle of the screen, wherever you have scrolled to); the FX button in the nav bar turns them all off, and they never run for people who set reduced motion), and the "What does in role mean?" dialog (a plain-words version of the title rule below, opened from the ? buttons). The look follows the cold glass-screen interfaces in Blade Runner 2049, and each page is its own "terminal" with its own pattern, background, frame and sound set by `<html data-theme>`, while all four share one palette (the outline asks for one set of colors; a test keeps the theme blocks free of color definitions): Today is a teal-green radar screen with a diamond lattice, Browse a blue monitor with numbered records, Market a steel-blue lab screen with bracketed windows and a column of code, Globe an orange point-cloud scan with cyan beams. All four share the same navigation bar and the same two fonts. Common to all: a deep teal-green night seen through a dirty display (grain, scratches, a vignette, a bright bottom edge), a rounded HUD bezel with ruler ticks down both sides, a faint diamond lattice under the top edge, cyan hairlines and glow, cream-yellow for the values that matter, red-orange for removals and alerts, wide techno numerals and small monospace labels. Chart bars fade out downward and end in a bright cap. |
| `sfx.js` | Sound effects, made in the browser with the Web Audio API (no audio files): a brass swell and a low drone when switched on, holographic blips for clicks, a chime when a job is saved, static bursts for glitches, a sonar ping on the globe, a power-down between pages. Each page has its own ambient loop underneath (a sonar-ping drone for Today, mains hum and a film-transport whirr for Browse, a lab pad with a heartbeat for Market, a rumble and wind for Globe). On by default, and it starts at the first click or key press on each page because browsers only allow sound after a click; the speaker icon in the nav bar turns it off. |
| `fonts/share-tech-mono.woff2`, `fonts/michroma.woff2`, `fonts/OFL.txt` | The two web fonts (Share Tech Mono for labels and data, Michroma for the large numerals and titles; both SIL Open Font License) kept in the repository so they work offline. |
| `sw.js` | Service worker: network first, cached copy when offline, so the site opens offline and shows the last data it loaded. |
| `manifest.webmanifest` | Web app manifest: name, start page and icons, so the browser can install the site as an app. |
| `icon-maskable-192.png`, `icon-maskable-512.png` | The same icon with extra margin, for Android and other launchers that crop app icons to a circle or rounded square (the manifest marks them `maskable`). |
| `icon-192.png`, `icon-512.png` | The app icon (three glowing bars with bright caps inside the rounded HUD bezel) at the two sizes the manifest names. |
| `.nojekyll` | Tells GitHub Pages to serve the files as they are. |

## Sources

| Source | Employer | ATS |
|---|---|---|
| robinhood, coinbase, stripe, affirm, brex, mercury, chime, carta, toast, sofi, gusto, betterment, databricks, airbnb, cloudflare | Robinhood, Coinbase, Stripe, Affirm, Brex, Mercury, Chime, Carta, Toast, SoFi, Gusto, Betterment, Databricks, Airbnb, Cloudflare | Greenhouse (`boards-api.greenhouse.io`) |
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

Electronic Arts and Valve (Steam) have no job board the tool can read as JSON without a login (Valve's jobs page is HTML only), so they are not watched. Microsoft's API serves 10 postings per page and throttles with HTTP 429, so its fetch is slow (about 7 minutes), retries after each 429, and waits out a brief HTTP 403 block (12 waits of 15 seconds per crawl, then it fails) instead of abandoning the crawl at once. **Search term:** Apple (6,303 postings) and Amazon (over 5,000) return more than 5,000 postings, so both are requested with the search term **analyst**, set in `SEARCH_TERMS` in `pipeline/sources.py`. Every other board is read in full, and every posting a board returns is kept, not only ones in role. Workday serves at most 2,000 results per query, so a capped Workday board (NVIDIA, Capital One) is re-queried once per job family, then worker type and location, until every posting is collected. Workday gives only relative dates ("Posted 3 Days Ago"), so `posted_date` is empty for those rows, as is `department` for Greenhouse and Workday. For a Workday posting in several places the list only says "2 Locations", so `location` holds the first location, read from the posting's URL slug (for example `McLean, VA`, or `US, CA, Santa Clara` written the way NVIDIA writes it). Placeholder `BLANK` parts of a location are dropped.

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
- A second run on the same UTC day deletes that day's raw files, fetches again, rebuilds, and updates that day's issue (replacing its continuation comments), so each day counts once.
