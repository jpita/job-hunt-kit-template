#!/usr/bin/env python3
"""Judge the job pages Google returned. No company list, no board sweep.

Input is the JSON from harvest-google.js: a list of job page URLs. Each one is
fetched from its board API for the country and the full body, then judged with
the same rules as rules.py.

Nothing is dropped. Every job Google returned appears in the report, sorted
into a bucket, so a wrong rule is visible rather than silent.

google-seen.json remembers the date each job URL was first seen. It never hides
anything: a job first seen today is tagged NEW and sorted to the top of its
bucket, and everything older stays listed underneath.

  python3 google_scan.py harvest.json
"""
import json, re, sys, pathlib, datetime, html, urllib.request, urllib.error

import config

import bodies
import judge as judging  # one place both scanners judge from
import rules  # the title and geography rules live there
import runlog
import storage

HERE = config.STATE
OUT = HERE / "google-report.html"
SEEN = HERE / "google-seen.json"
UA = {"User-Agent": "Mozilla/5.0"}

HOME = config.HOME_OR_ANYWHERE

JOB_URL = re.compile(
    r"https://(?:jobs\.lever\.co|(?:job-)?boards\.greenhouse\.io|jobs\.ashbyhq\.com)"
    r"/([A-Za-z0-9._-]+)/(?:jobs/)?([0-9a-f-]+|\d+)")


def posted_date(value):
    """Normalise board publication timestamps to YYYY-MM-DD."""
    if not value:
        return ""
    if isinstance(value, (int, float)):
        return str(datetime.datetime.fromtimestamp(
            value / 1000, datetime.timezone.utc).date())
    return str(value)[:10]


def parse(url):
    """(source, slug, job id) from a job page URL."""
    m = JOB_URL.match(url)
    if not m:
        return None
    host = url.split("/")[2]
    src = ("lever" if "lever" in host
           else "greenhouse" if "greenhouse" in host else "ashby")
    return src, m.group(1), m.group(2)


def get(url):
    try:
        with urllib.request.urlopen(
                urllib.request.Request(url, headers=UA), timeout=25) as r:
            return json.load(r)
    except Exception:
        return None


def fetch_lever(slug, jid, url):
    d = get(f"https://api.lever.co/v0/postings/{slug}/{jid}")
    if not d:
        return None
    cats = d.get("categories") or {}
    return dict(
        title=d.get("text", ""), url=url, company=slug,
        loc=" / ".join(cats.get("allLocations") or [cats.get("location", "")]),
        country=d.get("country") or "",
        remote=d.get("workplaceType") == "remote",
        body=(d.get("descriptionPlain", "") + " " + d.get("additionalPlain", "")),
        pay=(d.get("salaryRange") or {}).get("text", ""),
        posted=posted_date(d.get("createdAt")))


def fetch_greenhouse(slug, jid, url):
    d = get(f"https://boards-api.greenhouse.io/v1/boards/{slug}/jobs/{jid}")
    if not d:
        return None
    return dict(
        title=d.get("title", ""), url=url, company=slug,
        loc=(d.get("location") or {}).get("name", ""), country="",
        body=rules.strip(d.get("content")), pay="",
        posted=posted_date(d.get("first_published")))


_ashby_cache = {}


def fetch_ashby(slug, jid, url):
    """Ashby has no per-job endpoint, so read the board once and match the id."""
    if slug not in _ashby_cache:
        d = get(f"https://api.ashbyhq.com/posting-api/job-board/{slug}?includeCompensation=true")
        _ashby_cache[slug] = (d or {}).get("jobs", [])
    for j in _ashby_cache[slug]:
        if jid in j.get("jobUrl", ""):
            locs = [j.get("location", "")] + [
                s.get("location", "") for s in (j.get("secondaryLocations") or [])]
            return dict(
                title=j.get("title", ""), url=url, company=slug,
                loc=" / ".join(x for x in locs if x), country="",
                remote=j.get("isRemote"),
                body=rules.strip(j.get("descriptionHtml")),
                pay=(j.get("compensation") or {}).get("compensationTierSummary") or "",
                posted=posted_date(j.get("publishedAt")))
    return None


