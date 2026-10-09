# Historical agent evaluation results

Measured 8-9 October 2026. Sixteen aggregate rows cover eight distinct model IDs.

These results came from a private text-classification suite. Source texts, URLs, expected categories and personal policy are withheld. The public support-ticket example is a separate, new suite: these numbers are not its results and cannot be reproduced from it.

Each table is a separate cohort. Do not rank across tables: prompts, output contracts and scoring changed. Even within a cohort, native CLI system context, tokenizers, cache state and internal orchestration differed. These are workflow measurements, not intrinsic model efficiency benchmarks. Ten selected cases in one pass do not establish a production error rate.

Time is the sum of per-case wall durations (two batch durations for the exploratory cohort), not total experiment elapsed time. Tokens include native agent overhead. Reasoning tokens are a subset of output; do not add them twice. Input totals include cached input and cache writes where reported. Missing counts are unknown, not zero.

Cost is the total for each row, in USD. CLI estimates and token-rate estimates are not settled charges. Subscription runs without a dollar measurement show unknown rather than $0. Copilot reports a request unit separately.

## Shared evidence-ID contract, high effort

| Agent / model | Effort | Category matches | Valid outputs | Time (s) | Input | Output | Cached read | Reasoning | Cost / basis |
|---|---|---:|---:|---:|---:|---:|---:|---:|---|
| Codex / `gpt-6-luna` | high | 10/10 | 10/10 | 102.450 | 156,574 | 2,393 | 22,016 | 1,464 | unknown |
| Claude Code / `claude-haiku-5-5` | high | 10/10 | 10/10 | 73.144 | 164,733 | 12,765 | 94,343 | 9,644 | $0.428039 (cli-estimate) |

## Verified provider requests, low effort

| Agent / model | Effort | Category matches | Valid outputs | Time (s) | Input | Output | Cached read | Reasoning | Cost / basis |
|---|---|---:|---:|---:|---:|---:|---:|---:|---|
| Kimi Code / `kimi-k3` | low | 10/10 | 10/10 | 89.153 | 49,354 | 1,734 | 10,240 | 425 | $0.146424 (token-rate-estimate) |
| Reasonix / `deepseek-v4-pro` | low | 10/10 | 10/10 | 212.863 | 69,067 | 12,873 | 19,968 | 11,485 | $0.058333 (token-rate-estimate) |

Same prepared case prompts, 120-second caps, no wrapper retries and no browsing. Forwarded paid requests verified the model, low effort and zero tools. A transport adapter removed mandatory Reasonix tool declarations; it did not repair answers. Kimi made 10 API requests; Reasonix made 26, including internal continuations whose tokens and duration are included.

Kimi: auxiliary facts 8/9, raw unfenced JSON 2/10, CLI exit zero 10/10. DeepSeek: auxiliary facts 9/9, raw unfenced JSON 6/10, CLI exit zero 4/10. Both had 10/10 schema/evidence-valid extracted answers. Six Reasonix calls returned completion_uncertain despite correct extracted answers. Category accuracy alone therefore overstates readiness for automation.

Token-rate estimates per case: Kimi $0.0146424; DeepSeek $0.0058333. Recorded rates per million tokens: Kimi fresh input/default five-minute cache writes $3, cache reads $0.30, output $15; DeepSeek off-peak fresh input $0.66, cache reads $0.022, output $1.98. Cache writes were included in normalized input and charged once. These are dated estimates, not promises about future prices.

