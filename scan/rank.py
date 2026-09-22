#!/usr/bin/env python3
"""Order the rows inside a bucket, best first.

Bucketing answers "can you apply". This answers "which one first", and they
are different questions. A twelve-year-old evergreen posting and one from
this morning both sit in Clean.

Reads only what the seen files store, so it needs no network and no cache.
"""
import datetime, re

import config

import rules

# A posting stops being a real opening long before it is taken down. Full
# score for the first week, nothing after four months.
FRESH_DAYS, STALE_DAYS = 7, 120

WORLDWIDE = re.compile(
    r"\b(worldwide|global|globally|anywhere|any country|any location|"
    r"international)\b", re.I)
HOME = config.HOME


def age_days(row, today=None):
    """Days since publication, or None when the board did not say."""
    p = row.get("posted") or ""
    try:
        return ((today or datetime.date.today())
                - datetime.date.fromisoformat(p[:10])).days
    except (ValueError, TypeError):
        return None


def score(row, today=None):
    """0 to 100, and the reasons, best first. Higher is worth reading sooner."""
    points, why = 0, []

    age = age_days(row, today)
    if age is None:
        points += 8
        why.append("no publication date")
    elif age <= FRESH_DAYS:
        points += 40
        why.append("posted this week" if age else "posted today")
    elif age >= STALE_DAYS:
        why.append(f"{age} days old")
    else:
        span = STALE_DAYS - FRESH_DAYS
        points += int(40 * (STALE_DAYS - age) / span)
        why.append(f"{age} days old")

    text = f'{row.get("title") or ""} {row.get("loc") or ""}'
    # The stored home flag also matches "worldwide" and "anywhere", so it
    # cannot carry the home claim on its own.
    if HOME.search(text):
        points += 25
        why.append(f"names {config.HOME_LABEL}")
    elif WORLDWIDE.search(text) or row.get("home"):
        points += 18
        why.append("open worldwide")
    elif rules.BARE_REMOTE.match((row.get("loc") or "").strip()):
        points += 10
        why.append("remote, no country named")

    title = row.get("title") or ""
    if rules.TITLE_OK.search(title):
        points += 20
        why.append("staff-level title")
    elif rules.LEVEL_REASON in (row.get("soft") or []):
        why.append("a level down")

    if row.get("pay"):
        points += 7
        why.append("pay disclosed")

    # Your own verdict outranks every rule.
    if row.get("mark") == "good":
        points += 30
        why.append("you marked it good")
    elif row.get("mark") == "bad":
        points -= 40
        why.append("you marked it no")

    return max(0, min(100, points)), why


def sort_key(row, today=None):
    """Best first, then the newest sighting, then the company, so the order
    never depends on dict insertion."""
    return (-score(row, today)[0], row.get("first_seen") or "",
            row.get("company") or "")
