# Job hunt kit

A Claude Code setup for your remote job search. Any role, any location you can legally work from.

- **job-fit skill**: paste a job ad or link. Claude researches the company, scores your fit against your real history, and gives GO / GO WITH CAVEATS / SKIP.
- **CV builder**: one file of facts, a few focus CVs, ATS-safe PDFs, and a check that fails on repeated claims or tools you never used.
- **Daily scan**: reads public Greenhouse, Lever and Ashby job boards every morning, and Google through your Chrome. Ranks matches in a local report page.

## Start

Clone it, open Claude Code in the folder, and say:

    Read SETUP.md and set me up.

Nothing is filled in. Claude interviews you: your role, your location and work rights, your full work history, what you want and what you don't. Have a CV/resume on hand (paste it, or point Claude at the file) and it will pre-fill answers from it for you to confirm, instead of asking everything cold.

## Layout

| Folder | Holds | Shared |
|---|---|---|
| `skills/job-fit/` | the skill | yes |
| `cv/` | CV and letter builder | yes |
| `scan/` | daily scanner | yes |
| `templates/me/` | the blank starting profile | yes |
| `me/` | your data, CVs, scan state | no, gitignored |
| `evals/` | generic classification eval template and aggregate model results | yes |

Updates: `git pull`. Your `me/` folder is never touched.

## Privacy

Your real name, history and CVs live only in `me/`, which is gitignored: they never get committed to this repo. This kit's own rules (`CLAUDE.md`) tell Claude never to make your job search public: no posts, no public repos naming a company you apply to. If you keep your fork of this kit for your own search, keep that fork private.

## Agent evaluations

[Compare historical model results](evals/BENCHMARKS.md) for duration, token usage, output validity and cost estimates. The [eval template](evals/README.md) accepts your own policy and fixtures; its public example uses synthetic support tickets. Private source postings and candidate rules are not published.
