#!/bin/bash
# Install the daily scan and the report server as launchd agents (macOS).
#
#   scan/install-launchd.sh              write the plists, print the load commands
#   scan/install-launchd.sh --load       write them and load them now
#   HOUR=7 MINUTE=30 scan/install-launchd.sh   pick the daily time (default 08:12)

set -eu

SCAN_DIR="$(cd "$(dirname "$0")" && pwd)"
REPO="$(dirname "$SCAN_DIR")"
STATE="${JOBKIT_ME:-$REPO/me}/scan"
PYTHON="$(command -v python3 || true)"
CLAUDE="$(command -v claude || true)"
HOUR="${HOUR:-8}"
MINUTE="${MINUTE:-12}"
USER_ID="$(whoami)"
DEST="$HOME/Library/LaunchAgents"

[ -n "$PYTHON" ] || { echo "python3 not found on PATH"; exit 1; }
[ -n "$CLAUDE" ] || echo "warning: claude not found on PATH. The Google step will be skipped."
[ -f "$REPO/me/search.py" ] || [ -n "${JOBKIT_ME:-}" ] || { echo "me/search.py missing. Run: cp -R templates/me me"; exit 1; }

mkdir -p "$DEST" "$STATE"
PATHS="$(dirname "$PYTHON"):$(dirname "${CLAUDE:-/usr/bin/true}"):/opt/homebrew/bin:/usr/local/bin:/usr/bin:/bin:/usr/sbin:/sbin"

for kind in job-scan job-scan-server; do
  label="com.$USER_ID.$kind"
  sed -e "s|__LABEL__|$label|g" -e "s|__REPO__|$REPO|g" -e "s|__STATE__|$STATE|g" \
      -e "s|__PYTHON__|$PYTHON|g" -e "s|__CLAUDE__|$CLAUDE|g" -e "s|__HOME__|$HOME|g" \
      -e "s|__PATH__|$PATHS|g" -e "s|__HOUR__|$HOUR|g" -e "s|__MINUTE__|$MINUTE|g" \
      "$SCAN_DIR/launchd/$kind.plist.template" > "$DEST/$label.plist"
  echo "wrote $DEST/$label.plist"
  cmd="launchctl bootout gui/$(id -u)/$label 2>/dev/null; launchctl bootstrap gui/$(id -u) $DEST/$label.plist"
  if [ "${1:-}" = "--load" ]; then
    eval "$cmd" && echo "loaded $label"
  else
    echo "  to load: $cmd"
  fi
done
