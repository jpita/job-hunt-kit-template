# Job hunt kit

A Claude Code setup for your remote job search. Any role, any location you can legally work from.

- **job-fit skill**: paste a job ad or link. Claude researches the company, scores your fit against your real history, and gives GO / GO WITH CAVEATS / SKIP.
- **CV builder**: one file of facts, a few focus CVs, ATS-safe PDFs, and a check that fails on repeated claims or tools you never used.
- **Daily scan**: reads public Greenhouse, Lever and Ashby job boards every morning, and Google through your Chrome. Ranks matches in a local report page.

<!-- BEGIN GENERATED EVAL RESULTS -->

## Agent evaluations

These experiments tested whether command-line AI agents could assign documents to predefined categories, follow a classification policy and cite supporting text. The table contains 16 recorded results across eight model IDs, measured 8-9 October 2026.

Each row summarizes one agent configuration. Most configurations classified ten documents; batch tests classified eight, and compatibility checks classified one. The source documents and personal policy are private. The reusable [eval template](evals/README.md) includes a separate synthetic support-ticket dataset; the scores below were not measured on that example.

**Reading the table:** Reasoning is the requested level of model deliberation. Category matches compares answers with predefined expected labels. Valid answers passed the experiment's response-format and evidence checks. A score of 10/10 means ten out of ten documents. Time, tokens and cost are totals for the row.

Compare configurations using the same experiment and reasoning setting. The experiments used different prompts and grading rules; the tools also supplied different system instructions, cache behavior and internal model calls. This measures complete agent workflows, rather than model performance in isolation.

| Experiment | Agent / model | Reasoning | Category matches | Valid answers | Total time (s) | Input tokens | Output tokens | Estimated cost (USD) |
|---|---|---|---:|---:|---:|---:|---:|---|
| Evidence references | Codex / `gpt-6-luna` | high | 10/10 | 10/10 | 102.450 | 156,574 | 2,393 | unknown |
| Evidence references | Claude Code / `claude-haiku-5-5` | high | 10/10 | 10/10 | 73.144 | 164,733 | 12,765 | $0.428039 (CLI estimate) |
| Verified request settings | Kimi Code / `kimi-k3` | low | 10/10 | 10/10 | 89.153 | 49,354 | 1,734 | $0.146424 (rate estimate) |
| Verified request settings | Reasonix / `deepseek-v4-pro` | low | 10/10 | 10/10 | 212.863 | 69,067 | 12,873 | $0.058333 (rate estimate) |
| Custom prompt | Codex / `gpt-6-luna` | low | 10/10 | 10/10 | 76.604 | 146,605 | 877 | unknown |
| Custom prompt | Claude Code / `claude-haiku-5-5` | low | 10/10 | 10/10 | 42.657 | 45,024 | 5,473 | $0.231446 (CLI estimate) |
| Custom prompt | Codex / `gpt-6-luna` | high | 10/10 | 10/10 | 98.596 | 145,231 | 2,958 | unknown |
| Custom prompt | Claude Code / `claude-haiku-5-5` | high | 10/10 | 10/10 | 50.889 | 45,024 | 7,419 | $0.221209 (CLI estimate) |
| Supporting quotations | Codex / `gpt-6-luna` | high | 5/10 | 5/10 | 100.171 | 153,303 | 2,622 | unknown |
| Supporting quotations | Claude Code / `claude-haiku-5-5` | high | 9/10 | 10/10 | 82.401 | 160,385 | 16,055 | $0.444193 (CLI estimate) |
| Batch classification | codex / `gpt-6-luna` | low | 8/8 | not scored | 51.965 | 32,482 | 611 | $0.003554 (unverified legacy estimate) |
| Batch classification | claude / `claude-haiku-4-5-20251001` | unsupported; extended thinking disabled | 8/8 | not scored | 14.508 | 11,355 | 1,094 | $0.028174 (CLI estimate) |
| Single-document check | Kimi Code / `kimi-k2.7-code` | default (not set) | 1/1 | 1/1 | 19.640 | 25,561 | 1,121 | unknown |
| Single-document check | Reasonix / `deepseek-v4-flash` | default (not set) | 1/1 | 1/1 | 7.414 | 11,415 | 1,014 | $0.002990 (CLI estimate) |
| Single-document check | Grok Build / `grok-4.7` | default (not set) | 1/1 | 1/1 | 12.296 | 28,168 | 635 | $0.058418 (CLI estimate) |
| Single-document check | Copilot Auto / `gpt-6-luna` | default (not set) | 1/1 | 1/1 | 13.106 | 7,110 | 213 | 1 premium request; USD unknown |

Tokens are the provider-reported units of input and generated text, including the agent tool's own instructions and internal calls. A CLI estimate is reported by the command-line tool; a rate estimate applies published token prices to recorded usage. Neither is a settled bill. Unknown subscription costs do not mean the service is free. Copilot reported a premium-request unit rather than dollars.

**Correct answers still need a reliable integration.** DeepSeek Pro produced ten valid, correctly categorized answers, but its command-line tool reported successful completion for only four. Flash produced a correct answer but reported failure and included extra prose. The batch Haiku test matched category labels but included unsupported evidence. The quotation experiment counted a category match only after evidence validation. The detailed report explains these grading differences and the remaining limitations.

[Full results, cache/reasoning tokens and methodology](evals/BENCHMARKS.md) · [Reusable eval template](evals/README.md)

<!-- END GENERATED EVAL RESULTS -->

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
