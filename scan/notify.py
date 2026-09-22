#!/usr/bin/env python3
"""Tell the user when there is something to say, and stay quiet otherwise.

Two things are worth a notification: a job you have not seen that is actually
worth reading, and a scan that failed. A daily "nothing happened" trains you
to ignore the thing.

  python3 notify.py           notify if there is news
  python3 notify.py --dry     print what it would say
  python3 notify.py --force   notify even with no news, to test the plumbing

State lives in notified.json, so the same job is never announced twice.
"""
import argparse, json, pathlib, subprocess, sys

import config

import report
import runlog

HERE = config.STATE
STATE = HERE / "notified.json"
PORT = config.PORT
# Only these two buckets are worth interrupting you for.
WORTH = ("clean", "check")


def already():
    if not STATE.exists():
        return set()
    try:
        return set(json.loads(STATE.read_text()))
    except (json.JSONDecodeError, OSError):
        return set()


def remember(urls):
    STATE.write_text(json.dumps(sorted(urls), indent=1))


def failures():
    """Which sources did not complete, in words."""
    out = []
    for kind, label in (("boards", "board scan"), ("google", "Google scan")):
        ok = runlog.last(kind, ok_only=True)
        any_run = runlog.last(kind, ok_only=False)
        if any_run and not any_run.get("ok") and (
                not ok or any_run["when"] > ok["when"]):
            out.append(f'{label}: {any_run.get("why") or "did not finish"}')
    return out


# The text is passed as arguments, never pasted into the script. AppleScript
# has no \\uXXXX escape, so json.dumps of a middle dot produced a script
# osascript refused, and the one notification that had something to say was
# lost.
SCRIPT = ('on run argv\n'
          '  display notification (item 2 of argv) '
          'with title (item 1 of argv) sound name "Submarine"\n'
          'end run')


def notify(title, body):
    """macOS notification. osascript is on every Mac; nothing to install."""
    try:
        r = subprocess.run(["/usr/bin/osascript", "-e", SCRIPT, title, body],
                           capture_output=True, text=True, timeout=15)
        if r.returncode:
            print(f"  ! osascript said: {r.stderr.strip()[:200]}",
                  file=sys.stderr)
            return False
        return True
    except (subprocess.SubprocessError, OSError) as e:
        print(f"  ! could not notify: {e}", file=sys.stderr)
        return False


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry", action="store_true")
    ap.add_argument("--force", action="store_true")
    a = ap.parse_args()

    rows = report.load()
    seen = already()
    fresh = [r for r in rows
             if r["bucket"] in WORTH and r["url"] not in seen
             and not r.get("state")]
    broke = failures()

    lines = []
    if fresh:
        lead = fresh[:3]
        lines.append(", ".join(f'{r["title"][:38]} at {r["company"]}'
                               for r in lead))
        if len(fresh) > len(lead):
            lines.append(f"and {len(fresh) - len(lead)} more")
    if broke:
        lines += broke

    if not lines and not a.force:
        print("  nothing to say")
        return

    n = len(fresh)
    title = (f'{n} job{"s" if n != 1 else ""} worth reading' if n
             else "Job scan did not finish")
    body = " · ".join(lines) or "no news"
    print(f"  {title}\n  {body}")

    if a.dry:
        print("  --dry, nothing sent")
        return
    if notify(title, body):
        remember(seen | {r["url"] for r in fresh})


if __name__ == "__main__":
    main()
