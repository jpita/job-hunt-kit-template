"""Offline harness demonstration, NOT a model or benchmark result."""
import json
import sys

request = json.load(sys.stdin)
text = ' '.join(request['evidence'].values()).lower()
if 'resolved' in text:
    label = 'closed'
elif 'lunch menu' in text:
    label = 'out_of_scope'
elif 'production outage' in text or 'data loss' in text:
    label = 'urgent'
elif 'no details' in text or 'no description' in text:
    label = 'needs_info'
else:
    label = 'normal'
json.dump({'answer': {'label': label, 'reason': 'Matches the supplied routing policy.',
                      'evidence_ids': [next(iter(request['evidence']))]}}, sys.stdout)
