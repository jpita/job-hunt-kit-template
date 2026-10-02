#!/usr/bin/env python3
"""Scan public job-board APIs for roles you can actually apply to.

Reads company slugs from companies.txt, pulls every posting body, filters on title,
then screens the real text for the blockers Google cannot see (US-persons clauses,
US-only remote, on-site). Prints only postings not seen before.
"""
import argparse, json, os, re, sys, time, urllib.request, urllib.error

import config
import pathlib, datetime, html, zlib

HERE = config.STATE
SEEN = HERE / "board-seen.json"
BOARD_LOG = HERE / "boards-read.json"
COMPANIES = config.COMPANIES
UA = {"User-Agent": "Mozilla/5.0"}

# The boards showed no throttling: 1,504 requests with zero
# errors, and 15 rapid calls to each host all returned 200. This pause is
# courtesy, not a workaround. SCAN_DELAY=0 turns it off.
DELAY = float(os.environ.get("SCAN_DELAY", "0.3"))

# A full sweep of 751 boards takes about 17 minutes, which is why it was not
# in the daily run. So Google was the only scheduled source, and on
# Once, Google served /sorry/ and the day produced nothing.
#
# Splitting the boards across seven days gives every board a weekly refresh
# for about a seventh of the time. The slice comes from a hash of the board
# name, not its position, so editing companies.txt does not reshuffle
# everything and leave a board unscanned for a fortnight.
ROTATE_DAYS = 7

import bodies
import judge as judging
import runlog
import storage

from rules import strip, salary

HOME = config.HOME_OR_ANYWHERE

def posted_date(value):
    """Normalise board publication timestamps to YYYY-MM-DD."""
    if not value:
        return ""
    if isinstance(value, (int, float)):
        return str(datetime.datetime.fromtimestamp(
            value / 1000, datetime.timezone.utc).date())
    return str(value)[:10]

def get(url):
    time.sleep(DELAY)
    try:
        with urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=25) as r:
            return json.load(r)
    except Exception as e:
        print(f"  ! {url} -> {e}", file=sys.stderr)
        return None

def ashby(slug):
    d = get(f"https://api.ashbyhq.com/posting-api/job-board/{slug}?includeCompensation=true")
    if d is None:
        return None
    out = []
    for j in d.get("jobs", []):
        locs = [j.get("location", "")] + [
            s2.get("location", "") for s2 in (j.get("secondaryLocations") or [])]
        out.append(dict(title=j["title"], url=j["jobUrl"],
                   loc=" / ".join(x for x in locs if x), country="",
                   remote=j.get("isRemote"), body=strip(j.get("descriptionHtml")),
                   pay=j.get("compensation", {}).get("compensationTierSummary") or "",
                   posted=posted_date(j.get("publishedAt"))))
    return out

def greenhouse(slug):
    d = get(f"https://boards-api.greenhouse.io/v1/boards/{slug}/jobs?content=true")
    if d is None:
        return None
    return [dict(title=j["title"], url=j["absolute_url"],
                 loc=(j.get("location") or {}).get("name", ""),
                 country="", remote=None, body=strip(j.get("content")), pay="",
                 posted=posted_date(j.get("first_published")))
            for j in d.get("jobs", [])]

def lever(slug):
    d = get(f"https://api.lever.co/v0/postings/{slug}?mode=json")
    if d is None:
        return None
    return [dict(title=j["text"], url=j["hostedUrl"],
                   loc=" / ".join((j.get("categories") or {}).get("allLocations")
                                  or [(j.get("categories") or {}).get("location", "")]),
                   country=j.get("country") or "",
                 remote=(j.get("workplaceType") == "remote"),
                 body=(j.get("descriptionPlain", "") + " " + j.get("additionalPlain", "")), pay="",
                 posted=posted_date(j.get("createdAt")))
            for j in d]

SOURCES = {"ashby": ashby, "greenhouse": greenhouse, "lever": lever}


def todays_slice(entries, day, parts=ROTATE_DAYS, never=()):
    """The boards due today, plus any board never read before.

    A board discover.py adds would otherwise wait up to a week for its slot.
    A new board can hold the one job you want, so read it the same day.
    """
    due = [e for e in entries
           if zlib.crc32(e.encode()) % parts == day % parts]
    fresh = [e for e in entries if e in never and e not in due]
    return due + fresh


def boards_read():
    """"source:slug" -> the day that board last answered.

    A board with no matching postings writes no row, so whether it was read
    cannot be inferred from board-seen.json. This is the only record
    of what was actually asked.
    """
    if not BOARD_LOG.exists():
        return {}
    try:
        return json.loads(BOARD_LOG.read_text())
    except (json.JSONDecodeError, OSError):
        return {}


