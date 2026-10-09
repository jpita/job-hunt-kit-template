# Agent evaluation template

Compare one-shot classification workflows with your own policy, labels and expected outcomes.
This folder is independent of the scanner and contains no candidate profile or live postings.

[Historical results](BENCHMARKS.md) show measured duration, token usage, output validity and
cost provenance for eight model IDs. The original private classification suite is withheld.
Those measurements do not describe the public synthetic support-ticket example.

## Offline example

Requires Python 3.10+ on macOS or Linux. From this folder:

```sh
python3 runner.py --suite examples/tickets.json --model mock --effort none --output runs/mock.json -- python3 "$PWD/examples/mock_adapter.py"
python3 -m unittest discover -s . -p 'test_*.py'
python3 render_report.py
```

The mock proves that the harness runs; it is not an AI eval. Change the policy, labels and
cases to suit your task. Keep private suites in `private/` or your existing `me/` directory.
Expected labels are used by the grader and are not included in the adapter request.

## Real agent adapters

Pass an absolute adapter command after `--`. The runner launches it in a fresh temporary
directory for every case, sends a JSON object on stdin and accepts exactly one JSON object
on stdout. No shell interpolation, model retries, answer repair or URL fetching is performed.

Input includes `model`, `reasoning_effort`, `policy`, `labels`, `evidence` and an output
contract. The adapter must invoke its provider's CLI/API, honor the requested model/effort,
disable browsing/tools for text-only comparisons and parse the native response envelope.
Native CLIs do not share a single output/usage format, so their raw stdout cannot be passed
directly to this runner. Provider adapters are deliberately not bundled yet.

Output contract:

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

Usage is optional. Normalize input counts consistently across providers and include all
internal paid calls; reasoning counts are informational subsets of output. Unknown metrics
remain null. The runner does not estimate costs or assert that effort was honored.
Record verified provider settings and dated pricing separately. Never interpret subscription
inclusion as a measured zero-dollar cost.

An automation pass requires a supported label, a 1-40 word reason, 1-3 unique evidence IDs
that exist in the input, the expected category, no timeout and exit zero. ID validation proves
the cited text exists, not that it supports the answer semantically. Review evidence relevance
separately. A fresh cwd is not a permissions sandbox; adapters must enforce tool restrictions.

## Publishing results

Publish only allowlisted aggregate metrics, their measurement date and conditions. Keep
source texts, URLs, prompts, raw sessions, credentials, balances, personal rules and expected
labels for private suites out of Git. `.gitignore` is a convenience, not a privacy guarantee.
The public historical JSON was built by selecting numeric counters and model identifiers,
not by attempting to redact private logs. Results in `runs/` remain local until reviewed.

Rebuild `BENCHMARKS.md` from `historical-results.json` with `render_report.py`. Keep harness
versions in separate tables. Compare the same fixture snapshots, policy, timeout, retries,
tool permissions, reasoning settings and cache conditions; document every difference.
