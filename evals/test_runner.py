import json
from pathlib import Path
import sys
import unittest

import runner
from render_report import render


class HarnessTests(unittest.TestCase):
    def setUp(self):
        self.suite = {'labels': ['normal'], 'policy': 'Use normal.', 'cases': [
            {'id': 'test', 'evidence': {'e1': 'Feature request.'}, 'expected_label': 'normal',
             'private_metadata': 'NEVER_SEND_THIS'}]}

    def test_expected_answers_and_metadata_are_not_sent(self):
        payload = runner.payload_for(self.suite, self.suite['cases'][0], 'example', 'low')
        self.assertNotIn('expected_label', json.dumps(payload))
        self.assertNotIn('NEVER_SEND_THIS', json.dumps(payload))
        self.assertNotIn('cases', payload)

    def test_nonzero_exit_does_not_pass_even_with_correct_answer(self):
        program = 'import json,sys;json.dump({"answer":{"label":"normal","reason":"Routine request.","evidence_ids":["e1"]}},sys.stdout);sys.exit(1)'
        result = runner.run(self.suite, [sys.executable, '-c', program], 'example', 'low', 2)
        self.assertTrue(result['results'][0]['category_match'])
        self.assertEqual(result['automation_passes'], 0)
        self.assertIsNone(result['results'][0]['usage']['input_tokens'])
        self.assertIsNone(result['cost_usd'])

    def test_fabricated_evidence_and_extra_prose_fail(self):
        answer = {'label': 'normal', 'reason': 'Routine request.', 'evidence_ids': ['invented']}
        self.assertFalse(runner.valid_answer(answer, self.suite['labels'], {'e1': 'Text'}))
        program = 'print(\'{} extra prose\')'
        result = runner.run(self.suite, [sys.executable, '-c', program], 'example', 'low', 2)
        self.assertFalse(result['results'][0]['valid'])

    def test_timeout_is_a_failure(self):
        result = runner.run(self.suite, [sys.executable, '-c', 'import time;time.sleep(30)'],
                            'example', 'low', .1)
        self.assertEqual(result['results'][0]['status'], 'timeout')
        self.assertEqual(result['automation_passes'], 0)

    def test_report_keeps_cohorts_and_unknown_costs(self):
        root = Path(__file__).resolve().parent
        data = json.loads((root / 'historical-results.json').read_text())
        report = render(data)
        self.assertEqual(report.count('\n## '), 7)
        self.assertIn('private text-classification suite', report)
        self.assertIn('USD unknown', report)
        self.assertIn('legacy-rate-estimate-unverified', report)
        self.assertEqual(len(data['rows']), 16)
        self.assertEqual(len({r['model'] for r in data['rows']}), 8)


if __name__ == '__main__':
    unittest.main()
