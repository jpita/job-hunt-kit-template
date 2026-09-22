#!/usr/bin/env python3
"""The raw text of every posting a scanner has read, so rules can be re-run.

board-seen.json stores verdicts. A verdict cannot be recomputed from another
verdict, so every rules change used to need a full 751-board sweep before it
showed anything. This keeps what the rules actually read: title, location,
country, the board's remote flag, pay, and the body.

Gzipped, and kept out of git: it is a cache, and a sweep rebuilds it. About
15 MB of text, a few MB on disk.
"""
import gzip, json, os, pathlib, tempfile

import config

F = config.STATE / "bodies.json.gz"

FIELDS = ("title", "loc", "country", "remote", "pay", "body")


def load():
    """url -> the fields the rules read. Empty when the cache is missing."""
    if not F.exists():
        return {}
    try:
        with gzip.open(F, "rt", encoding="utf-8") as fh:
            return json.load(fh)
    except (OSError, json.JSONDecodeError, EOFError):
        return {}


def save(store):
    fd, tmp = tempfile.mkstemp(dir=str(F.parent), prefix=".bodies-")
    os.close(fd)
    try:
        with gzip.open(tmp, "wt", encoding="utf-8") as fh:
            json.dump(store, fh)
        os.replace(tmp, F)
    except BaseException:
        pathlib.Path(tmp).unlink(missing_ok=True)
        raise


def put(store, url, job):
    """Keep only what the rules read, so the cache cannot drift from them."""
    store[url] = {k: job.get(k) for k in FIELDS}


def as_job(url, row):
    """One cache row back in the shape judge.judge expects."""
    job = {k: row.get(k) for k in FIELDS}
    job["url"] = url
    job["body"] = job.get("body") or ""
    job["country"] = job.get("country") or ""
    return job
