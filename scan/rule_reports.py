#!/usr/bin/env python3
"""Rows you say are in the wrong bucket. The work queue for rules.py.

mark.py records whether a job was worth seeing. This records something else:
that the classification itself is wrong. The reason strings are the point,
because they name the rule that misfired.

One entry per report, append-only, so a repeat report is visible rather than
overwriting the first.
"""
import json, pathlib, datetime, os, tempfile

import config

F = config.STATE / "rule-reports.json"
BUCKETS = ("clean", "check", "country", "blocked", "failed", "closed",
           "handled", "")
KEEP = 2000


def load():
    if not F.exists():
        return []
    try:
        d = json.loads(F.read_text())
        return d if isinstance(d, list) else []
    except (json.JSONDecodeError, OSError):
        return []


def save(items):
    fd, tmp = tempfile.mkstemp(dir=str(F.parent), prefix=".rule-reports-")
    try:
        with os.fdopen(fd, "w") as fh:
            json.dump(items[-KEEP:], fh, indent=1)
        os.replace(tmp, F)
    except BaseException:
        pathlib.Path(tmp).unlink(missing_ok=True)
        raise


def add(url, bucket_now, expected="", reasons=(), company="", title="",
        note=""):
    """Record one wrong-bucket report. Returns it."""
    if expected not in BUCKETS:
        raise ValueError(f"expected must be one of {BUCKETS}")
    item = dict(url=url, company=company[:80], title=title[:200],
                bucket_now=bucket_now[:20], expected=expected,
                reasons=[str(r)[:200] for r in reasons][:12],
                note=note[:1000], date=str(datetime.date.today()), open=True)
    items = load()
    items.append(item)
    save(items)
    return item


def resolve(reason):
    """Close every open report whose reasons include this string."""
    items = load()
    n = 0
    for it in items:
        if it.get("open") and reason in it.get("reasons", []):
            it["open"] = False
            it["resolved"] = str(datetime.date.today())
            n += 1
    if n:
        save(items)
    return n
