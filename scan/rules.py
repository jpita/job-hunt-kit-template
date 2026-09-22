#!/usr/bin/env python3
"""The rules that judge one posting: is it the right role, and can you work there.

Kept apart from the scanners so there is one source of truth. google_scan.py
imports this. It has no network calls and no state.
"""
import re, html

import config

# Your role and level. The patterns live in me/search.py.
TITLE_OK = config.TARGET_TITLE

# The only gate. A posting that matches none of these is not your kind of job.
# Everything past this point is judged and shown, never dropped.
# Keep generic words (like "automation" or "engineer") out of it, or unrelated
# jobs flood the "Worth a glance" list.
TITLE_RELEVANT = config.ROLE_GATE

TITLE_WEAK = config.EXCLUDE_TITLES

# Right kind of work, lower down. These go to "One level down", not to
# "Wrong kind of role".
BELOW_LEVEL = config.LOWER_LEVEL

# Placeholder postings, not jobs. Boards carry templates and test fixtures of
# their own, and they match every keyword a real posting does.
TITLE_JUNK = re.compile(
    r"\btest job\b|\[template\]|\btest role\b|req\s*#|uat-req|"
    r"-\s*test\s*$|\btest\s+\d+\s*$|-test-\d+", re.I)


# Soft reasons split in two. A logistics doubt is worth a glance: the role is
# right and only the arrangement is unclear. A role doubt is not: the job is
# the wrong kind of work, so it belongs in its own list.
# One bucket for all soft reasons buried the real rows under wrong-role rows.
NOT_QA_REASON = f"not a {config.ROLE_NOUN} at all"
LEVEL_REASON = f"title is not a {config.TARGET_LABEL}"
WRONG_ROLE_REASON = "title may not be a software role"


def title_bucket(soft):
    """Which list a row belongs in, given its soft reasons.

    "" means the soft reasons are all logistics, so it is worth a glance.
    """
    if NOT_QA_REASON in soft:
        return "notqa"
    if WRONG_ROLE_REASON in soft:
        return "role"
    if LEVEL_REASON in soft:
        return "level"
    return ""

# ---------------------------------------------------------------- geography
# Allowlist, not a blocklist. A posting must name a place you can work from.
# Your places come from HOME_PLACES in me/search.py.
GEO_OK = config.GEO_OK

# "Remote - United States" is a hiring policy, not a physical requirement.
# A remote-first company that files a role under one country is worth one
# question, so it goes to Worth a glance rather than out.
# An office address like "Bangalore, India" is not the same thing.
# An explicit "US only" or "must reside in the United States" is still hard:
# those live in HARD and this does not touch them.
REMOTE_SCOPED = re.compile(
    r"^\s*(?:fully\s+)?remote\s*[-\u2013\u2014,|/]\s*(\S.*)$"
    r"|^(\S.*?)\s*[-\u2013\u2014,|/]\s*(?:fully\s+)?remote\s*$", re.I)

# An "anywhere" word only counts when a hiring or remote phrase sits beside
# it. On its own it is usually company blurb or a job title, and it was
# silently clearing real office locations.
# A blurb like "a global team" once cleared real office roles.
HIRING_NEAR = re.compile(
    r"work(?:ing)?\s+(?:from|remotely)|fully\s+remote|100%\s+remote|"
    r"remote(?:[- ]first)?\s+(?:position|role|job|opportunity)|"
    r"hir(?:e|ed|ing)|eligib|"
    r"open\s+to\s+(?:candidates|applicants)|"
    # "candidates" and "applicants" are hiring words. "employees" is not:
    # "1,000+ employees in more than 20 countries ... global impact" is a
    # company-size boast, and it cleared a Bangalore office role.
    r"(?:candidates|applicants)\s+(?:in|from|located|based)", re.I)
NEAR = 80


# "anywhere in North America" is a hiring statement and a restriction at the
# same time.
SCOPED_TO = re.compile(
    r"\s*(?:in|within|across|throughout)\s+(?:the\s+)?"
    r"([A-Za-z][A-Za-z .&-]{2,28})", re.I)


