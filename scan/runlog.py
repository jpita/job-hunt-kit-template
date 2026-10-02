#!/usr/bin/env python3
"""One record per scan, so the report can say how fresh its data is.

A regenerated report.html proves only that report.py ran. It says nothing
about whether Google answered or whether the boards were reachable. This file
is what the banner reads.

The scanners call record() themselves. The daily agent uses the CLI for the
step no Python sees, the browser harvest:

  python3 runlog.py google --blocked          Google served /sorry/
  python3 runlog.py google --ok --found 140   the harvest finished
  python3 runlog.py google --failed           it broke for another reason
  python3 runlog.py show                      the last run of each kind
"""
import datetime, fcntl, json, os, pathlib, sys, tempfile

import config
import storage

F = config.STATE / "runs.json"
LOCK = F.with_name(".runs.lock")
# "rejudge" re-runs the rules over cached text. It refreshes no search,
# so the health banner ignores it, but it belongs in the history.
KINDS = ("discovery", "boards", "google", "report", "rejudge")
# 400 runs is over a year of daily scans of all three kinds.
KEEP = 400


def now():
    """Local time with its offset, so a record is never ambiguous."""
    return datetime.datetime.now().astimezone().replace(microsecond=0).isoformat()


def load():
    if not F.exists():
        return []
    try:
        return json.loads(F.read_text())
    except (json.JSONDecodeError, OSError):
        return []


def record(kind, ok, **counts):
    """Append one run without losing simultaneous scanner or report writes."""
    try:
        with LOCK.open("a+") as lock:
            fcntl.flock(lock, fcntl.LOCK_EX)
            runs = load()
            runs.append(dict(kind=kind, ok=bool(ok), when=now(), **counts))
            storage.write_json(F, runs[-KEEP:], indent=1)
    except OSError as e:
        print(f"  ! could not write {F.name}: {e}", file=sys.stderr)


def last(kind, ok_only=True, completed_only=False):
    """The most recent run of one kind, or {}."""
    for r in reversed(load()):
        if r.get("kind") != kind or (ok_only and not r.get("ok")):
            continue
        if completed_only and kind == "google" and r.get("ok") and "urls_in" not in r:
            continue
        return r
    return {}


def age_days(when, today=None):
    """Whole days between a recorded run and today. None when unparseable.

    `today` may be a date or an ISO string: report.py holds it as a string,
    and taking only a date crashed the whole report the first time a run was
    actually recorded.
    """
    if not when:
        return None
    if isinstance(today, str):
        try:
            today = datetime.date.fromisoformat(today[:10])
        except ValueError:
            today = None
    try:
        day = datetime.date.fromisoformat(when[:10])
    except (ValueError, TypeError):
        return None
    return ((today or datetime.date.today()) - day).days


def main():
    if len(sys.argv) < 2 or sys.argv[1] == "show":
        for kind in KINDS:
            r = last(kind, ok_only=False)
            if not r:
                print(f"  {kind:<8} never run")
                continue
            state = "ok" if r.get("ok") else (r.get("why") or "failed")
            extra = " ".join(f"{k}={v}" for k, v in r.items()
                             if k not in ("kind", "ok", "when", "why"))
            print(f"  {kind:<8} {r['when']}  {state}  {extra}")
        return
    kind = sys.argv[1]
    if kind not in KINDS:
        sys.exit(__doc__)
    args = sys.argv[2:]
    ok = "--ok" in args
    why = ("google served /sorry/, unusual traffic" if "--blocked" in args
           else "" if ok else "the step did not finish")
    counts = {}
    if "--found" in args:
        counts["found"] = int(args[args.index("--found") + 1])
    record(kind, ok, why=why, **counts)
    print(f"{kind}: {'ok' if ok else why}")


if __name__ == "__main__":
    main()