Sources: [Kimi pricing](https://platform.kimi.ai/docs/pricing/chat), [Kimi cache billing](https://platform.kimi.ai/docs/guide/context-caching), [DeepSeek pricing](https://api-docs.deepseek.com/quick_start/pricing/).

## Earlier harness, low effort

| Agent / model | Effort | Category matches | Valid outputs | Time (s) | Input | Output | Cached read | Reasoning | Cost / basis |
|---|---|---:|---:|---:|---:|---:|---:|---:|---|
| Codex / `gpt-6-luna` | low | 10/10 | 10/10 | 76.604 | 146,605 | 877 | 0 | unknown | unknown |
| Claude Code / `claude-haiku-5-5` | low | 10/10 | 10/10 | 42.657 | 45,024 | 5,473 | 879 | unknown | $0.231446 (cli-estimate) |

## Earlier harness, high effort

| Agent / model | Effort | Category matches | Valid outputs | Time (s) | Input | Output | Cached read | Reasoning | Cost / basis |
|---|---|---:|---:|---:|---:|---:|---:|---:|---|
| Codex / `gpt-6-luna` | high | 10/10 | 10/10 | 98.596 | 145,231 | 2,958 | 0 | unknown | unknown |
| Claude Code / `claude-haiku-5-5` | high | 10/10 | 10/10 | 50.889 | 45,024 | 7,419 | 8,694 | unknown | $0.221209 (cli-estimate) |

## Earlier shared quote contract, high effort

| Agent / model | Effort | Category matches | Valid outputs | Time (s) | Input | Output | Cached read | Reasoning | Cost / basis |
|---|---|---:|---:|---:|---:|---:|---:|---:|---|
| Codex / `gpt-6-luna` | high | 5/10 | 5/10 | 100.171 | 153,303 | 2,622 | 41,984 | 1,531 | unknown |
| Claude Code / `claude-haiku-5-5` | high | 9/10 | 10/10 | 82.401 | 160,385 | 16,055 | 94,173 | 12,437 | $0.444193 (cli-estimate) |

Luna matched all 10 raw category labels, but only five outputs passed the quote/evidence contract. The table counts only validated category matches. Haiku passed the contract on 10 outputs but matched nine categories.

## Exploratory batch calls

| Agent / model | Effort | Category matches | Valid outputs | Time (s) | Input | Output | Cached read | Reasoning | Cost / basis |
|---|---|---:|---:|---:|---:|---:|---:|---:|---|
| codex / `gpt-6-luna` | low | 8/8 | not scored | 51.965 | 32,482 | 611 | 0 | 0 | $0.003554 (legacy-rate-estimate-unverified) |
| claude / `claude-haiku-4-5-20251001` | unsupported; extended thinking disabled | 8/8 | not scored | 14.508 | 11,355 | 1,094 | 0 | 0 | $0.028174 (cli-estimate) |

Eight decisions across two batch calls per agent. Luna evidence quotes were valid 14/14; Haiku quotes were valid 8/16 and it made three unsupported positive claims. Whole-output validity was not scored. The legacy Luna dollar estimate used unverified rate assumptions; retain it only as historical provenance, not current pricing.

## Single-case CLI compatibility checks

| Agent / model | Effort | Category matches | Valid outputs | Time (s) | Input | Output | Cached read | Reasoning | Cost / basis |
|---|---|---:|---:|---:|---:|---:|---:|---:|---|
| Kimi Code / `kimi-k2.7-code` | default (not set) | 1/1 | 1/1 | 19.640 | 25,561 | 1,121 | 256 | unknown | unknown |
| Reasonix / `deepseek-v4-flash` | default (not set) | 1/1 | 1/1 | 7.414 | 11,415 | 1,014 | 896 | unknown | $0.002990 (cli-estimate) |
| Grok Build / `grok-4.7` | default (not set) | 1/1 | 1/1 | 12.296 | 28,168 | 635 | 1,152 | 540 | $0.058418 (cli-estimate) |
| Copilot Auto / `gpt-6-luna` | default (not set) | 1/1 | 1/1 | 13.106 | 7,110 | 213 | 0 | 134 | 1 premium request (USD unknown) |

One expected outcome establishes compatibility only. Reasonix Flash returned exit 1 and extra prose, despite a correct extractable decision. Its recorded model ID is the legacy alias; [DeepSeek documents its routing to V4.1 Flash](https://api-docs.deepseek.com/quick_start/pricing/). Copilot used Auto and selected Luna; its model was not pinned. Gemini had no completed run and is excluded.
