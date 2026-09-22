# Job scan

Finds remote jobs that fit you, every day, and shows them on one page.

## What it does

- Reads the public job boards (Ashby, Greenhouse, Lever) of about 900 companies.
- Reads a seventh of the boards each day, so each board refreshes weekly.
- Finds new boards through GitHub code search (`discover.py`, needs `gh` logged in).
- Searches Google for more job pages, through your Chrome, driven by Claude.
- Sorts every job into lists: Clean, Worth a glance, One level down, Wrong kind of role, Wrong country.
- Never deletes a job. It only moves it between lists.
- Sends a macOS notification only when there is a new job worth reading, or a scan failed.

## Requirements

- macOS.
- Python 3 (standard library only).
- Claude Code, with the Claude in Chrome extension connected. Only the Google step needs it.
- Optional: `gh` CLI, logged in, for board discovery.

## Set up

1. `cp -R templates/me me` at the repo root, if `me/` does not exist.
2. Edit `me/search.py`. Each key has a comment. Set your role, level, places and queries.
3. Try it: `python3 scan/scan.py --slice`, then `python3 scan/report.py`.
4. Open `me/scan/report.html`.

## Daily schedule

- `scan/install-launchd.sh` writes two launchd agents and prints the load commands.
- `scan/install-launchd.sh --load` also loads them.
- `HOUR=7 MINUTE=30 scan/install-launchd.sh` sets the daily time. Default is 08:12.
- The daily agent runs `scan/daily-agent.sh`. The server keeps the report live on `http://127.0.0.1:<PORT>`.

## Manual commands

| Command | Does |
|---|---|
| `python3 scan/scan.py --slice` | Read today's seventh of the boards |
| `python3 scan/scan.py` | Read every board (slow) |
| `python3 scan/discover.py` | Add new boards to `me/scan/companies.txt` |
| `python3 scan/report.py` | Rebuild the report |
| `python3 scan/serve.py` | Serve the report, so your marks save |
| `python3 scan/rejudge.py --dry` | Show what a change to `me/search.py` moves |
| `python3 scan/rejudge.py` | Apply it |
| `python3 scan/notify.py --dry` | Show what the notification would say |

## Where output lands

- Everything is in `me/scan/`: seen jobs, your marks, logs, `report.html`.
- `me/` is gitignored. Nothing personal goes into git.

## Tune the search

- Too many wrong jobs in Clean: tighten `TARGET_TITLE` or add words to `EXCLUDE_TITLES`.
- Good jobs in "Wrong kind of role": widen `ROLE_GATE`.
- Good jobs in "Wrong country": add the place to `HOME_PLACES` or its code to `HOME_COUNTRY_CODES`.
- After each change, run `python3 scan/rejudge.py --dry`, then `python3 scan/rejudge.py`.
- In the report, "wrong list" reports go to `me/scan/rule-reports.json`. Ask Claude to read them and fix `me/search.py`.
