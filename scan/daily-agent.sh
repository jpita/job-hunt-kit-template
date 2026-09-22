#!/bin/bash
# The daily run. launchd starts it once a day (see install-launchd.sh).
# Run it by hand the same way:  scan/daily-agent.sh

set -u

SCAN_DIR="$(cd "$(dirname "$0")" && pwd)"
REPO="$(dirname "$SCAN_DIR")"
ME="${JOBKIT_ME:-$REPO/me}"
STATE="$ME/scan"
REPORT="$STATE/report.html"
CLAUDE_BIN="${CLAUDE_BIN:-$(command -v claude)}"
PY="${PYTHON:-$(command -v python3)}"

mkdir -p "$STATE"
PORT=$("$PY" -c "import sys; sys.path.insert(0, '$SCAN_DIR'); import config; print(config.PORT)") || exit 1

# The served page can save your marks and refreshes itself when a scan
# finishes. The file cannot, so it is only the fallback for a server that is down.
open_report() {
  if /usr/bin/curl -sf -m 5 -o /dev/null "http://127.0.0.1:$PORT/version"; then
    /usr/bin/open "http://127.0.0.1:$PORT/" >/dev/null 2>&1 || true
  else
    /usr/bin/open "$REPORT" >/dev/null 2>&1 || true
  fi
}

# Opening the report is always the final action, even when a step failed.
trap open_report EXIT

cd "$SCAN_DIR" || exit 1

# Find boards that are not on the list yet. It needs no browser.
# A failure here must not stop the scan.
"$PY" discover.py >>"$STATE/discover.log" 2>&1 || echo "discover.py failed, continuing" >>"$STATE/discover.log"

# The boards run next, without a browser. A seventh of the boards each day
# gives every board a weekly refresh, and a Google block costs the Google half only.
"$PY" scan.py --slice >>"$STATE/board-slice.log" 2>>"$STATE/board-slice.err.log"

AUTOMATION_PROMPT="Run the unattended daily job scan. Read and follow $SCAN_DIR/DAILY-AUTOMATION.md exactly. Use the connected Chrome session for Google and do all harvesting, validation, Python processing, and report verification yourself. Board discovery and the board rotation have already run, so do not run discover.py or scan.py. The wrapper opens the report after you exit, so do not open it. Finish with a concise summary of new viable jobs or state that there were none."

if [ -z "$CLAUDE_BIN" ]; then
  echo "claude not found on PATH, skipping the Google step" >&2
  STATUS=1
else
  /usr/bin/caffeinate -i "$CLAUDE_BIN" \
    --print \
    --chrome \
    --no-session-persistence \
    --dangerously-skip-permissions \
    "$AUTOMATION_PROMPT"
  STATUS=$?
fi

# Rebuild the report whatever the browser did, so the board results show
# even when Google was blocked.
"$PY" report.py >>"$STATE/report-refresh.log" 2>&1

# Notify only when there is something to say.
"$PY" notify.py >>"$STATE/notify.log" 2>&1

exit $STATUS
