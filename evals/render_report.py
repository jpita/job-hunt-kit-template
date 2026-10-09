"""Render only the allowlisted historical aggregate fields; no source records."""
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent
GROUPS = {
    'shared-ids-high': 'Shared evidence-ID contract, high effort',
    'verified-low': 'Verified provider requests, low effort',
    'initial-low': 'Earlier harness, low effort',
    'initial-high': 'Earlier harness, high effort',
    'shared-quotes-high': 'Earlier shared quote contract, high effort',
    'exploratory-batches': 'Exploratory batch calls',
    'one-case-smoke': 'Single-case CLI compatibility checks',
}


def render(data):
    lines = [
        '# Historical agent evaluation results', '',
        'Measured 8-9 October 2026. Sixteen aggregate rows cover eight distinct model IDs.', '',
        'These results came from a private text-classification suite. Source texts, URLs, '
        'expected categories and personal policy are withheld. The public support-ticket '
        'example is a separate, new suite: these numbers are not its results and cannot '
        'be reproduced from it.', '',
        'Each table is a separate cohort. Do not rank across tables: prompts, output '
        'contracts and scoring changed. Even within a cohort, native CLI system context, '
        'tokenizers, cache state and internal orchestration differed. These are workflow '
        'measurements, not intrinsic model efficiency benchmarks. Ten selected cases '
        'in one pass do not establish a production error rate.', '',
        'Time is the sum of per-case wall durations (two batch durations for the '
        'exploratory cohort), not total experiment elapsed time. Tokens include native '
        'agent overhead. Reasoning tokens are a subset of output; do not add them twice. '
        'Input totals include cached input and cache writes where reported. Missing '
        'counts are unknown, not zero.', '',
        'Cost is the total for each row, in USD. CLI estimates and token-rate estimates '
        'are not settled charges. Subscription runs without a dollar measurement show '
        'unknown rather than $0. Copilot reports a request unit separately.', '',
    ]
    for cohort, title in GROUPS.items():
        lines += [f'## {title}', '',
                  '| Agent / model | Effort | Category matches | Valid outputs | Time (s) | Input | Output | Cached read | Reasoning | Cost / basis |',
                  '|---|---|---:|---:|---:|---:|---:|---:|---:|---|']
        for r in data['rows']:
            if r['cohort'] != cohort:
                continue
            count = lambda value: 'unknown' if value is None else f'{value:,}'
            ratio = lambda value: 'not scored' if value is None else f"{value}/{r['cases']}"
            cost = 'unknown'
            if r['cost_usd'] is not None:
                cost = f"${r['cost_usd']:.6f} ({r['cost_basis']})"
            elif r.get('premium_requests') is not None:
                cost = f"{r['premium_requests']} premium request (USD unknown)"
            lines.append(f"| {r['provider']} / `{r['model']}` | {r['reasoning_effort']} | "
                         f"{ratio(r['category_correct'])} | {ratio(r['valid_outputs'])} | "
                         f"{r['seconds']:.3f} | {count(r['input_tokens'])} | "
                         f"{count(r['output_tokens'])} | {count(r['cached_read_tokens'])} | "
                         f"{count(r['reasoning_tokens'])} | {cost} |")
        lines += ['']
        if cohort == 'verified-low':
            lines += [
                'Same prepared case prompts, 120-second caps, no wrapper retries and no browsing. '
                'Forwarded paid requests verified the model, low effort and zero tools. '
                'A transport adapter removed mandatory Reasonix tool declarations; it did '
                'not repair answers. Kimi made 10 API requests; Reasonix made 26, including '
                'internal continuations whose tokens and duration are included.', '',
                'Kimi: auxiliary facts 8/9, raw unfenced JSON 2/10, CLI exit zero 10/10. '
                'DeepSeek: auxiliary facts 9/9, raw unfenced JSON 6/10, CLI exit zero 4/10. '
                'Both had 10/10 schema/evidence-valid extracted answers. Six Reasonix '
                'calls returned completion_uncertain despite correct extracted answers. '
                'Category accuracy alone therefore overstates readiness for automation.', '',
                'Token-rate estimates per case: Kimi $0.0146424; DeepSeek $0.0058333. '
                'Recorded rates per million tokens: Kimi fresh input/default five-minute '
                'cache writes $3, cache reads $0.30, output $15; DeepSeek off-peak fresh '
                'input $0.66, cache reads $0.022, output $1.98. Cache writes were included '
                'in normalized input and charged once. These are dated estimates, not '
                'promises about future prices.', '',
                'Sources: [Kimi pricing](https://platform.kimi.ai/docs/pricing/chat), '
                '[Kimi cache billing](https://platform.kimi.ai/docs/guide/context-caching), '
                '[DeepSeek pricing](https://api-docs.deepseek.com/quick_start/pricing/).', '',
            ]
        elif cohort == 'shared-quotes-high':
            lines += ['Luna matched all 10 raw category labels, but only five outputs passed '
                      'the quote/evidence contract. The table counts only validated category '
                      'matches. Haiku passed the contract on 10 outputs but matched nine categories.', '']
        elif cohort == 'exploratory-batches':
            lines += ['Eight decisions across two batch calls per agent. Luna evidence quotes '
                      'were valid 14/14; Haiku quotes were valid 8/16 and it made three '
                      'unsupported positive claims. Whole-output validity was not scored. '
                      'The legacy Luna dollar estimate used unverified rate assumptions; '
                      'retain it only as historical provenance, not current pricing.', '']
        elif cohort == 'one-case-smoke':
            lines += ['One expected outcome establishes compatibility only. Reasonix Flash '
                      'returned exit 1 and extra prose, despite a correct extractable decision. '
                      'Its recorded model ID is the legacy alias; '
                      '[DeepSeek documents its routing to V4.1 Flash]'
                      '(https://api-docs.deepseek.com/quick_start/pricing/). '
                      'Copilot used Auto and selected Luna; its model was not pinned. '
                      'Gemini had no completed run and is excluded.', '']
    return '\n'.join(lines).rstrip() + '\n'


if __name__ == '__main__':
    (ROOT / 'BENCHMARKS.md').write_text(render(json.loads((ROOT / 'historical-results.json').read_text())))