FETCH = {"lever": fetch_lever, "greenhouse": fetch_greenhouse, "ashby": fetch_ashby}

TITLE_TAG = re.compile(r"<title[^>]*>(.*?)</title>", re.I | re.S)
OG_TITLE = re.compile(r'<meta[^>]+property="og:title"[^>]+content="([^"]*)"', re.I)
LD_JSON = re.compile(
    r'<script[^>]+type="application/ld\+json"[^>]*>(.*?)</script>', re.I | re.S)
ASHBY_APPDATA = re.compile(r"window\.__appData\s*=\s*(\{)")


def fetch_page(url):
    """(status, final url, text) for the public job page, redirects followed."""
    try:
        with urllib.request.urlopen(
                urllib.request.Request(url, headers=UA), timeout=25) as r:
            return r.status, r.geturl(), r.read(2000000).decode("utf-8", "replace")
    except urllib.error.HTTPError as e:
        try:
            body = e.read(2000000).decode("utf-8", "replace")
        except Exception:
            body = ""
        return e.code, e.geturl(), body
    except Exception:
        return 0, url, ""


def page_title(page):
    m = OG_TITLE.search(page) or TITLE_TAG.search(page)
    if not m:
        return ""
    t = html.unescape(re.sub(r"\s+", " ", m.group(1))).strip()
    for junk in (" - Job Board", " | Job Board", " @ ", " - Lever", " | Greenhouse"):
        t = t.split(junk)[0]
    return t[:120]


def _place(node):
    """The locality strings inside a schema.org jobLocation, in order."""
    out = []
    for n in (node if isinstance(node, list) else [node]):
        if not isinstance(n, dict):
            continue
        a = n.get("address") or {}
        bits = [a.get("addressLocality"), a.get("addressRegion"),
                a.get("addressCountry")]
        text = ", ".join(str(b) for b in bits if b)
        if text:
            out.append(text)
    return out


def from_jsonld(page, url, slug):
    """A job dict built from the page's schema.org JobPosting, or None.

    Lever serves this on every live posting, including the ones whose public
    API answers 404, so it is the only way to read those.
    """
    for block in LD_JSON.findall(page):
        try:
            d = json.loads(block.strip())
        except json.JSONDecodeError:
            continue
        for d in (d if isinstance(d, list) else [d]):
            if not isinstance(d, dict) or d.get("@type") != "JobPosting":
                continue
            locs = _place(d.get("jobLocation"))
            if d.get("jobLocationType") == "TELECOMMUTE":
                locs.insert(0, "Remote")
            pay = d.get("baseSalary") or {}
            val = pay.get("value") if isinstance(pay, dict) else {}
            money = ""
            if isinstance(val, dict) and (val.get("minValue") or val.get("value")):
                money = " ".join(str(x) for x in [
                    pay.get("currency", ""), val.get("minValue") or val.get("value"),
                    val.get("maxValue"), val.get("unitText", "")] if x)
            return dict(
                title=str(d.get("title") or "")[:200], url=url, company=slug,
                loc=" / ".join(locs), country="",
                body=rules.strip(d.get("description") or ""),
                pay=money, posted=posted_date(d.get("datePosted")))
    return None


def _path(u):
    return u.split("?")[0].split("#")[0].split("/", 3)[-1].rstrip("/").lower()


def read_page(url, slug):
    """Read the public page when the board API would not answer.

    Returns ("live", job), ("closed", title) or ("unknown", title).

    A closed posting is never a plain 404: Greenhouse sends the visitor to the
    board root with ?error=true or to the company careers site, and Ashby
    serves its normal shell with posting:null. Each of those is proof the
    posting is gone, which is worth more than leaving the row unread.
    """
    status, final, page = fetch_page(url)
    if status == 0:
        return "unknown", ""
    title = page_title(page)
    if status == 404:
        return "closed", title
    if status == 200:
        job = from_jsonld(page, url, slug)
        if job and job.get("title"):
            return "live", job
        m = ASHBY_APPDATA.search(page)
        if m and re.search(r'"posting"\s*:\s*null', page):
            return "closed", title
        # Redirected off the posting's own path: the board sent the visitor to
        # a board root or a careers page because the posting is not there.
        if _path(final) != _path(url):
            return "closed", title
    return "unknown", title


