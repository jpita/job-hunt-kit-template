# Historical agent evaluation results

Measured 8-9 October 2026. Sixteen aggregate results cover eight distinct model IDs.

The task was document classification: read supplied text, apply a fixed policy, select a category and identify supporting passages. Predictions were checked against predefined expected categories. Tests also checked whether the answer followed the required structure and cited available source text.

These results came from a private text-classification suite. Source texts, URLs, expected categories and personal policy are withheld. The public support-ticket example is a separate, new suite: these numbers are not its results and cannot be reproduced from it.

Each table describes a separate experiment. Instructions, required response structure and grading rules differed between experiments. Even within a table, the command-line tools supplied different system instructions, tokenization, cache behavior and internal model calls. The measurements describe these complete workflows. A single pass over ten selected documents is too small to estimate a production error rate or establish a general model ranking.

## How to read the results

- **Agent / model:** the command-line application and model identifier it used.
- **Reasoning:** the requested level of model deliberation. It was verified in provider requests only in the verified-settings experiment. Default means no explicit level was set.
- **Category matches:** answers matching predefined expected labels. The quotation experiment required evidence validation before counting a label match; the batch experiment scored labels separately from evidence.
- **Valid answers:** extracted answers that passed the experiment's structure and evidence checks. This does not imply the tool reported successful completion.
- **Cached read:** input tokens reused from a provider cache. Cache writes are recorded separately in the aggregate JSON when available.
- **Reasoning tokens:** provider-reported generated reasoning, already included in output tokens when recorded.

Time is the sum of per-case wall durations (two batch durations for the exploratory cohort), not total experiment elapsed time. Tokens include native agent overhead. Reasoning tokens are a subset of output; do not add them twice. Input totals include cached input and cache writes where reported. Missing counts are unknown, not zero.

Cost is the total for each row, in USD. CLI estimates and token-rate estimates are not settled charges. Subscription runs without a dollar measurement show unknown rather than $0. Copilot reports a request unit separately.

## Classification with evidence references: high reasoning

Each agent received the same classification instructions and prepared document text. Supporting passages had identifiers that the answer could cite, avoiding the need to reproduce quotations exactly.

| Agent / model | Reasoning | Category matches | Valid answers | Time (s) | Input tokens | Output tokens | Cached read | Reasoning tokens | Cost / basis |
|---|---|---:|---:|---:|---:|---:|---:|---:|---|
| Codex / `gpt-6-luna` | high | 10/10 | 10/10 | 102.450 | 156,574 | 2,393 | 22,016 | 1,464 | unknown |
| Claude Code / `claude-haiku-5-5` | high | 10/10 | 10/10 | 73.144 | 164,733 | 12,765 | 94,343 | 9,644 | $0.428039 (cli-estimate) |

## Classification with verified request settings: low reasoning

Each agent received the same prepared prompts and cited passage identifiers. Provider requests were recorded to verify the model, low reasoning setting and absence of available tools.

| Agent / model | Reasoning | Category matches | Valid answers | Time (s) | Input tokens | Output tokens | Cached read | Reasoning tokens | Cost / basis |
|---|---|---:|---:|---:|---:|---:|---:|---:|---|
| Kimi Code / `kimi-k3` | low | 10/10 | 10/10 | 89.153 | 49,354 | 1,734 | 10,240 | 425 | $0.146424 (token-rate-estimate) |
| Reasonix / `deepseek-v4-pro` | low | 10/10 | 10/10 | 212.863 | 69,067 | 12,873 | 19,968 | 11,485 | $0.058333 (token-rate-estimate) |

Each document had a 120-second process limit. The evaluation script did not retry failed calls or allow browsing. A forwarding adapter recorded provider requests and removed tool definitions that Reasonix added by default, so neither workflow could call a tool. The adapter did not change answers. Kimi made 10 paid API requests; Reasonix made 26 because it continued processing internally. All those calls contribute to the reported tokens, time and estimated cost.

Additional factual fields were graded separately from category labels on nine applicable cases: Kimi matched eight; DeepSeek matched nine. Kimi returned a plain JSON object without Markdown formatting on 2/10 cases; DeepSeek did so on 6/10. The evaluator could extract and validate all ten answers from each workflow.

Kimi's command-line process reported success on 10/10 cases. Reasonix reported success on 4/10; the remaining six returned `completion_uncertain`, a failure status, despite correct extracted answers. A production integration would need to handle that distinction.

Token-rate estimates per case: Kimi $0.0146424; DeepSeek $0.0058333. Recorded rates per million tokens: Kimi fresh input/default five-minute cache writes $3, cache reads $0.30, output $15; DeepSeek off-peak fresh input $0.66, cache reads $0.022, output $1.98. Cache writes were included in normalized input and charged once. These are dated estimates, not promises about future prices.

