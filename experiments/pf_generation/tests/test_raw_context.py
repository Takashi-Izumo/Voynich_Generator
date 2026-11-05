"""R2: refreshed receipts cannot move a raw row to another PF candidate."""
from copy import deepcopy
import unittest

from experiments.pf_generation.common import digest
from experiments.pf_generation.policy_audit import trace_coverage
from experiments.pf_generation.tests.test_trace_coverage import fixture


def refresh_receipts(data):
    _, requests, _, proposals = data
    for request in requests:
        for receipt in request['pfgen']['raw_calls']:
            receipt['row_sha256'] = digest(proposals[receipt['call_id']])


def two_candidates(context=None):
    left = fixture()
    right = fixture()
    replacement = context or dict(page='p', locus='p.1', segment_id=0, event=0, candidate=1)
    c, r, g, p = right
    c[0].update(replacement, proposal_id_start=3, proposal_id_end=6,
                pfgen_trace=dict(trace_schema=2, gate_start=2, gate_stop=4, raw_start=3, raw_stop=6))
    for request in r:
        request.update({k: replacement[k] for k in ['page', 'locus', 'segment_id']})
        request['proposal_id'] += 3
        request['pfgen'].update(event=replacement['event'], candidate=replacement['candidate'])
        request['pfgen']['gate_query_id'] += 2
        for receipt in request['pfgen']['raw_calls']:
            receipt['call_id'] += 3
    for gate in g:
        gate.update(replacement)
        gate['query_id'] += 2
    for row in p:
        row.update(replacement)
        row['call_id'] += 3
        row['request_id'] += 3
        row['gate_query_id'] += 2
    merged = tuple(a + b for a, b in zip(left, right))
    refresh_receipts(merged)
    return merged


class RawContextTests(unittest.TestCase):
    def check(self, data):
        return trace_coverage(*data, 'PF_GATE_LENGTH')

    def test_normal_multiple_candidates(self):
        self.assertEqual(self.check(two_candidates())['raw_calls'], 6)

    def test_existing_candidate_misattribution_even_with_fresh_receipt(self):
        data = two_candidates()
        data[3][0]['candidate'] = 1
        refresh_receipts(data)
        with self.assertRaisesRegex(ValueError, 'Raw call belongs to another candidate context'):
            self.check(data)

    def test_each_raw_context_component_with_refreshed_receipt(self):
        for name, wrong in dict(page='other-page', locus='p.99', segment_id=1, event=1, candidate=1).items():
            with self.subTest(field=name):
                data = fixture()
                data[3][0][name] = wrong
                refresh_receipts(data)
                with self.assertRaisesRegex(ValueError, 'Raw call belongs to another candidate context'):
                    self.check(data)

    def test_complete_context_from_other_existing_event(self):
        other = dict(page='p', locus='p.2', segment_id=1, event=1, candidate=0)
        data = two_candidates(other)
        data[3][0].update(other)
        refresh_receipts(data)
        with self.assertRaisesRegex(ValueError, 'Raw call belongs to another candidate context'):
            self.check(data)

    def test_context_types_are_not_coerced(self):
        for name in ['segment_id', 'event', 'candidate']:
            for value in [False, 0.0, '0']:
                with self.subTest(field=name, value=value):
                    data = fixture()
                    data[3][0][name] = value
                    refresh_receipts(data)
                    with self.assertRaisesRegex(ValueError, 'context fields/types'):
                        self.check(data)

    def test_missing_context_component_is_explicitly_rejected(self):
        for name in ['page', 'locus', 'segment_id', 'event', 'candidate']:
            with self.subTest(field=name):
                data = fixture()
                del data[3][0][name]
                refresh_receipts(data)
                with self.assertRaisesRegex(ValueError, 'context fields/types'):
                    self.check(data)

    def test_gate_context_uses_same_strict_identity(self):
        data = fixture()
        data[2][0]['candidate'] = 0.0
        with self.assertRaisesRegex(ValueError, 'context fields/types'):
            self.check(data)

    def test_request_context_uses_same_strict_identity(self):
        data = fixture()
        data[1][0]['pfgen']['candidate'] = False
        with self.assertRaisesRegex(ValueError, 'context fields/types'):
            self.check(data)


if __name__ == '__main__':
    unittest.main()