CSS = """
:root{--bg:#14140f;--fg:#e8e6de;--muted:#93918a;--line:#2c2c26;
 --link:#7fb0ff;--warn:#d9b23a;--card:#1b1b16}
html{color-scheme:dark}
body{background:var(--bg);color:var(--fg);
 font:15px/1.5 -apple-system,system-ui,sans-serif;max-width:1040px;margin:0 auto;padding:40px 20px}
h1{font-size:22px;margin-bottom:4px}
.sub{color:var(--muted);margin-bottom:28px}
h2{font-size:16px;margin-top:34px;border-bottom:1px solid var(--line);padding-bottom:6px}
table{border-collapse:collapse;width:100%;background:var(--card);border-radius:6px;overflow:hidden}
td{padding:8px 12px;border-bottom:1px solid var(--line);vertical-align:top}
tr:last-child td{border-bottom:none}
td:first-child{color:var(--muted);white-space:nowrap;width:140px}
a{color:var(--link);text-decoration:none}a:hover{text-decoration:underline}
.why{color:var(--warn);font-size:13px;width:300px}
.count{color:var(--muted);font-weight:normal}
.empty{color:var(--muted);padding:8px 0}
.new{background:#2b5c2b;color:#d8f0d8;font-size:11px;font-weight:600;
 padding:1px 6px;border-radius:3px;margin-right:8px;vertical-align:1px}
tr.fresh td{background:#1d241d}
.seen{color:var(--muted);font-size:12px;white-space:nowrap;width:90px}
"""

SECTIONS = [
    ("clean", "Clean", "nothing against them"),
    ("check", "Worth a glance", "right role, only the arrangement is unclear"),
    ("level", "One level down", f"a real {config.ROLE_NOUN}, below the level you want"),
    ("role", "Wrong kind of role", f"not a {config.ROLE_NOUN}"),
    ("country", "Wrong country", "tied to a place you cannot work from"),
    ("blocked", "Legally impossible", "US persons, clearance, US-only"),
    ("closed", "Closed", "the board itself says the posting is gone"),
    ("failed", "Could not read", "likely closed, still listed by Google. Check by hand"),
]


def render(rows, queried, today):
    def table(items):
        if not items:
            return '<div class="empty">none</div>'
        # New first, then newest-first by the day it appeared. Nothing is cut.
        items = sorted(items, key=lambda x: (x["first_seen"], x["company"]),
                       reverse=True)
        out = []
        for r in items:
            fresh = r["first_seen"] == today
            why = html.escape("; ".join(r["hard"] + r["soft"]))
            tag = '<span class="new">NEW</span>' if fresh else ""
            when = "today" if fresh else r["first_seen"]
            out.append(
                f'<tr class="{"fresh" if fresh else ""}">'
                f'<td>{html.escape(r["company"])}</td>'
                f'<td>{tag}<a href="{html.escape(r["url"])}" target="_blank">'
                f'{html.escape(r["title"] or r["url"])}</a></td>'
                f'<td class="why">{why}</td>'
                f'<td class="seen">{when}</td></tr>')
        return f"<table>{''.join(out)}</table>"

    parts = []
    for key, name, note in SECTIONS:
        items = [r for r in rows if r["bucket"] == key]
        n_new = len([r for r in items if r["first_seen"] == today])
        extra = f", {n_new} new" if n_new else ""
        parts.append(f'<h2>{name} <span class="count">({len(items)}{extra})</span> '
                     f'&mdash; {note}</h2>{table(items)}')

    return (f'<!doctype html><meta charset="utf-8">'
            f'<meta name="viewport" content="width=device-width,initial-scale=1">'
            f'<title>Job scan, from Google</title><style>{CSS}</style>'
            f'<h1>Job scan, from Google</h1>'
            f'<div class="sub">{datetime.date.today():%d-%m-%Y} &middot; '
            f'{queried} job pages returned by Google &middot; '
            f'{len(rows)} judged, none hidden &middot; '
            f'{len([r for r in rows if r["first_seen"] == today])} new today</div>'
            + "".join(parts))


