# Agent evaluation template

Use this template to test whether an AI agent can classify documents according to your
rules. Supply a policy, a list of allowed categories and documents with known expected
categories. The runner sends each document to an adapter, grades the returned answer and
records processing time and available token counts.

The template works independently of the job scanner. Its included example classifies ten
fictional support tickets into `urgent`, `normal`, `needs_info`, `out_of_scope` or `closed`.
It contains no candidate profile or real postings.

[Historical model results](BENCHMARKS.md) describe separate experiments on a private
document-classification dataset. Those scores were not obtained from the support-ticket
example. The original documents and policy are withheld, so the public example cannot
reproduce those historical scores.

## Run the offline example

Requires Python 3.10+ on macOS or Linux. From the repository root:

```sh
cd evals
python3 runner.py --suite examples/tickets.json --model mock --effort none --output runs/mock.json -- python3 "$PWD/examples/mock_adapter.py"
python3 -m unittest discover -s . -p 'test_*.py'
```

This uses a local keyword classifier, not an AI model. It makes no network calls and incurs
no provider charges. It should report `10/10 automation passes` and write `runs/mock.json`.
The example checks that the runner can send inputs, grade answers and record results.

## Define your own classification task

Edit or copy `examples/tickets.json`. A test suite contains:

- `policy`: the rules the agent must follow, including how to resolve overlapping categories.
- `labels`: the categories the agent is allowed to return.
- `cases`: documents with an ID, supporting text and an expected category.

For example, one case can look like this:

```json
{
  "id": "case-01",
  "evidence": {"e1": "Production outage: every request fails."},
  "expected_label": "urgent"
}
```

An evidence ID such as `e1` identifies a supplied passage. The agent cites IDs in its answer
so the grader can check that its references exist. Expected categories are used only for
grading and are not sent to the adapter. Keep private suites in `evals/private/` or the
repository's `me/` directory; both are excluded from Git.

## Connect an AI agent

An **adapter** is a small program that translates between this runner's JSON format and
the command-line tool or API you want to test. Only the offline example adapter is included.
You must provide a real provider adapter before this template can evaluate an AI model.

The adapter reads one JSON object from standard input. It receives `model`,
`reasoning_effort`, `policy`, `labels`, `evidence` and the required answer structure. It
should invoke the selected model, apply the requested reasoning setting, disable browsing
and tools for text-only comparisons, then translate the provider's response into this form:

```json
{
  "answer": {
    "label": "normal",
    "reason": "A routine feature request.",
    "evidence_ids": ["e1"]
  },
  "usage": {
    "input_tokens": 100,
    "output_tokens": 20,
    "cached_read_tokens": 0,
    "reasoning_tokens": null
  }
}
```

Write exactly one JSON object to standard output. Put diagnostics on standard error.
The optional `usage` object contains provider-reported token counts; omit unavailable
counts or use `null`. Include all internal model calls and use a consistent definition of
input tokens across providers. Reasoning tokens are part of generated output, not an
additional charge to add on top of output tokens.

Pass the adapter command after `--`, as in the offline example, using an absolute path.
The runner launches it in a new temporary working directory for each document and enforces
a timeout. It does not retry calls, repair answers or fetch URLs. A temporary working
directory does not restrict filesystem or network access; the adapter must enforce tool
permissions itself. Native agent tools have different response formats, so their raw output
usually needs translation before the runner can grade it.

The runner records the requested model and reasoning level. It cannot verify that the
provider honored them. Verify actual request settings separately when comparing providers.

## Understand the score

An **automation pass** requires all of the following:

- The answer selects an allowed category and matches the expected category.
- The reason contains 1-40 words.
- The answer cites 1-3 unique IDs present in the supplied evidence.
- The adapter returns the required JSON, finishes before the timeout and exits successfully.

The runner records category matches separately from automation passes. A correct answer
from a process that reports failure therefore does not count as an automation pass.
Evidence-ID validation checks that a cited passage exists; it does not prove that the
passage supports the answer. Review that semantic relationship separately.

Results are saved under `runs/`, which is excluded from Git. Token counts that were not
reported stay `null`. The runner does not calculate dollar costs. Record provider-reported
estimates or calculate costs using dated token rates, and label their source. A subscription
without per-run billing does not establish a measured zero-dollar cost.

## Compare and publish results

For a meaningful comparison, use the same document snapshots, policy, answer format,
grading rules, timeouts, retry policy and tool permissions. Set the reasoning level explicitly.
Document differences in system instructions, caching and internal calls: identical document
inputs alone do not create identical execution conditions.

Publish reviewed aggregate measurements with their dates and test conditions. Keep private
documents, source URLs, prompts, raw sessions, credentials, account balances and personal
policy out of Git. `.gitignore` helps prevent accidental inclusion but does not replace
reviewing the files you publish.

The included historical JSON contains selected aggregate counters and model identifiers.
To regenerate both its detailed report and the table in the main README, run this command
from `evals/`:

```sh
python3 render_report.py
```

This command formats the recorded historical data; it does not run any model evaluations.
