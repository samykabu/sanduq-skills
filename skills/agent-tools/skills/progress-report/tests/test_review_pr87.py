"""Regressions for the sanduq PR #87 review: duplicate facts lanes that share a delegation identity, and stale receipts."""
import tempfile
import unittest
from datetime import datetime

import helpers  # noqa: F401  (puts the scripts dir on sys.path)
from sanduq_progress import model
from sanduq_progress.collect import workflow as wf
from test_p1_review import REQ, STAGE, attempt, fact_lane, synth


def parse(value):
    return datetime.fromisoformat(value.replace('Z', '+00:00'))


class DuplicateIdentityLanes(unittest.TestCase):
    def test_two_facts_lanes_owned_by_one_identity_fold_into_one_lane(self):
        facts = (fact_lane('L1', STAGE, '2026-10-17T13:00:00Z', '2026-10-17T13:10:00Z', REQ)
                 + fact_lane('L2', STAGE, '2026-10-17T13:01:00Z', '2026-10-17T13:10:00Z', REQ))
        attempts = [attempt(STAGE, 'codex-20261017130500-aaaa', '2026-10-17T13:02:00Z', '2026-10-17T13:09:00Z')]
        with tempfile.TemporaryDirectory() as base:
            report = model.build_v2(synth(base, facts, attempts), parse('2026-10-17T14:00:00Z'), 1, {})
        lanes = [l for l in report['lanes'] if l['owner'] == STAGE]
        self.assertEqual([l['id'] for l in lanes], ['L1'])
        self.assertEqual(len(lanes[0]['attempts']), 1)


class StaleReceipts(unittest.TestCase):
    RECEIPTS = {'plan': {'stage': 'plan', 'outcome': 'passed', 'completed_at': '2026-10-17T10:00:00Z'},
                'implement': {'stage': 'implement', 'outcome': 'passed', 'completed_at': '2026-10-17T11:00:00Z',
                              'stale': {'reason': 'evidence-amended', 'stage': 'plan'}}}

    def test_the_current_stage_skips_a_stale_receipt_but_history_keeps_it(self):
        with tempfile.TemporaryDirectory() as base:
            ctx = synth(base, checkpoint={'branch': 'b', 'status': 'in-progress', 'receipts': self.RECEIPTS})
            cp = wf.checkpoint(ctx.feature_dir)
            self.assertEqual(cp['last_accepted']['stage'], 'plan')
            self.assertEqual([r['stage'] for r in cp['receipts']], ['plan', 'implement'])
            self.assertEqual(model.build_v2(ctx, parse('2026-10-17T14:00:00Z'), 1, {})['feature']['stage']['value'], 'plan')

    def test_a_stale_receipt_still_supersedes_a_pause_it_followed(self):
        with tempfile.TemporaryDirectory() as base:
            ctx = synth(base, checkpoint={'status': 'in-progress', 'receipts': self.RECEIPTS,
                                          'pause': {'reason': 'wait', 'at': '2026-10-17T10:30:00Z'}})
            self.assertEqual(wf.checkpoint(ctx.feature_dir)['pause']['superseded'], 'later accepted receipt')

    def test_only_stale_receipts_leave_no_current_stage(self):
        stale = {k: dict(v, stale={'reason': 'x'}) for k, v in self.RECEIPTS.items()}
        with tempfile.TemporaryDirectory() as base:
            ctx = synth(base, checkpoint={'status': 'in-progress', 'receipts': stale})
            self.assertIsNone(wf.checkpoint(ctx.feature_dir)['last_accepted'])


if __name__ == '__main__':
    unittest.main()