def close_missing(seen, answered, today):
    """Mark every posting whose board answered but which it no longer lists.

    Presence is proven by the write above, never by matching URLs: Greenhouse
    hands back three host shapes plus custom domains, so a host change would
    read as a closure. A row is only judged when its own board answered.

    The board is (source, slug), not the slug: "anyscale" is a live Lever
    board and a live Ashby board belonging to different companies, so a slug
    alone would let one board's failure close the other's postings.

    Returns (closed now, reopened now).
    """
    live_roles = {(v.get("company"), (v.get("title") or "").strip().lower())
                  for v in seen.values() if v.get("last_seen") == today}
    closed, reopened = [], []
    for url, v in seen.items():
        # A row written before the source was stored falls back to the slug.
        board = ((v.get("src"), v.get("company")) if v.get("src")
                 else v.get("company"))
        known = answered if v.get("src") else {s for _, s in answered}
        if board not in known:
            continue
        if v.get("last_seen") == today:
            if v.pop("closed", None):
                reopened.append(url)
            continue
        # The same role listed again under a new URL is a move, not a closure.
        if (v.get("company"), (v.get("title") or "").strip().lower()) in live_roles:
            continue
        if not v.get("closed"):
            v["closed"] = today
            closed.append(url)
    return closed, reopened


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--slice", action="store_true",
                    help=f"only the boards due today, about 1/{ROTATE_DAYS} of them")
    ap.add_argument("--day", type=int,
                    help="which rotation day to run, for checking the split")
    ap.add_argument("--board", action="append",
                    help="scan only this tracked source:slug; repeat for multiple boards")
    args = ap.parse_args()

    started = time.time()
    asked = boards_read()

    def save():
        """Everything this run has learned so far.

        Called as it goes, not only at the end: a run over 500 newly
        discovered boards takes long enough that one exception used to throw
        away every board already read.
        """
        storage.write_json(SEEN, seen, indent=1)
        storage.write_json(BOARD_LOG, asked, indent=1, sort_keys=True)
        bodies.save(store)

    seen = json.loads(SEEN.read_text()) if SEEN.exists() else {}
    # The text the rules read, kept so a rules change needs no new sweep.
    store = bodies.load()
    today = str(datetime.date.today())
    fresh, blocked = [], 0
    answered, failed = set(), []
    entries = [l.strip() for l in COMPANIES.read_text().splitlines()
               if l.strip() and not l.strip().startswith("#")]
    full = len(entries)
    if args.board:
        missing = set(args.board) - set(entries)
        if missing:
            ap.error("untracked board(s): " + ", ".join(sorted(missing)))
        entries = [e for e in entries if e in args.board]
    if args.slice:
        day = args.day if args.day is not None else datetime.date.today().toordinal()
        never = {e for e in entries if e not in asked}
        entries = todays_slice(entries, day, never=never)
        extra = f", plus {len(never)} never read" if never else ""
        print(f"  rotation day {day % ROTATE_DAYS}: {len(entries)} of "
              f"{full} boards{extra}", file=sys.stderr)
    for n, line in enumerate(entries, 1):
        # A typo or an unsupported board in companies.txt used to raise
        # KeyError and end the run, losing every board read before it.
        src, _, slug = line.partition(":")
        src, slug = src.strip().lower(), slug.strip()
        if src not in SOURCES or not slug:
            print(f"  ! skipping {line!r}: not a board this can read",
                  file=sys.stderr)
            failed.append(line)
            continue
        if n % 50 == 0:
            save()
        try:
            jobs = SOURCES[src](slug)
        except Exception as e:
            # One board's bad payload must not end the run.
            print(f"  ! {src}:{slug} -> {e}", file=sys.stderr)
            jobs = None
        # None means the board did not answer. Its postings keep their old
        # verdict and are never called closed on the strength of a failure.
        if jobs is None:
            failed.append(f"{src}:{slug}")
            continue
        answered.add((src, slug))
        asked[f"{src}:{slug}"] = today
        for job in jobs:
            t = job["title"]
            # The only things dropped are a posting that is not about your role at
            # all, and a board's own placeholder or template posting.
            if not judging.keep(t):
                continue
            job["country"] = job.get("country") or ""
            bodies.put(store, job["url"], job)
            _, hard, soft = judging.judge(job)
            # Always re-judge: the rules change, so a stale verdict must not stick.
            prev = seen.get(job["url"])
            seen[job["url"]] = {"title": t, "company": slug, "src": src,
                                "loc": job.get("loc") or "",
                                "home": bool(HOME.search(
                                    f'{t} {job["loc"]} {job["body"]}')),
                                "date": (prev or {}).get("date") or today,
                                "posted": job.get("posted") or (prev or {}).get("posted", ""),
                                "last_seen": today,
                                "blocked": hard, "check": soft,
                                "pay": salary(job.get("pay", ""), job["body"])}
            if prev:
                continue
            if hard:
                blocked += 1
                continue
            job["company"] = slug
            job["home"] = seen[job["url"]]["home"]
            job["check"] = soft
            fresh.append(job)

    closed, reopened = close_missing(seen, answered, today)
    save()

    if fresh:
        print(f"## {len(fresh)} new role(s) - {datetime.date.today():%d-%m-%Y}\n")
        for j in fresh:
            flag = f" \u00b7 names {config.HOME_LABEL} or global" if j["home"] else ""
            chk = ("\n  check: " + "; ".join(j["check"])) if j["check"] else ""
            pay = f' \u00b7 {j["pay"]}' if j["pay"] else ""
            print(f'- **{j["title"]}** at {j["company"]} \u00b7 {j["loc"]}{pay}{flag}'
                  f'\n  {j["url"]}{chk}')
        print()
    else:
        print("No new roles.\n")

    # The run summary always prints, so a quiet day and a broken day differ.
    still_open = len([v for v in seen.values() if not v.get("closed")])
    print(f"  boards answered: {len(answered)} of {len(answered) + len(failed)}")
    print(f"  {blocked} new postings dropped as legally impossible")
    print(f"  closed today: {len(closed)}   reopened: {len(reopened)}")
    print(f"  {still_open} postings still open, {len(seen) - still_open} archived")
    if failed:
        print(f"  boards that did not answer ({len(failed)}): "
              + ", ".join(failed[:10]) + (" ..." if len(failed) > 10 else ""))

    # A sweep that reached almost no board is a failure, however many rows the
    # report still shows.
    total = len(answered) + len(failed)
    runlog.record("boards", ok=bool(answered) and len(answered) >= total * 0.5,
                  boards_ok=len(answered), boards_failed=len(failed),
                  of_all=full, sliced=bool(args.slice),
                  new=len(fresh), closed=len(closed), reopened=len(reopened),
                  open_now=still_open, seconds=round(time.time() - started))


if __name__ == "__main__":
    main()
