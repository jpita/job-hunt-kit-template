# Daily job scan: instructions for the agent

Run this once a day. Paths are relative to the repo root.
All state and output is in `me/scan/`.

1. Use the connected Chrome session (Claude in Chrome). Do not use a generic web search or background HTTP requests for Google.
2. Run `python3 scan/queries.py`. Inject its output into the Google tab, then inject `scan/harvest-google.js`.
3. For each URL in `window._queries()`: navigate to it, run `window._page()`, follow the real **Next** link. Wait about 10 seconds between navigations. Read at most five result pages per query.
4. If Google shows `/sorry/` or "unusual traffic", stop the browser part at once. Do not retry. Run `python3 scan/runlog.py google --blocked`, then `python3 scan/report.py`, and report the block.
5. Save `window._all().jobs` as `me/scan/harvest-YYYY-MM-DD.json`, with today's date in the `TIMEZONE` from `me/search.py`. Shape: `{"jobs":["https://..."]}`.
6. Run `python3 scan/runlog.py google --ok --found N`. N is the number of URLs.
7. Run `python3 scan/google_scan.py me/scan/harvest-YYYY-MM-DD.json`.
8. Run `python3 scan/report.py`.
9. Check that `me/scan/report.html` shows today's date and the health strip reads "Both scans are current". If not, say which source is stale.
10. Summarize only new jobs in **Clean** or **Worth a glance**. If there are none, say so. Report any block or failed step.
11. Do not open the report. The wrapper opens it after you exit.

The wrapper already ran `discover.py` and `scan.py --slice`. Do not run them.
