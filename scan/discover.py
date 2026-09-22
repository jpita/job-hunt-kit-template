#!/usr/bin/env python3
"""Find new job-board slugs and append them to companies.txt.

The scan itself only reads boards already listed. This is the step that grows
that list. It works the way the old manual Google harvest did: search for the
board URL shape, take the slug out of the path, keep the slugs whose board API
answers.

Two sources, because no free engine allows unattended site: querying:

  GitHub code search   runs in cron, no browser, no CAPTCHA. The default.
  --slugs FILE         JSON from harvest-google.js, the real Google site:
                       harvest. It needs the Claude Chrome extension and a live
                       session, so it is run by hand, not by cron.
"""
import argparse, json, os, re, shutil, subprocess, sys, urllib.request, pathlib, datetime

import config

# cron runs with a minimal PATH, so find gh up front rather than trusting PATH.
GH = shutil.which("gh") or "gh"

HERE = config.STATE
COMPANIES = config.COMPANIES
UA = {"User-Agent": "Mozilla/5.0"}
PAGES = int(os.environ.get("DISCOVER_PAGES", 10))  # GitHub caps the set at 1000
PER_PAGE = 100

# source -> (host to search for, slug regex, board API to confirm the slug)
BOARDS = {
    "lever": (
        "jobs.lever.co",
        re.compile(r"jobs\.lever\.co/([A-Za-z0-9._-]{2,40})"),
        "https://api.lever.co/v0/postings/{}?mode=json",
    ),
    "greenhouse": (
        "boards.greenhouse.io",
        re.compile(r"(?:boards|job-boards)\.greenhouse\.io/(?:embed/job_board\?for=)?"
                   r"([A-Za-z0-9._-]{2,40})"),
        "https://boards-api.greenhouse.io/v1/boards/{}/jobs",
    ),
    "ashby": (
        "jobs.ashbyhq.com",
        re.compile(r"jobs\.ashbyhq\.com/([A-Za-z0-9._-]{2,40})"),
        "https://api.ashbyhq.com/posting-api/job-board/{}",
    ),
}

# Path segments that are not company slugs.
JUNK = {"embed", "api", "jobs", "job", "board", "boards", "search", "www",
        "static", "assets", "images", "favicon", "robots", "sitemap", "null",
        "undefined", "example", "test", "your-company", "company", "slug"}


def gh_search(host, page):
    """One page of GitHub code search, with the matched text fragments."""
    cmd = [GH, "api", "-X", "GET", "search/code",
           "-H", "Accept: application/vnd.github.text-match+json",
           "-f", f'q="{host}"',
           "-f", f"per_page={PER_PAGE}", "-f", f"page={page}"]
    r = subprocess.run(cmd, capture_output=True, text=True)
    if r.returncode:
        print(f"  ! gh page {page}: {r.stderr.strip()[:120]}", file=sys.stderr)
        return None
    return json.loads(r.stdout)


def harvest(host, slug_rx):
    """Every slug GitHub code search can see for one board host."""
    slugs = set()
    for page in range(1, PAGES + 1):
        d = gh_search(host, page)
        if not d:
            break
        items = d.get("items", [])
        if not items:
            break
        for it in items:
            for tm in it.get("text_matches", []):
                slugs |= set(slug_rx.findall(tm.get("fragment", "")))
    return {s for s in slugs if s.lower() not in JUNK}



def slugs_from_file(path):
    """Slugs harvested by harvest-google.js, as {source: [slug, ...]}.

    That harvest runs in the browser through the Claude Chrome extension, so it
    cannot run unattended. Save its JSON and pass the path here.
    """
    try:
        d = json.loads(pathlib.Path(path).read_text())
    except Exception as e:
        print(f"  ! {path}: {e}", file=sys.stderr)
        return {}
    d = d.get("slugs", d)
    return {k: {s for s in v if s.lower() not in JUNK} for k, v in d.items()}


def board_is_live(url):
    """A slug only counts if its board API actually answers with postings."""
    try:
        with urllib.request.urlopen(
                urllib.request.Request(url, headers=UA), timeout=20) as r:
            d = json.load(r)
    except Exception:
        return False
    jobs = d if isinstance(d, list) else (d.get("jobs") or [])
    return bool(jobs)


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--slugs", metavar="FILE",
                    help="JSON from harvest-google.js to merge in")
    ap.add_argument("--no-github", action="store_true",
                    help="skip the GitHub search, use only --slugs")
    args = ap.parse_args()

    text = COMPANIES.read_text()
    known = set()
    for line in text.splitlines():
        line = line.strip().lstrip("# ").split("(")[0].strip()
        if ":" in line:
            known.add(line.lower())

    from_search = {}
    if args.slugs:
        from_search = slugs_from_file(args.slugs)
        n = sum(len(v) for v in from_search.values())
        print(f"{n} slugs from {args.slugs}", file=sys.stderr)

    added = []
    for src, (host, slug_rx, api) in BOARDS.items():
        found = set() if args.no_github else harvest(host, slug_rx)
        if not args.no_github:
            print(f"searching {host} (GitHub) ...", file=sys.stderr)
        found |= from_search.get(src, set())
        new = [s for s in sorted(found) if f"{src}:{s}".lower() not in known]
        print(f"  {len(found)} slugs, {len(new)} not in companies.txt",
              file=sys.stderr)
        for s in new:
            if board_is_live(api.format(s)):
                added.append(f"{src}:{s}")
                print(f"  + {src}:{s}", file=sys.stderr)

    if not added:
        print("No new live boards.")
        return
    # Re-read immediately before writing. The live-check loop takes minutes,
    # and writing back the copy read at the start discards anything added
    # meanwhile: a test run wiped 79 boards this way.
    live = COMPANIES.read_text()
    have = {l.strip().lower() for l in live.splitlines()
            if ":" in l and not l.strip().startswith("#")}
    added = [b for b in added if b.lower() not in have]
    if not added:
        print("No new live boards: already added while this was running.")
        return
    stamp = datetime.date.today().strftime("%d-%m-%Y")
    COMPANIES.write_text(
        live.rstrip("\n")
        + f"\n# --- added {stamp} by discover.py ---\n"
        + "\n".join(added) + "\n")
    print(f"Added {len(added)} board(s) to companies.txt.")


main()
