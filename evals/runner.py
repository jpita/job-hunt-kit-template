"""Provider-neutral text classification eval. Adapter: stdin JSON -> stdout JSON."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import signal
import subprocess
import tempfile
import time


def payload_for(suite, case, model, effort):
    # Explicit selection ensures expected labels and fixture metadata never enter the request.
    return {'model': model, 'reasoning_effort': effort,
            'policy': suite['policy'], 'labels': suite['labels'],
            'evidence': case['evidence'],
            'output_contract': {'label': 'one allowed label', 'reason': '1-40 words',
                                'evidence_ids': '1-3 IDs from supplied evidence'}}


def valid_answer(answer, labels, evidence):
    if not isinstance(answer, dict) or set(answer) != {'label', 'reason', 'evidence_ids'}:
        return False
    ids = answer['evidence_ids']
    return (isinstance(answer['label'], str) and answer['label'] in labels
            and isinstance(answer['reason'], str) and 1 <= len(answer['reason'].split()) <= 40
            and isinstance(ids, list) and 1 <= len(ids) <= 3
            and all(isinstance(i, str) and i in evidence for i in ids)
            and len(set(ids)) == len(ids))


def invoke(command, payload, timeout):
    started = time.monotonic()
    # A fresh cwd reduces implicit project context. This is not a security sandbox.
    with tempfile.TemporaryDirectory(prefix='classification-eval-') as scratch:
        proc = subprocess.Popen(command, stdin=subprocess.PIPE, stdout=subprocess.PIPE,
                                stderr=subprocess.PIPE, text=True, cwd=scratch,
                                start_new_session=True)
        try:
            stdout, _ = proc.communicate(json.dumps(payload), timeout=timeout)
            status = 'completed'
        except subprocess.TimeoutExpired:
            os.killpg(proc.pid, signal.SIGKILL)
            proc.communicate()
            stdout, status = '', 'timeout'
    return stdout, proc.returncode, status, round(time.monotonic() - started, 3)


def run(suite, command, model, effort, timeout):
    results = []
    for case in suite['cases']:
        payload = payload_for(suite, case, model, effort)
        stdout, exit_code, status, seconds = invoke(command, payload, timeout)
        valid, matched, usage = False, False, {}
        try:
            envelope = json.loads(stdout)  # Strict JSON: fences/prose are not silently repaired.
            answer = envelope['answer']
            valid = valid_answer(answer, suite['labels'], case['evidence'])
            matched = valid and answer['label'] == case['expected_label']
            supplied = envelope.get('usage', {})
            # Unknown token counters stay null. Do not persist arbitrary adapter metadata.
            for key in ['input_tokens', 'output_tokens', 'cached_read_tokens', 'reasoning_tokens']:
                value = supplied.get(key) if isinstance(supplied, dict) else None
                usage[key] = value if type(value) is int and value >= 0 else None
        except (ValueError, TypeError, KeyError):
            pass
        results.append({'case_id': case['id'], 'status': status, 'exit_code': exit_code,
                        'seconds': seconds, 'valid': valid, 'category_match': matched,
                        'automation_pass': matched and status == 'completed' and exit_code == 0,
                        'usage': usage or dict.fromkeys(['input_tokens', 'output_tokens',
                                                      'cached_read_tokens', 'reasoning_tokens'])})
    serialized = json.dumps(suite, sort_keys=True).encode()
    return {'schema_version': 1, 'suite_sha256': hashlib.sha256(serialized).hexdigest(),
            'model_requested': model, 'effort_requested': effort,
            'effort_verified': False, 'timeout_seconds': timeout, 'wrapper_retries': 0,
            'cases': len(results), 'automation_passes': sum(r['automation_pass'] for r in results),
            'seconds': round(sum(r['seconds'] for r in results), 3),
            'cost_usd': None, 'cost_basis': 'not measured', 'results': results}


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--suite', type=Path, required=True)
    parser.add_argument('--model', required=True)
    parser.add_argument('--effort', required=True)
    parser.add_argument('--timeout', type=float, default=120)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('command', nargs=argparse.REMAINDER)
    args = parser.parse_args()
    command = args.command[1:] if args.command[:1] == ['--'] else args.command
    if not command or args.timeout <= 0:
        parser.error('provide a command after -- and a positive timeout')
    report = run(json.loads(args.suite.read_text()), command, args.model, args.effort, args.timeout)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2) + '\n')
    print(f"{report['automation_passes']}/{report['cases']} automation passes, {report['seconds']}s")
