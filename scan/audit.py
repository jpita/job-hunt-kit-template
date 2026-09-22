#!/usr/bin/env python3
"""Check a bucket against the live postings, without waiting for a sweep.

board-seen.json stores verdicts, not job bodies, so a rules change shows
nothing until the next sweep. This refetches the postings in one bucket and
prints what the current rules make of them, so a change can be checked before
it is trusted.

  python3 audit.py                     how many rows in each bucket
  python3 audit.py check               refetch Worth a glance, show every move
  python3 audit.py check --stay        only the rows that do not move
  python3 audit.py reported            refetch every open wrong-bucket report
  python3 audit.py check --limit 40    stop after 40 postings

Read-only. It never writes a seen file or the report.
"""
import argparse, collections, sys

import judge
import report
import rule_reports


def rows_for(target):
    rows = report.load()
    if target == "reported":
        want = {i["url"] for i in rule_reports.load() if i.get("open")}
        return [r for r in rows if r["url"] in want]
    return [r for r in rows if r["bucket"] == target]


def counts():
    rows = report.load()
    c = collections.Counter(r["bucket"] for r in rows)
    for key, name, _ in report.SECTIONS:
        print(f"  {name:<22} {c.get(key, 0)}")
    print(f"  {'total':<22} {len(rows)}")


def main():
    ap = argparse.ArgumentParser(add_help=False)
    ap.add_argument("target", nargs="?")
    ap.add_argument("--limit", type=int, default=0)
    ap.add_argument("--stay", action="store_true")
    ap.add_argument("-h", "--help", action="store_true")
    a = ap.parse_args()
    if a.help or not a.target:
        print(__doc__ if a.help else "")
        return counts()

    rows = rows_for(a.target)
    if a.limit:
        rows = rows[:a.limit]
    if not rows:
        return print(f"  nothing in {a.target}")
    print(f"  refetching {len(rows)} posting(s) from {a.target}\n")

    moved, stayed, gone, unread = [], [], [], []
    for r in rows:
        job = judge.fetch(r["url"])
        if not job:
            unread.append(r)
            continue
        if not judge.keep(job["title"]):
            gone.append((r, job))
            continue
        bucket, hard, soft = judge.judge(job)
        (stayed if bucket == r["bucket"] else moved).append(
            (r, job, bucket, hard, soft))

    def line(r, job, bucket, hard, soft):
        print(f'  {r["bucket"]:>8} -> {bucket:<8} {job["title"][:48]:<50}'
              f' | {job["loc"][:26]}')
        why = "; ".join(hard + soft)
        if why:
            print(f'           {why[:104]}')

    if not a.stay:
        for item in sorted(moved, key=lambda x: x[2]):
            line(*item)
        for r, job in gone:
            print(f'  {r["bucket"]:>8} -> dropped  {job["title"][:48]:<50}'
                  f' | not your kind of posting, or a board fixture')
    else:
        for item in stayed:
            line(*item)

    print(f'\n  {len(moved)} move, {len(stayed)} stay, {len(gone)} dropped, '
          f'{len(unread)} could not be read')
    if moved:
        for b, n in collections.Counter(m[2] for m in moved).most_common():
            print(f'    -> {b}: {n}')


if __name__ == "__main__":
    main()
