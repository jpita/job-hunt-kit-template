"""Loads the personal settings from me/search.py and gives the state folder.

Everything personal lives in me/ at the repo root, which git ignores.
Set JOBKIT_ME to use another folder, for example in a test.
"""
import importlib.util
import os
import pathlib
import re
import shutil
import sys

REPO = pathlib.Path(__file__).resolve().parent.parent
ME = pathlib.Path(os.environ.get("JOBKIT_ME") or REPO / "me")
FILE = ME / "search.py"

if not FILE.exists():
    sys.exit(f"{FILE} not found. Run setup: copy templates/me to me/ "
             "(cp -R templates/me me), then edit me/search.py.")

_spec = importlib.util.spec_from_file_location("search", FILE)
S = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(S)

# State and output. Nothing personal is written inside scan/.
STATE = ME / "scan"
STATE.mkdir(parents=True, exist_ok=True)

# The board list the scanner appends to. Seeded once from the shared list.
COMPANIES = STATE / "companies.txt"
if not COMPANIES.exists():
    shutil.copy(pathlib.Path(__file__).parent / "companies.txt", COMPANIES)

NAME = S.NAME
TIMEZONE = S.TIMEZONE
PORT = S.PORT
ROLE_NOUN = S.ROLE_NOUN
TARGET_LABEL = S.TARGET_LABEL
HOME_LABEL = S.HOME_LABEL
GOOGLE_QUERIES = S.GOOGLE_QUERIES

TARGET_TITLE = re.compile(S.TARGET_TITLE, re.I)
ROLE_GATE = re.compile(S.ROLE_GATE, re.I)
EXCLUDE_TITLES = re.compile(S.EXCLUDE_TITLES, re.I)
LOWER_LEVEL = re.compile(S.LOWER_LEVEL, re.I)
# Places you can work from, plus the words that mean "anywhere".
ANYWHERE = (r"worldwide|global|globally|anywhere|any country|any location|"
            r"international|multiple countries")
GEO_OK = re.compile(r"\b(" + S.HOME_PLACES + "|" + ANYWHERE + r")\b", re.I)
HOME = re.compile(r"\b(" + S.HOME_PLACES + r")\b", re.I)
HOME_OR_ANYWHERE = re.compile(
    r"\b(" + S.HOME_PLACES + "|" + ANYWHERE + r")\b", re.I)
ISO_OK = {c.upper() for c in S.HOME_COUNTRY_CODES}
