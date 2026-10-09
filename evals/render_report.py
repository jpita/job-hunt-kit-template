"""Render only the allowlisted historical aggregate fields; no source records."""
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent
GROUPS = {
    'shared-ids-high': 'Classification with evidence references: high reasoning',
    'verified-low': 'Classification with verified request settings: low reasoning',
    'initial-low': 'Custom classification prompt: low reasoning',
    'initial-high': 'Custom classification prompt: high reasoning',
    'shared-quotes-high': 'Classification with supporting quotations: high reasoning',
    'exploratory-batches': 'Batch classification: eight documents in two calls',
    'one-case-smoke': 'Single-document compatibility checks',
}
GROUP_DESCRIPTIONS = {
    'shared-ids-high': 'Each agent received the same classification instructions and prepared '
                      'document text. Supporting passages had identifiers that the answer '
                      'could cite, avoiding the need to reproduce quotations exactly.',
    'verified-low': 'Each agent received the same prepared prompts and cited passage identifiers. '
                    'Provider requests were recorded to verify the model, low reasoning setting '
                    'and absence of available tools.',
    'initial-low': 'A custom evaluation script supplied the classification policy and prepared '
                   'documents. This experiment used a different prompt and grader from the '
                   'evidence-reference and quotation experiments.',
    'initial-high': 'The custom-prompt experiment repeated at high reasoning. Compare it with '
                    'the low-reasoning custom-prompt table; other experiments used different '
                    'instructions and grading.',
    'shared-quotes-high': 'Each agent followed shared classification instructions and was '
                         'required to reproduce supporting quotations from the source text. '
                         'Answers failed validation when those quotations did not match.',
    'exploratory-batches': 'Each agent classified eight documents across two command-line '
                          'calls. Category labels and supporting quotations were checked '
                          'separately; a complete answer-validity score was not recorded.',
    'one-case-smoke': 'Each command-line tool classified one document with a known expected '
                     'category. This checks whether the integration works, rather than '
                     'measuring accuracy across a varied dataset.',
}
README_START = '<!-- BEGIN GENERATED EVAL RESULTS -->'
README_END = '<!-- END GENERATED EVAL RESULTS -->'


def render_overview(data):
    lines = [README_START, '', '## Agent evaluations', '',
             'These experiments tested whether command-line AI agents could assign documents '
             'to predefined categories, follow a classification policy and cite supporting text. '
             'The table contains 16 recorded results across eight model IDs, measured '
             '8-9 October 2026.', '',
             'Each row summarizes one agent configuration. Most configurations classified ten '
             'documents; batch tests classified eight, and compatibility checks classified one. '
             'The source documents and personal policy are private. The reusable '
             '[eval template](evals/README.md) includes a separate synthetic support-ticket '
             'dataset; the scores below were not measured on that example.', '',
             '**Reading the table:** Reasoning is the requested level of model deliberation. '
             'Category matches compares answers with predefined expected labels. Valid answers '
             'passed the experiment\'s response-format and evidence checks. A score of 10/10 '
             'means ten out of ten documents. Time, tokens and cost are totals for the row.', '',
             'Compare configurations using the same experiment and reasoning setting. '
             'The experiments used different prompts and grading rules; the tools also supplied '
             'different system instructions, cache behavior and internal model calls. '
             'This measures complete agent workflows, rather than model performance in isolation.', '',
             '| Experiment | Agent / model | Reasoning | Category matches | Valid answers | Total time (s) | Input tokens | Output tokens | Estimated cost (USD) |',
             '|---|---|---|---:|---:|---:|---:|---:|---|']
    names = {'shared-ids-high': 'Evidence references', 'verified-low': 'Verified request settings',
             'initial-low': 'Custom prompt', 'initial-high': 'Custom prompt',
             'shared-quotes-high': 'Supporting quotations',
             'exploratory-batches': 'Batch classification',
             'one-case-smoke': 'Single-document check'}
    for cohort in GROUPS:
        for r in data['rows']:
            if r['cohort'] != cohort:
                continue
            ratio = lambda value: 'not scored' if value is None else f"{value}/{r['cases']}"
            cost = 'unknown'
            if r['cost_usd'] is not None:
                basis = {'cli-estimate': 'CLI estimate', 'token-rate-estimate': 'rate estimate',
                         'legacy-rate-estimate-unverified': 'unverified legacy estimate'}[r['cost_basis']]
                cost = f"${r['cost_usd']:.6f} ({basis})"
            elif r.get('premium_requests') is not None:
                cost = f"{r['premium_requests']} premium request; USD unknown"
            lines.append(f"| {names[cohort]} | {r['provider']} / `{r['model']}` | "
                         f"{r['reasoning_effort']} | {ratio(r['category_correct'])} | "
                         f"{ratio(r['valid_outputs'])} | {r['seconds']:.3f} | "
                         f"{r['input_tokens']:,} | {r['output_tokens']:,} | {cost} |")
    lines += ['', 'Tokens are the provider-reported units of input and generated text, including '
              'the agent tool\'s own instructions and internal calls. A CLI estimate is reported '
              'by the command-line tool; a rate estimate applies published token prices to '
              'recorded usage. Neither is a settled bill. Unknown subscription costs do not mean '
              'the service is free. Copilot reported a premium-request unit rather than dollars.', '',
              '**Correct answers still need a reliable integration.** DeepSeek Pro produced '
              'ten valid, correctly categorized answers, but its command-line tool reported '
              'successful completion for only four. Flash produced a correct answer but reported '
              'failure and included extra prose. The batch Haiku test matched category labels '
              'but included unsupported evidence. The quotation experiment counted a category '
              'match only after evidence validation. The detailed report explains these '
              'grading differences and the remaining limitations.', '',
              '[Full results, cache/reasoning tokens and methodology](evals/BENCHMARKS.md) · '
              '[Reusable eval template](evals/README.md)', '', README_END]
    return '\n'.join(lines)