def main():
    if len(sys.argv) < 2:
        sys.exit(__doc__)
    if sys.argv[1] == "--all-known":
        if not SEEN.exists():
            sys.exit("No Google history to refresh.")
        urls = [r["url"] for r in json.loads(SEEN.read_text())]
    else:
        d = json.loads(pathlib.Path(sys.argv[1]).read_text())
        urls = d.get("jobs", d) if isinstance(d, dict) else d
    urls = list(dict.fromkeys(urls))
    today = str(datetime.date.today())
    print(f"{len(urls)} job pages from Google", file=sys.stderr)

    # Carry the first-seen date forward. A URL missing from today's search is
    # kept, not dropped, so the report never loses a job it once showed.
    history = {}
    if SEEN.exists():
        for r in json.loads(SEEN.read_text()):
            history[r["url"]] = r

    store = bodies.load()
    rows = []
    for i, url in enumerate(urls, 1):
        previous = history.get(url, {})
        first = previous.get("first_seen", today)
        posted = previous.get("posted", "")
        p = parse(url)
        if not p:
            rows.append(dict(company="?", title="", url=url, bucket="failed",
                             hard=[], soft=["URL shape not recognised"],
                             first_seen=first, posted=posted, pay="",
                             closed=""))
            continue
        src, slug, jid = p
        job = FETCH[src](slug, jid, url)
        if not job:
            # The API said nothing. Read the page a visitor would see before
            # calling the posting unreadable: a live Lever posting whose API
            # answers 404 is still fully readable from the page itself.
            state, found = read_page(url, slug)
            if state == "live":
                job = found
            else:
                rows.append(dict(
                    company=slug, title=found, url=url,
                    bucket="closed" if state == "closed" else "failed",
                    hard=[],
                    soft=(["the board no longer serves this posting"]
                          if state == "closed"
                          else ["the board API and the page both refused"]),
                    first_seen=first, posted=posted, pay="",
                    closed=today if state == "closed" else ""))
                continue
        bodies.put(store, url, job)
        bucket, hard, soft = judging.judge(job)
        rows.append(dict(company=slug, title=job["title"], url=url,
                         loc=job.get("loc") or "",
                         home=bool(HOME.search(
                             f'{job["title"]} {job.get("loc","")} {job["body"]}')),
                         bucket=bucket, hard=hard, soft=soft, first_seen=first,
                         posted=job.get("posted") or posted,
                         pay=rules.salary(job.get("pay", ""), job["body"]),
                         closed=""))
        if i % 25 == 0:
            print(f"  {i}/{len(urls)}", file=sys.stderr)

    # Do not replace the last useful snapshot after a substantial read failure.
    read_ok = sum(r["bucket"] != "failed" for r in rows)
    minimum = max(1, (len(urls) + 1) // 2)
    if read_ok < minimum:
        runlog.record("google", ok=False,
                      why=f"only {read_ok} of {len(urls)} current pages could be read",
                      urls_in=len(urls), read_ok=read_ok)
        print(f"  ! Google processing incomplete: {read_ok} of {len(urls)} pages read",
              file=sys.stderr)
        return 1

    # Anything seen before but absent from today's search stays in the report.
    fresh_urls = {r["url"] for r in rows}
    carried = [r for u, r in history.items() if u not in fresh_urls]
    rows += carried

    storage.write_text(OUT, render(rows, len(urls), today))
    storage.write_json(SEEN, rows, indent=1)
    bodies.save(store)
    n_new = len([r for r in rows if r["first_seen"] == today])
    for key, name, _ in SECTIONS:
        items = [r for r in rows if r["bucket"] == key]
        new = len([r for r in items if r["first_seen"] == today])
        print(f"  {name}: {len(items)}" + (f" ({new} new)" if new else ""))
    print(f"  {n_new} new today, {len(carried)} carried from earlier runs")

    runlog.record("google", ok=True,
                  urls_in=len(urls), judged=len(rows), read_ok=read_ok,
                  new=n_new, carried=len(carried))
    print(OUT)
    return 0


if __name__ == "__main__":
    sys.exit(main())
