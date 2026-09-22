#!/usr/bin/env python3
"""Fetch one job page and judge it. The single place both scanners agree on.

scan.py and google_scan.py each had their own copy of the judging code, and
they had drifted: only one of them dropped a board's placeholder postings, and
only one of them used the board's own remote flag. A row could land in two
different buckets depending on which scanner saw it first.

No state, no report. rules.py owns the rules; this owns applying them.
"""
import json, re, urllib.request

import rules

UA = {"User-Agent": "Mozilla/5.0"}
GEO_PREFIX = ("location:", "board says country", "body says based in")

JOB_URL = re.compile(
    r"https://(?:jobs\.lever\.co|(?:job-)?boards(?:\.eu)?\.greenhouse\.io"
    r"|jobs\.ashbyhq\.com)"
    r"/([A-Za-z0-9._-]+)/(?:jobs/)?([0-9a-f-]+|\d+)")


def bucket_for(hard, soft):
    """The one place a bucket is decided, from reasons alone.

    report.py needs this from stored reasons and judge() needs it from fresh
    ones. Two copies drifted once already: a posting that was the wrong
    role and also in the wrong country showed as one thing here and
    another on the page.
    """
    if rules.NOT_QA_REASON in soft:
        return "notqa"
    if hard and all(h.startswith(GEO_PREFIX) for h in hard):
        return "country"
    if hard:
        return "blocked"
    if not soft:
        return "clean"
    return rules.title_bucket(soft) or "check"


def judge(job):
    """(bucket, hard, soft) for one job dict.

    Expects: title, loc, body, country, remote. remote may be None when the
    board does not say.
    """
    t = job.get("title") or ""
    loc = job.get("loc") or ""
    body = job.get("body") or ""
    hay = f"{t} {loc} {body}"

    hard = [n for n, rx in rules.HARD if rx.search(hay)]
    remote_here = bool(job.get("remote")) or bool(
        rules.REMOTE.search(f"{t} {loc}")) or bool(
        rules.REMOTE_LOC.search(loc)) or bool(
        rules.REMOTE_BODY.search(body[:1500]))
    soft = [n for n, rx in rules.SOFT if rx.search(hay) and not remote_here]

    ghard, gsoft = rules.geo_verdict(loc, job.get("country"), body, t,
                                     remote=remote_here)
    hard += ghard
    soft += gsoft
    if not remote_here:
        soft.append("no remote signal")
    # A posting that is not about your role at all is bucketed, never dropped:
    # you tag these yourself, and a silent deletion could lose a real job.
    if not keep(t):
        soft.append(rules.NOT_QA_REASON)
    if rules.TITLE_WEAK.search(t):
        soft.append(rules.WRONG_ROLE_REASON)
    if not rules.TITLE_OK.search(t):
        soft.append(rules.LEVEL_REASON)

    return bucket_for(hard, soft), hard, soft


def keep(title):
    """False for a posting that is not your kind of job, or is a board's own fixture.

    A blank title is kept. It means the board would not answer and the page
    scrape found nothing, so there is nothing to judge, and dropping it would
    be a verdict on missing data rather than on the posting.
    """
    title = (title or "").strip()
    if not title:
        return True
    return bool(rules.TITLE_RELEVANT.search(title)) and not \
        rules.TITLE_JUNK.search(title)


# ------------------------------------------------------------------ fetching
def _get(url, timeout=20):
    try:
        with urllib.request.urlopen(
                urllib.request.Request(url, headers=UA), timeout=timeout) as r:
            return json.load(r)
    except Exception:
        return None


_ashby_boards = {}


def fetch(url):
    """One job by its public page url, or None when the board will not answer."""
    m = JOB_URL.match(url or "")
    if not m:
        return None
    slug, jid = m.group(1), m.group(2)
    host = url.split("/")[2]

    if "lever" in host:
        d = _get(f"https://api.lever.co/v0/postings/{slug}/{jid}")
        if not d:
            return None
        cats = d.get("categories") or {}
        return dict(
            title=d.get("text", ""), url=url, company=slug,
            loc=" / ".join(cats.get("allLocations") or [cats.get("location", "")]),
            country=d.get("country") or "",
            body=(d.get("descriptionPlain", "") + " "
                  + d.get("additionalPlain", "")),
            remote=(d.get("workplaceType") == "remote"),
            pay=(d.get("salaryRange") or {}).get("text", ""))

    if "greenhouse" in host:
        d = _get(f"https://boards-api.greenhouse.io/v1/boards/{slug}/jobs/{jid}")
        if not d:
            return None
        return dict(
            title=d.get("title", ""), url=url, company=slug,
            loc=(d.get("location") or {}).get("name", ""), country="",
            body=rules.strip(d.get("content")), remote=None, pay="")

    if slug not in _ashby_boards:
        d = _get("https://api.ashbyhq.com/posting-api/job-board/"
                 f"{slug}?includeCompensation=true")
        _ashby_boards[slug] = (d or {}).get("jobs", [])
    for j in _ashby_boards[slug]:
        if jid in j.get("jobUrl", ""):
            locs = [j.get("location", "")] + [
                s.get("location", "") for s in (j.get("secondaryLocations") or [])]
            return dict(
                title=j.get("title", ""), url=url, company=slug,
                loc=" / ".join(x for x in locs if x), country="",
                body=rules.strip(j.get("descriptionHtml")),
                remote=j.get("isRemote"),
                pay=(j.get("compensation") or {}).get(
                    "compensationTierSummary") or "")
    return None