def says_anywhere(text, limit=2000):
    """True only when an "anywhere" word has a hiring phrase next to it and
    is not immediately scoped to a place you cannot work from."""
    text = text or ""
    for m in GEO_OK.finditer(text[:limit]):
        if not HIRING_NEAR.search(text[max(0, m.start() - NEAR):m.end() + NEAR]):
            continue
        scope = SCOPED_TO.match(text, m.end())
        if scope:
            place = scope.group(1).strip().rstrip(".,")
            if not GEO_OK.search(place) and (COUNTRY_RX.search(place)
                                             or PLACE_RX.search(place)):
                continue
        return True
    return False


# A bare "Remote" with no country attached is fine. "Remote - US" is not.
BARE_REMOTE = re.compile(r"^[\s,\-|/]*(fully\s+)?remote[\s,\-|/]*$", re.I)

COUNTRIES = (
    r"united states|usa|u\.s\.a?|us|america|canada|mexico|united kingdom|uk|"
    r"england|scotland|wales|ireland|france|germany|deutschland|spain|portugal|"
    r"italy|netherlands|holland|belgium|luxembourg|switzerland|austria|poland|"
    r"czechia|czech republic|slovakia|hungary|romania|bulgaria|greece|turkey|"
    r"ukraine|serbia|croatia|denmark|sweden|norway|finland|iceland|estonia|"
    r"latvia|lithuania|india|pakistan|bangladesh|sri lanka|china|hong kong|"
    r"taiwan|japan|tokyo|korea|singapore|malaysia|indonesia|thailand|vietnam|"
    r"philippines|australia|new zealand|israel|uae|emirates|saudi arabia|qatar|"
    r"egypt|nigeria|kenya|south africa|morocco|colombia|argentina|chile|"
    r"emea|apac|namer|eu|europe|north america|asia|africa|middle east|"
    r"benelux|nordics|dach"
)
COUNTRY_RX = re.compile(r"(?<![A-Za-z])(" + COUNTRIES + r")(?![A-Za-z])", re.I)

# A named city or US state is just as restrictive as a country.
PLACES = (
    r"bangalore|bengaluru|hyderabad|pune|chennai|mumbai|delhi|gurgaon|noida|"
    r"san francisco|santa clara|san jose|palo alto|mountain view|sunnyvale|"
    r"seattle|austin|atlanta|boston|chicago|denver|new york|nyc|brooklyn|"
    r"los angeles|san diego|dallas|houston|miami|phoenix|portland|"
    r"toronto|vancouver|montreal|ottawa|london|dublin|berlin|munich|hamburg|"
    r"paris|amsterdam|madrid|barcelona|lisbon|milan|rome|zurich|geneva|"
    r"stockholm|oslo|copenhagen|helsinki|warsaw|krakow|prague|budapest|"
    r"bucharest|belgrade|kyiv|tel aviv|dubai|riyadh|sydney|melbourne|"
    r"auckland|tokyo|osaka|seoul|shanghai|beijing|shenzhen|bangkok|manila|"
    r"jakarta|kuala lumpur|ho chi minh|hanoi|lagos|nairobi|cairo|cape town|"
    r"alabama|alaska|arizona|arkansas|california|colorado|connecticut|"
    r"delaware|florida|georgia|hawaii|idaho|illinois|indiana|iowa|kansas|"
    r"kentucky|louisiana|maine|maryland|massachusetts|michigan|minnesota|"
    r"mississippi|missouri|montana|nebraska|nevada|new hampshire|new jersey|"
    r"new mexico|north carolina|north dakota|ohio|oklahoma|oregon|"
    r"pennsylvania|rhode island|south carolina|south dakota|tennessee|texas|"
    r"utah|vermont|virginia|washington|west virginia|wisconsin|wyoming"
)
PLACE_RX = re.compile(r"(?<![A-Za-z])(" + PLACES + r")(?![A-Za-z])", re.I)

# "Irvine, CA" / "Pittsburgh, PA" / "KOHO (CAN)" / "Espoo, FI" all pin a place.
CODE_RX = re.compile(r",\s*[A-Z]{2,3}\b|\(\s*[A-Z]{2,3}\s*\)")

