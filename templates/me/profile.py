# Your fixed facts. Every CV prints these the same way.
# Change a fact here, then run cv/build.sh. Never change it inside one CV.
# Every fact here must also be in work-history.txt. No em or en dashes.
#
# Filled in during setup, from the interview in SETUP.md. Leave nothing here
# that you cannot defend in an interview.

NAME = ""

# Must end with a real city and country.
CONTACT = ""

EDUCATION = ""

# Languages spoken, or "" to omit the SPEAKING line entirely.
SPEAKING = ""

TOOLS = ""

# Tools or claims that must never appear on a CV, even if an ad lists them.
BANNED = []

# Hex color for the CV's accent: role line, section headers, the rule under the name.
ACCENT = "#00695C"

# Newest first. The first job is tailored per focus CV (CURRENT in cv-data/*.py).
# One dict per employer:
#   {"key": "employer-key", "title": "Your Title", "company": "Employer &middot; Location, type",
#    "dates": "Mon YYYY - Mon YYYY", "bullets": ["...", "..."]}
JOBS = []
