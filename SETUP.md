# Setup (instructions for Claude)

This kit starts empty. Your job: interview the user for every fact below, then fill `me/` from
their answers. Never invent or assume a fact they did not give you.

If they hand you a CV/resume (pasted text or a file), read it first and pre-fill your best
answer to each question below from it, then confirm every one with them instead of asking cold.
Say plainly which answers came from their file and which still need an answer. Either way, do
not proceed past the interview until every question below is answered or explicitly skipped.

## 1. Install

- Run `./setup.sh`. It copies `templates/me/` to `me/`, makes `me/.venv` with reportlab, and
  links the skill into `~/.claude/skills/job-fit`.
- Fix anything it prints as MISSING. Ask before installing software.

## 2. The interview

Ask in short batches, not all at once. Wait for real answers, do not guess a plausible one.

**About them**
- Full name, as it should appear on a CV.
- Email, phone (optional), city and country, LinkedIn, GitHub or portfolio, any other link
  worth showing.
- Languages spoken.
- Education: degree, school, dates, for each.

**Where and how they can work**
- Countries or regions they are legally authorized to work in (citizenship, residency, visa
  status). Be specific: "EU citizen", "needs sponsorship in the US", "Brazil only", etc.
- Remote-only, hybrid, or open to relocating.
- Time zone (IANA name, e.g. `Europe/Lisbon`, `America/Sao_Paulo`).
- Employment type: full-time, contract, or both.
- Minimum acceptable pay, or "not now".
- Any hard dealbreaker that should be an instant SKIP (e.g. "not fully remote").

**What they're looking for**
- Target role(s) and seniority, in their own words: "QA Engineer", "Senior Backend Engineer",
  "Product Marketing Manager". Do not normalize this into a title they did not say.
- Any adjacent title or level to explicitly avoid (e.g. "not team lead", "not a level down").
- How many focus CVs they want (2 to 6 is normal) and what each should emphasize.

**Their work history, the source of truth**
For each job, newest first:
- Employer, title, dates, location and remote status, employment type.
- One line on what the company does or sells.
- What they actually did: facts they can defend in an interview, not responsibilities copied
  from a job description.
- Tools and technologies used, confirmed only.
- Anything from the ad-reading world (a tool, a claim) they'd rather this role not have to prove.

**Odds and ends**
- Tools or skills recruiters often assume for this role, that they have never actually used
  (goes to `BANNED`, so no CV claims it by accident).
- Personal projects, publications or portfolio pieces worth citing, with links.
- An accent color for the CV, or "default".

## 3. Fill `me/`

Write the interview into, in this order:

1. `me/work-history.txt` — the source of truth, in the format the template shows. Every fact
   that will ever appear on a CV or in a fit score must be here first.
2. `me/profile.py` — `NAME`, `CONTACT`, `EDUCATION`, `SPEAKING`, `TOOLS`, `BANNED`, `ACCENT`,
   `JOBS`. Every fact here must also be in `work-history.txt`, worded the same way.
3. `me/preferences.md` — hard filter, where they can work, what they want, flags that are not
   kills.
4. `me/search.py` — `NAME`, `TIMEZONE`, `PORT`, `ROLE_NOUN`, `TARGET_LABEL`, `HOME_LABEL`,
   `ROLE_GATE`, `TARGET_TITLE`, `EXCLUDE_TITLES`, `HOME_PLACES`, `HOME_COUNTRY_CODES`,
   `GOOGLE_QUERIES`. Derive the regexes from the role and location answers above:
   - `ROLE_GATE` stays broad: every word that could plausibly name this kind of job.
   - `TARGET_TITLE` narrows `ROLE_GATE` down to the seniority they actually want.
   - `EXCLUDE_TITLES` names adjacent roles that share the gate's keywords but are the wrong
     job (for "QA Engineer", that includes things like "sales engineer" or "support engineer").
   - `HOME_PLACES` and `HOME_COUNTRY_CODES` come from where they can legally work.
   - Test every change with `python3 scan/rejudge.py --dry` before trusting it.
5. `me/cv-data/*.py` — one file per focus CV they asked for. Copy
   `templates/me/cv-data/example.py`, never edit the original, and never leave a bracketed
   placeholder in a file `cv/build.sh` will render.

## 4. Rebuild the CVs

- Run `cv/build.sh` until it prints `ALL GOOD`.
- Show them the PDFs in `me/cvs/`.
- Ask if a focus is missing or wrong. Change only `me/cv-data/*.py`.

## 5. Daily scan

- `me/search.py` is now set for their role and where they can work.
- Ask before the first run. Then run `me/.venv/bin/python scan/scan.py --slice` and
  `me/.venv/bin/python scan/report.py`, and open `me/scan/report.html`.
- Ask before installing the daily schedule: `scan/install-launchd.sh --load`.
- The Google step needs Claude Code with the Chrome extension connected. Skip it if they don't
  use Chrome.

## 6. Done

Tell them, in 3 lines:
- paste any job ad or link into Claude to get a verdict
- `cv/build.sh` rebuilds the CVs after a fact changes
- where the daily report opens
