---
name: job-fit
description: Judge whether a job posting is worth applying to, then build the tailored CV only after the user says go. Use this whenever the user pastes a job description, a job link (LinkedIn, Wellfound, Otta, Ashby, Greenhouse, Lever, a careers page), a recruiter message, or a referral link, even with no instruction. Also use it for "is this one worth it", "should I apply", "check this company", "make a CV for this", or "write a cover letter for this". A pasted posting with no instruction means: research the company, score the fit, give a verdict, and wait. Do not start a CV before the verdict is on screen.
---

# Job fit

A pasted posting is a question: "is this worth my time". Answer it before any CV work.

## Find the kit

The kit root is two folders above this file. Resolve the symlink:

    KIT="$(cd "$(dirname "$(readlink -f ~/.claude/skills/job-fit/SKILL.md)")/../.." && pwd)"

Personal files, all in `$KIT/me/`:
- `preferences.md`: hard filter, location, timezone, roles wanted.
- `work-history.txt`: the source of truth for what the user did.
- `profile.py`, `cv-data/*.py`: CV facts and focus CVs.
- `job-log.md`: every past verdict.

Re-read each file in the same turn you use it. Never score from memory.

## Half one: decide

### 1. Get the posting text

- Pasted text is the posting.
- For a link, load `WebFetch` via `ToolSearch` and fetch it.
- If the fetch has no requirements section (login wall, empty shell), say so and ask for the text. Never guess.

Pull out, and say which the ad does not state:
- employment type and duration
- remote, hybrid or on-site, and which countries or time zones
- hours and required overlap
- level and years asked for
- pay and currency
- the interview process

### 2. Check the log

Search `job-log.md` for the company. If found, open the report with "You looked at this on <date> and decided <verdict>".

### 3. Hard filter

Apply the hard filter from `preferences.md`. If it fails, stop. Quote the line of the ad. Do no research.
Everything else is a flag, not a stop.

### 4. Research the company

Read `references/company-research.md`. Every company claim carries its source link in the same line.

### 5. Score the fit

Read `work-history.txt` now. Put each requirement in one bucket:

| Call | Means |
|---|---|
| **Strong** | A named job did this, and work-history.txt says so. |
| **Partial** | Real but smaller: less time, a side of another job, or a personal project. |
| **Gap** | Not done, nothing close. |
| **Cannot claim** | A banned tool, or marked NOT confirmed in work-history.txt. |

- A keyword match is never a claim. An interviewer's follow-up on a tool never used costs more than the missing keyword.
- Count years honestly. A job that started 8 months ago is 8 months, not "2+ years".

### 6. Verdict

Lead with one of:
- **GO**: clears the real requirements, company checks out.
- **GO WITH CAVEATS**: name the one problem in the same sentence.
- **SKIP**: name the one deciding reason.

Pick a side. The table carries the nuance.

### Report format

```
## <Company> - <Role>
Remote <yes/no> · <type, duration> · <countries> · <hours + overlap> · Comp: <found, or "not stated">

**<VERDICT>** - one sentence why.

**Company**
- 3 to 5 lines, each with its source link.

**Fit**
| Ask | Evidence | Call |
|---|---|---|

**Cannot claim** - tools and claims to keep off the CV.
```

Then append one line to `job-log.md` (newest first) and stop. No CV yet.

## Half two: after the user says go

### Check the focus CVs first

List `me/cv-data/*.py`. Read the closest one or two. Ask: would a recruiter find the ad's asks in the first 15 lines (role, tagline, top 3 skills rows)? If yes, name that PDF in `me/cvs/` and stop. This is the common case.

Make a new CV only when:
- the level differs from every focus CV
- the ad's core sits across two or more focus CVs
- a real must-have is missing from the closest CV
- the domain matters and no focus CV speaks to it

Never edit a focus CV to fit one posting.

### If a new one is needed, show the plan first

- which focus file gets copied, and why none fits
- the ROLE and TAGLINE
- the summary angle in one sentence
- the SKILLS row order
- which gaps get named

Wait for OK. Then follow `references/cv-build.md`.

## What this kit is tuned for

Read `me/preferences.md` and `me/work-history.txt` fresh, every time. This kit has no fixed
role, level or country of its own: whatever those two files say at the moment you score a
posting is the bar. A US-only or UK-only "remote" role is a flag when it excludes a place in
`me/preferences.md`: check if they hire contractors there before ruling it out.

## Things that go wrong

- **Leading senior on a role a level down.** Reads as overqualified. Match the pitch to the ad.
- **An intermediary is not the employer.** Who signs the contract, who you report to, whose product you build: answer all three.
- **The wish list is not the bar.** A missing nice-to-have is not a skip. A missing core must-have is.
- **The process is a decision input.** Rounds, take-home length: put them in the header.
- **Nothing goes public.** No posts, no public repos naming a company the user applies to.
