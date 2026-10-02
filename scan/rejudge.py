#!/usr/bin/env python3
"""Re-run the rules over every posting already read. No network, no sweep.

A rules change used to show nothing until the next 751-board sweep, because
only verdicts were stored. bodies.json.gz keeps the text the rules read, so
this recomputes every verdict in seconds.

  python3 rejudge.py --dry        what would change, writing nothing
  python3 rejudge.py              apply it, then rebuild report.html
  python3 rejudge.py --fetch      read the postings missing from the cache

A row with no cached text keeps its verdict and is reported as skipped. The
next sweep fills it, or --fetch does it now.
"""
import argparse, collections, datetime, json, pathlib, re, sys

import config

import bodies
import judge
import report
import runlog
import storage

HOME = config.HOME_OR_ANYWHERE

HERE = config.STATE
BOARD = HERE / "board-seen.json"
GOOGLE = HERE / "google-seen.json"


def rejudge_board(store, moves, dropped):
    if not BOARD.exists():
        return 0, 0
    seen = json.loads(BOARD.read_text())
    done = skipped = 0
    for url, v in list(seen.items()):
        row = store.get(url)
        # Whether a posting is your kind of job at all is decided by its title, and
        # the title is stored. So a row is droppable even with no cached body.
        title = (row or {}).get("title") or v.get("title") or ""
        if not judge.keep(title) and not row:
            # Nothing cached to re-judge, but the title alone settles it.
            v["blocked"], v["check"] = [], [judge.rules.NOT_QA_REASON]
            dropped.append((url, title))
            done += 1
            continue
        if not row:
            skipped += 1
            continue
        job = bodies.as_job(url, row)
        bucket, hard, soft = judge.judge(job)
        before = report.bucket_of(v.get("blocked", []), v.get("check", []))
        if before != bucket:
            moves.append((before, bucket, title, job.get("loc") or ""))
            # A row that changes section under you needs to say so, or the
            # page looks like it lost a job you were reading.
            v["moved_from"] = before
            v["moved_on"] = str(datetime.date.today())
        v["blocked"], v["check"] = hard, soft
        v["loc"] = job.get("loc") or ""
        v["home"] = bool(HOME.search(
            f'{title} {job.get("loc") or ""} {job.get("body") or ""}'))
        done += 1
    return seen, done, skipped


def rejudge_google(store, moves, dropped):
    if not GOOGLE.exists():
        return None, 0, 0
    rows = json.loads(GOOGLE.read_text())
    done = skipped = 0
    keep_rows = []
    for r in rows:
        row = store.get(r["url"])
        title = (row or {}).get("title") or r.get("title") or ""
        keep_rows.append(r)
        if not judge.keep(title) and not row:
            r["bucket"], r["hard"], r["soft"] = "notqa", [], [judge.rules.NOT_QA_REASON]
            dropped.append((r["url"], title))
            done += 1
            continue
        if not row:
            skipped += 1
            continue
        job = bodies.as_job(r["url"], row)
        bucket, hard, soft = judge.judge(job)
        if r.get("bucket") != bucket:
            moves.append((r.get("bucket", "?"), bucket, r.get("title", ""),
                          job.get("loc") or ""))
            r["moved_from"] = r.get("bucket", "")
            r["moved_on"] = str(datetime.date.today())
        r["bucket"], r["hard"], r["soft"] = bucket, hard, soft
        r["loc"] = job.get("loc") or ""
        r["home"] = bool(HOME.search(
            f'{r.get("title") or ""} {job.get("loc") or ""} '
            f'{job.get("body") or ""}'))
        done += 1
    return keep_rows, done, skipped


def fetch_missing(store, urls):
    """Read the postings the cache does not have yet."""
    todo = [u for u in urls if u not in store]
    if not todo:
        return 0, 0
    print(f"  reading {len(todo)} posting(s) not in the cache", file=sys.stderr)
    got = lost = 0
    for i, url in enumerate(todo, 1):
        job = judge.fetch(url)
        if job:
            bodies.put(store, url, job)
            got += 1
        else:
            lost += 1
        if i % 100 == 0:
            print(f"    {i}/{len(todo)}", file=sys.stderr)
            bodies.save(store)
    bodies.save(store)
    return got, lost


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry", action="store_true",
                    help="show the moves, write nothing")
    ap.add_argument("--fetch", action="store_true",
                    help="read any posting missing from the cache first")
    a = ap.parse_args()

    store = bodies.load()
    if a.fetch:
        urls = list(json.loads(BOARD.read_text())) if BOARD.exists() else []
        urls += [r["url"] for r in json.loads(GOOGLE.read_text())] if GOOGLE.exists() else []
        got, lost = fetch_missing(store, list(dict.fromkeys(urls)))
        print(f"  cached {got} more, {lost} could not be read")

    if not store:
        sys.exit("  bodies.json.gz is empty. Run a scan, or rejudge.py --fetch.")

    moves, dropped = [], []
    seen, b_done, b_skip = rejudge_board(store, moves, dropped)
    grows, g_done, g_skip = rejudge_google(store, moves, dropped)

    print(f"  re-judged {b_done} board rows, {g_done} Google rows")
    if b_skip or g_skip:
        print(f"  {b_skip + g_skip} kept their verdict: not in the cache yet")
    if dropped:
        print(f"  {len(dropped)} filed as not your kind of posting "
              f"(kept, not deleted):")
        for url, title in dropped[:8]:
            print(f"    {title[:70]}")
        if len(dropped) > 8:
            print(f"    ... {len(dropped) - 8} more")

    if moves:
        print(f"\n  {len(moves)} row(s) change bucket:")
        for (a_, b), n in collections.Counter(
                (m[0], m[1]) for m in moves).most_common():
            print(f"    {a_:>8} -> {b:<8} {n}")
    else:
        print("\n  no bucket changes")

    if a.dry:
        print("\n  --dry, nothing written")
        return

    if seen:
        storage.write_json(BOARD, seen, indent=1)
    if grows is not None:
        storage.write_json(GOOGLE, grows, indent=1)
    runlog.record("rejudge", ok=True, board=b_done, google=g_done,
                  moved=len(moves), dropped=len(dropped),
                  skipped=b_skip + g_skip)
    report.main()


if __name__ == "__main__":
    main()
