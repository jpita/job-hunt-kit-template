# CV builder

One set of facts, many CVs. Every PDF prints the same work history, so the CVs never disagree.

    cv/build.sh                      rebuild every CV in me/cv-data and check them
    me/.venv/bin/python cv/render.py /tmp/x.py   build one throwaway CV, no checks
    me/.venv/bin/python cv/letter.py /tmp/l.py   build one cover letter

`setup.sh` installs reportlab in `me/.venv`. `pdftotext` comes from `brew install poppler`.
Run the scripts with `me/.venv/bin/python`. `build.sh` does this for you.
PDFs land in `me/cvs/`.

## Where to edit what

| Change | File |
|---|---|
| Name, contact, education, speaking, jobs, dates, older job bullets, tools row, banned tools | `me/profile.py` |
| Role line, tagline, summary, skills, current job bullets | one `me/cv-data/*.py` |
| Layout, fonts, colours | `cv/cvlib.py` |

## Focus CVs, not one CV per job ad

- Keep 3 to 6 focus CVs, one per kind of role you apply to. Example: `Senior Backend`, `Engineering Manager`, `Data Platform`.
- For one posting, first check if a focus CV already fits. It usually does.
- Make a posting CV only when no focus CV fits. Copy the closest one to `/tmp`, edit, `render.py`, delete the data file.
- A posting CV only rewords what a focus CV says. A new fact goes into `work-history.txt` and a focus CV first.
- A throwaway CV you send twice is a focus CV. Give it a data file in `me/cv-data/`.
- Never edit a focus CV to fit one posting.

## Rules the build enforces

- One claim, one place. The same 6-word phrase twice on a CV fails the build. The summary positions, the bullets prove, the skills list.
- No banned tool. Add a tool to `BANNED` in `me/profile.py` the first time it gets onto a CV by mistake.
- No em or en dashes.
- 1 or 2 pages. 3 fails. A page 2 with fewer than 6 lines is flagged. Fix it with content, not smaller type.
- An override equal to the default fails. Delete it.

## Rules the build cannot enforce

- Never add a tool because an ad lists it. You must be able to talk about it in an interview.
- Count years honestly. 8 months is not "2+ years".
- Match the level of the ad. Lead-level content on a mid-level role reads as overqualified.
- Put the ad's must-haves in the first three SKILLS rows, in the ad's words where true.
- Keep the job row one line: `Role · Employer · Dates`. Check with `pdftotext file.pdf - | head -30`.
- The contact line ends with a real city and country. Nothing after it. A trailing language list got parsed as the location.
- PDF names: 25 characters or less. Focus CV: `Senior Backend.pdf`. Posting CV: `Acme Backend.pdf`. Letter: `Cover Acme.pdf`.

## Cover letters

Only when asked. 250 to 400 words. Check with `pdftotext "Cover X.pdf" - | wc -w`.

- You are asking them. Never imply you have other options.
- Do not summarise the CV. Say why this company, what you want, how you work.
- Open plainly: "I would like to apply for the X role."
- One reason you want them that another company could not claim.
- Show one concrete result. No "proven track record".
- Do not volunteer gaps.
- Close by asking: "I would be glad to talk if you think it is worth a conversation."
- Every fact is in `work-history.txt`.