# ISO alpha-2 codes the boards hand back directly. Only these are acceptable.
ISO_OK = config.ISO_OK

BASED_IN = re.compile(
    r"(?:based|located|residing|reside|living|hired|employed)\s+(?:in|within)\s+"
    r"(?:the\s+)?([A-Za-z][A-Za-z .&-]{2,30})", re.I)

# A US pay disclosure names the US without restricting hiring to it.
PAY_CONTEXT = re.compile(
    r"pay range|salary range|salary|compensation|annual pay|pay band|"
    r"remunerat|pay scale|pay transparency", re.I)

# A location that names no place at all is a remote signal by itself. Your
# home country is not: it is somewhere you can work, a different question.
REMOTE_LOC = re.compile(
    r"\b(worldwide|global|globally|anywhere|any country|any location|"
    r"international|multiple countries)\b", re.I)


def geo_verdict(loc, country, body, title="", remote=False):
    """Return (hard, soft) reasons for the geography of one posting.

    A posting that says it is open anywhere wins over its office location.
    """
    hard, soft = [], []
    loc = (loc or "").strip()

    # The board's own country code is authoritative and beats any wording.
    # A body that says "global" while the posting is filed under country FR is
    # still an FR job.
    if country and country.upper() not in ISO_OK:
        return [f"board says country {country.upper()}"], soft

    # A title that says it is open anywhere outranks the office address.
    if says_anywhere(title, 200):
        return hard, soft

    # An allowlist means an unrecognised location is a place you cannot work
    # from, not a doubt. Only a bare "Remote" or a GEO_OK word gets past.
    names_a_place = bool(COUNTRY_RX.search(loc) or PLACE_RX.search(loc)
                         or CODE_RX.search(loc))

    # The body is weaker than the board's own location field. "A globally
    # distributed team" is about your sofa, not your country.
    if says_anywhere(body) and not names_a_place:
        return hard, soft

    if loc and not GEO_OK.search(loc) and not BARE_REMOTE.match(loc):
        m = REMOTE_SCOPED.match(loc)
        if m:
            where = (m.group(1) or m.group(2) or "").strip()
            soft.append(f"remote, but hiring is scoped to {where}"[:90])
            return hard, soft
        # A remote role whose location names only a country is scoped by
        # policy. A named city or state is an address, and stays hard even
        # when the posting calls itself remote.
        if remote and COUNTRY_RX.search(loc) and not (
                PLACE_RX.search(loc) or CODE_RX.search(loc)):
            soft.append(f"remote, but hiring is scoped to {loc}"[:90])
            return hard, soft
        return [f"location: {loc}"], soft

    for m in BASED_IN.finditer(body or ""):
        place = m.group(1).strip().rstrip(".,")
        if GEO_OK.search(place):
            continue
        if PAY_CONTEXT.search((body or "")[max(0, m.start() - 140):m.start()]):
            continue
        if COUNTRY_RX.search(place):
            return [f"body says based in {place}"], soft
    return hard, soft

# HARD: legally or physically impossible. These are the only ones that drop a role.
# "available in the following states: AZ, CA, CO, FL, ..." is US-only said
# without the words "US only". Three or more state codes in a row is the tell.
US_STATES = ("AL|AK|AZ|AR|CA|CO|CT|DE|FL|GA|HI|ID|IL|IN|IA|KS|KY|LA|ME|MD|MA|"
             "MI|MN|MS|MO|MT|NE|NV|NH|NJ|NM|NY|NC|ND|OH|OK|OR|PA|RI|SC|SD|TN|"
             "TX|UT|VT|VA|WA|WV|WI|WY|DC")
STATE_LIST = re.compile(
    r"(?<![A-Za-z])(?:" + US_STATES + r")(?:\s*,\s*(?:" + US_STATES + r")){2,}"
    r"(?![A-Za-z])")

