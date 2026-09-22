#!/usr/bin/env python3
"""Your own verdicts on a job. The one store the report writes to.

feedback.json started as url -> "good" | "bad". It now holds three separate
things per job, because they answer different questions:

  verdict  good | bad | ""        was this worth showing me
  state    applied | wont | ""    have I dealt with it
  note     free text              why

The old one-word shape is still read, so nothing marked before this file
existed is lost. It is rewritten in the new shape on the next write.

No network, no rendering. mark.py, report.py and serve.py all come through
here so the shape is defined once.
"""
import json, pathlib, datetime, os, tempfile

import config

F = config.STATE / "feedback.json"

VERDICTS = ("good", "bad", "")
# "wont" is short for "will not apply". Both hide the job from the live lists.
STATES = ("applied", "wont", "")
HANDLED = ("applied", "wont")


def _entry(v):
    """One stored value, in the new shape, whichever shape it was saved in."""
    if isinstance(v, str):
        return {"verdict": v, "state": "", "note": "", "date": ""}
    return {"verdict": v.get("verdict", ""), "state": v.get("state", ""),
            "note": v.get("note", ""), "date": v.get("date", "")}


def load():
    """url -> entry. Missing or unreadable file reads as empty, never raises."""
    if not F.exists():
        return {}
    try:
        return {u: _entry(v) for u, v in json.loads(F.read_text()).items()}
    except (json.JSONDecodeError, OSError, AttributeError):
        return {}


def save(marks):
    """Write the whole store atomically, so a crash cannot truncate it."""
    fd, tmp = tempfile.mkstemp(dir=str(F.parent), prefix=".feedback-")
    try:
        with os.fdopen(fd, "w") as fh:
            json.dump(marks, fh, indent=1)
        os.replace(tmp, F)
    except BaseException:
        pathlib.Path(tmp).unlink(missing_ok=True)
        raise


def set_fields(url, **fields):
    """Change only the named fields of one job. Returns the stored entry.

    Reads the live file first, so a click in the browser cannot overwrite a
    mark made from the terminal a second earlier.
    """
    for k, v in fields.items():
        if k == "verdict" and v not in VERDICTS:
            raise ValueError(f"verdict must be one of {VERDICTS}")
        if k == "state" and v not in STATES:
            raise ValueError(f"state must be one of {STATES}")
    marks = load()
    entry = marks.get(url) or _entry({})
    entry.update({k: v for k, v in fields.items()
                  if k in ("verdict", "state", "note")})
    entry["date"] = str(datetime.date.today())
    marks[url] = entry
    save(marks)
    return entry


def is_handled(entry):
    return bool(entry) and entry.get("state") in HANDLED