def render(data):
    lines = [
        '# Historical agent evaluation results', '',
        'Measured 8-9 October 2026. Sixteen aggregate results cover eight distinct model IDs.', '',
        'The task was document classification: read supplied text, apply a fixed policy, '
        'select a category and identify supporting passages. Predictions were checked '
        'against predefined expected categories. Tests also checked whether the answer '
        'followed the required structure and cited available source text.', '',
        'These results came from a private text-classification suite. Source texts, URLs, '
        'expected categories and personal policy are withheld. The public support-ticket '
        'example is a separate, new suite: these numbers are not its results and cannot '
        'be reproduced from it.', '',
        'Each table describes a separate experiment. Instructions, required response '
        'structure and grading rules differed between experiments. Even within a table, '
        'the command-line tools supplied different system instructions, tokenization, '
        'cache behavior and internal model calls. The measurements describe these '
        'complete workflows. A single pass over ten selected documents is too small '
        'to estimate a production error rate or establish a general model ranking.', '',
        '## How to read the results', '',
        '- **Agent / model:** the command-line application and model identifier it used.',
        '- **Reasoning:** the requested level of model deliberation. It was verified in '
        'provider requests only in the verified-settings experiment. Default means no '
        'explicit level was set.',
        '- **Category matches:** answers matching predefined expected labels. The quotation '
        'experiment required evidence validation before counting a label match; the batch '
        'experiment scored labels separately from evidence.',
        '- **Valid answers:** extracted answers that passed the experiment\'s structure and '
        'evidence checks. This does not imply the tool reported successful completion.',
        '- **Cached read:** input tokens reused from a provider cache. Cache writes are '
        'recorded separately in the aggregate JSON when available.',
        '- **Reasoning tokens:** provider-reported generated reasoning, already included '
        'in output tokens when recorded.', '',
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
        lines += [f'## {title}', '', GROUP_DESCRIPTIONS[cohort], '',
                  '| Agent / model | Reasoning | Category matches | Valid answers | Time (s) | Input tokens | Output tokens | Cached read | Reasoning tokens | Cost / basis |',
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
                'Each document had a 120-second process limit. The evaluation script did '
                'not retry failed calls or allow browsing. A forwarding adapter recorded '
                'provider requests and removed tool definitions that Reasonix added by '
                'default, so neither workflow could call a tool. The adapter did not change '
                'answers. Kimi made 10 paid API requests; Reasonix made 26 because it '
                'continued processing internally. All those calls contribute to the '
                'reported tokens, time and estimated cost.', '',
                'Additional factual fields were graded separately from category labels '
                'on nine applicable cases: Kimi matched eight; DeepSeek matched nine. '
                'Kimi returned a plain JSON object without Markdown formatting on 2/10 '
                'cases; DeepSeek did so on 6/10. The evaluator could extract and validate '
                'all ten answers from each workflow.', '',
                'Kimi\'s command-line process reported success on 10/10 cases. Reasonix '
                'reported success on 4/10; the remaining six returned '
                '`completion_uncertain`, a failure status, despite correct extracted answers. '
                'A production integration would need to handle that distinction.', '',
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
            lines += ['Luna selected the expected category on all ten documents, but only five '
                      'answers passed quotation validation. The table counts only those five '
                      'validated category matches. Haiku passed answer validation on all ten '
                      'documents and matched nine expected categories.', '']
        elif cohort == 'exploratory-batches':
            lines += ['Eight decisions across two batch calls per agent. Luna evidence quotes '
                      'were valid 14/14; Haiku quotes were valid 8/16 and it made three '
                      'unsupported claims that documents satisfied policy constraints. '
                      'Complete answer validity was not scored. The Luna dollar estimate used '
                      'unverified rate assumptions; it records the original calculation and '
                      'should not be used to budget future runs.', '']
        elif cohort == 'one-case-smoke':
            lines += ['Reasonix Flash produced a correct decision that the evaluator could '
                      'extract, but added extra prose and returned process exit code 1 '
                      '(failure). Its valid-answer score covers the extracted decision; '
                      'its complete response did not meet the required format. '
                      'Its recorded model ID is the legacy alias; '
                      '[DeepSeek documents its routing to V4.1 Flash]'
                      '(https://api-docs.deepseek.com/quick_start/pricing/). '
                      'Copilot automatically selected Luna instead of using an explicitly '
                      'chosen model. No Gemini evaluation completed, so there is no Gemini '
                      'result in this report.', '']
    return '\n'.join(lines).rstrip() + '\n'


if __name__ == '__main__':
    data = json.loads((ROOT / 'historical-results.json').read_text())
    (ROOT / 'BENCHMARKS.md').write_text(render(data))
    readme = ROOT.parent / 'README.md'
    text = readme.read_text()
    if README_START not in text or README_END not in text:
        raise ValueError('README generated-result markers are missing')
    before, rest = text.split(README_START, 1)
    _, after = rest.split(README_END, 1)
    readme.write_text(before + render_overview(data) + after)