HARD = [
    ("US persons only", re.compile(r"u\.?s\.?\s+persons?|citizens? or lawful permanent|green card holder", re.I)),
    ("US work authorization", re.compile(r"authoriz(ed|ation) to work in the (united states|u\.?s)", re.I)),
    ("security clearance", re.compile(r"security clearance|ITAR|critical infrastructure protection", re.I)),
    ("US only", re.compile(r"\bUS[- ]only\b|\bU\.S\. only\b|must (be located|reside) in the (united states|us)\b", re.I)),
    ("hiring only in named US states", STATE_LIST),
]

# SOFT: probably wrong, but cheap to check. These demote to "maybe", never drop.
HYBRID = re.compile(r"\bhybrid\b|\bon[- ]site\b|days? (per|a) week in (the )?office", re.I)
SOFT = [("mentions hybrid or on-site", HYBRID)]
REMOTE = re.compile(r"\bremote\b|\bdistributed\b|work from anywhere", re.I)
# In a location or a title, the bare word is enough. In body prose it is not:
# "distributed across the globe with hubs in Bengaluru" is a description of
# the company, and it was cancelling the hybrid flag on an office role.
REMOTE_BODY = re.compile(
    r"work(?:ing)?\s+(?:from\s+(?:home|anywhere)|remotely)|"
    r"fully\s+remote|100%\s+remote|remote[- ]first|"
    r"remote\s+(?:position|role|job|opportunity|work)|"
    r"this\s+(?:role|position)\s+is\s+remote", re.I)

def strip(h):
    """Plain text out of a board's HTML description."""
    return html.unescape(re.sub(r"<[^>]+>", " ", h or ""))


# ---------------------------------------------------------------- pay
# Ashby hands back a formatted string. Greenhouse and Lever usually do not, so
# the range has to come out of the body text when it is there at all.
_CUR = r"(?:\$|US\$|USD|R\$|BRL|€|EUR|£|GBP|CA\$|CAD|A\$)"
_AMT = r"\d{1,3}(?:[.,]\d{3})+(?:[.,]\d{2})?|\d{2,3}(?:[.,]\d)?\s?[kK]\b|\d{4,7}"
SALARY_RANGE = re.compile(
    r"(" + _CUR + r")\s?(" + _AMT + r")"
    r"(?:"
    # a dash or "to" may drop the second symbol
    r"\s?(?:-|\u2013|\u2014)\s?(" + _CUR + r")?\s?"
    r"|\s(?:to|through)\s(" + _CUR + r")?\s?"
    # Portuguese "a" must keep it, or "1,000 a lot of things" reads as a range
    r"|\s(?:a|ate|at\u00e9)\s(" + _CUR + r")\s?"
    r")"
    r"(" + _AMT + r")", re.I)
# A lone figure is only pay when a pay word sits just before it. Otherwise a
# referral bonus or a customer figure reads as a salary.
_PAY_WORD = (r"salary|salaries|compensation|base pay|base salary|pay range|"
             r"pay band|annual|annually|per year|per annum|/yr|OTE|remunera|"
             r"sal\u00e1rio|remunera\u00e7\u00e3o")
SALARY_ONE = re.compile(
    r"(?:" + _PAY_WORD + r")[^.\n]{0,60}?(" + _CUR + r")\s?(" + _AMT + r")", re.I)
# "$0 - $0" and similar placeholders are noise, and so is a lone tiny number.
_JUNK_PAY = re.compile(r"^\D*0\D*(?:-|\u2013|to)\D*0\D*$", re.I)


def salary(structured="", body=""):
    """A short pay string, or "". Structured value wins; body text is fallback."""
    if structured and structured.strip():
        return re.sub(r"\s+", " ", structured).strip()[:60]
    text = body or ""
    m = SALARY_RANGE.search(text)
    if m:
        cur, lo = m.group(1), m.group(2)
        cur2 = m.group(3) or m.group(4) or m.group(5) or cur
        out = f"{cur}{lo} - {cur2}{m.group(6)}"
    else:
        m = SALARY_ONE.search(text)
        if not m:
            return ""
        out = f"{m.group(1)}{m.group(2)}"
    out = re.sub(r"\s+", " ", out).strip()
    return "" if _JUNK_PAY.match(out) else out[:60]