Sources: [Kimi pricing](https://platform.kimi.ai/docs/pricing/chat), [Kimi cache billing](https://platform.kimi.ai/docs/guide/context-caching), [DeepSeek pricing](https://api-docs.deepseek.com/quick_start/pricing/).

## Custom classification prompt: low reasoning

A custom evaluation script supplied the classification policy and prepared documents. This experiment used a different prompt and grader from the evidence-reference and quotation experiments.

| Agent / model | Reasoning | Category matches | Valid answers | Time (s) | Input tokens | Output tokens | Cached read | Reasoning tokens | Cost / basis |
|---|---|---:|---:|---:|---:|---:|---:|---:|---|
| Codex / `gpt-6-luna` | low | 10/10 | 10/10 | 76.604 | 146,605 | 877 | 0 | unknown | unknown |
| Claude Code / `claude-haiku-5-5` | low | 10/10 | 10/10 | 42.657 | 45,024 | 5,473 | 879 | unknown | $0.231446 (cli-estimate) |

## Custom classification prompt: high reasoning

The custom-prompt experiment repeated at high reasoning. Compare it with the low-reasoning custom-prompt table; other experiments used different instructions and grading.

| Agent / model | Reasoning | Category matches | Valid answers | Time (s) | Input tokens | Output tokens | Cached read | Reasoning tokens | Cost / basis |
|---|---|---:|---:|---:|---:|---:|---:|---:|---|
| Codex / `gpt-6-luna` | high | 10/10 | 10/10 | 98.596 | 145,231 | 2,958 | 0 | unknown | unknown |
| Claude Code / `claude-haiku-5-5` | high | 10/10 | 10/10 | 50.889 | 45,024 | 7,419 | 8,694 | unknown | $0.221209 (cli-estimate) |

## Classification with supporting quotations: high reasoning

Each agent followed shared classification instructions and was required to reproduce supporting quotations from the source text. Answers failed validation when those quotations did not match.

| Agent / model | Reasoning | Category matches | Valid answers | Time (s) | Input tokens | Output tokens | Cached read | Reasoning tokens | Cost / basis |
|---|---|---:|---:|---:|---:|---:|---:|---:|---|
| Codex / `gpt-6-luna` | high | 5/10 | 5/10 | 100.171 | 153,303 | 2,622 | 41,984 | 1,531 | unknown |
| Claude Code / `claude-haiku-5-5` | high | 9/10 | 10/10 | 82.401 | 160,385 | 16,055 | 94,173 | 12,437 | $0.444193 (cli-estimate) |

Luna selected the expected category on all ten documents, but only five answers passed quotation validation. The table counts only those five validated category matches. Haiku passed answer validation on all ten documents and matched nine expected categories.

## Batch classification: eight documents in two calls

Each agent classified eight documents across two command-line calls. Category labels and supporting quotations were checked separately; a complete answer-validity score was not recorded.

| Agent / model | Reasoning | Category matches | Valid answers | Time (s) | Input tokens | Output tokens | Cached read | Reasoning tokens | Cost / basis |
|---|---|---:|---:|---:|---:|---:|---:|---:|---|
| codex / `gpt-6-luna` | low | 8/8 | not scored | 51.965 | 32,482 | 611 | 0 | 0 | $0.003554 (legacy-rate-estimate-unverified) |
| claude / `claude-haiku-4-5-20251001` | unsupported; extended thinking disabled | 8/8 | not scored | 14.508 | 11,355 | 1,094 | 0 | 0 | $0.028174 (cli-estimate) |

Eight decisions across two batch calls per agent. Luna evidence quotes were valid 14/14; Haiku quotes were valid 8/16 and it made three unsupported claims that documents satisfied policy constraints. Complete answer validity was not scored. The Luna dollar estimate used unverified rate assumptions; it records the original calculation and should not be used to budget future runs.

## Single-document compatibility checks

Each command-line tool classified one document with a known expected category. This checks whether the integration works, rather than measuring accuracy across a varied dataset.

| Agent / model | Reasoning | Category matches | Valid answers | Time (s) | Input tokens | Output tokens | Cached read | Reasoning tokens | Cost / basis |
|---|---|---:|---:|---:|---:|---:|---:|---:|---|
| Kimi Code / `kimi-k2.7-code` | default (not set) | 1/1 | 1/1 | 19.640 | 25,561 | 1,121 | 256 | unknown | unknown |
| Reasonix / `deepseek-v4-flash` | default (not set) | 1/1 | 1/1 | 7.414 | 11,415 | 1,014 | 896 | unknown | $0.002990 (cli-estimate) |
| Grok Build / `grok-4.7` | default (not set) | 1/1 | 1/1 | 12.296 | 28,168 | 635 | 1,152 | 540 | $0.058418 (cli-estimate) |
| Copilot Auto / `gpt-6-luna` | default (not set) | 1/1 | 1/1 | 13.106 | 7,110 | 213 | 0 | 134 | 1 premium request (USD unknown) |

Reasonix Flash produced a correct decision that the evaluator could extract, but added extra prose and returned process exit code 1 (failure). Its valid-answer score covers the extracted decision; its complete response did not meet the required format. Its recorded model ID is the legacy alias; [DeepSeek documents its routing to V4.1 Flash](https://api-docs.deepseek.com/quick_start/pricing/). Copilot automatically selected Luna instead of using an explicitly chosen model. No Gemini evaluation completed, so there is no Gemini result in this report.
