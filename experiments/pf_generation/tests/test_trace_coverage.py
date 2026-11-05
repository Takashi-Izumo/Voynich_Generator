"""Regression coverage for erased/partial/duplicated policy traces, R1."""
from copy import deepcopy
import unittest

from experiments.pf_generation.common import digest
from experiments.pf_generation.policy_audit import trace_coverage
from experiments.pf_generation.proposal import Trace


def fixture():
    context = dict(page='p', locus='p.1', segment_id=0, event=0, candidate=0)
    candidates = [dict(context, proposal_id_start=0, proposal_id_end=3, nwords=2, segment_capacity=9,
                       pfgen_trace=dict(trace_schema=2, gate_start=0, gate_stop=2, raw_start=0, raw_stop=3))]
    gates = [dict(context, query_id=i, rstart=r, capacity=9) for i, r in enumerate([9, 4])]
    requests, proposals = [], []
    for pid, (gid, word, remaining, end, auxiliary) in enumerate([(0, 0, 9, True, 0),
                                                                (0, 0, 9, False, 0),
                                                                (1, 1, 4, True, 1)]):
        request = dict(page='p', locus='p.1', segment_id=0, proposal_id=pid, row_phase='FINAL',
                       line_end_boundary=True, word_index=word, rstart=remaining, end=end,
                       proposal_draws=auxiliary, role='BODY', first='q',
                       pfgen=dict(trace_schema=2, gate_query_id=gid, event=0, candidate=0, raw_calls=[]))
        for _ in range(1 + auxiliary if end else 0):
            call_id = len(proposals)
            row = dict(context, call_id=call_id, gate_query_id=gid, request_id=pid,
                       word_index=word, rstart=remaining, role='BODY', chosen_draw=0,
                       draws=[dict(stable_surface='q')])
            proposals.append(row)
            request['pfgen']['raw_calls'].append(dict(call_id=call_id, draws=1, row_sha256=digest(row)))
        requests.append(request)
    return candidates, requests, gates, proposals


class CoverageTests(unittest.TestCase):
    def check(self, data, arm='PF_GATE_LENGTH'):
        return trace_coverage(*data, arm)

    def test_normal_retry_and_map_auxiliary_calls(self):
        self.assertEqual(self.check(fixture()), dict(gate_queries=2, raw_calls=3, pf_requests=3))

    def test_segment_retry_can_repeat_word_start_with_a_new_query_id(self):
        c, r, g, p = fixture()
        g.insert(1, dict(g[0]))
        for i, gate in enumerate(g):
            gate['query_id'] = i
            r[i]['pfgen']['gate_query_id'] = i
        c[0]['pfgen_trace']['gate_stop'] = 3
        for row in p:
            row['gate_query_id'] = r[row['request_id']]['pfgen']['gate_query_id']
        for request in r:
            for receipt in request['pfgen']['raw_calls']:
                receipt['row_sha256'] = digest(p[receipt['call_id']])
        self.assertEqual(self.check((c, r, g, p))['gate_queries'], 3)

    def test_full_omission_with_zeroed_summaries_cannot_pass(self):
        c, r, g, p = fixture()
        with self.assertRaisesRegex(ValueError, 'Missing PF policy rows'):
            self.check((c, r, [], []))

    def test_partial_gate_omission(self):
        c, r, g, p = fixture()
        with self.assertRaises(ValueError):
            self.check((c, r, g[:-1], p))

    def test_partial_raw_omission(self):
        c, r, g, p = fixture()
        with self.assertRaises(ValueError):
            self.check((c, r, g, p[:-1]))

    def test_duplicate_gate(self):
        c, r, g, p = fixture()
        with self.assertRaisesRegex(ValueError, 'duplicate/reordered gate'):
            self.check((c, r, [g[0], *g], p))

    def test_duplicate_raw(self):
        c, r, g, p = fixture()
        with self.assertRaisesRegex(ValueError, 'duplicate/reordered raw'):
            self.check((c, r, g, [p[0], *p]))

    def test_reordered_raw(self):
        c, r, g, p = fixture()
        with self.assertRaises(ValueError):
            self.check((c, r, g, list(reversed(p))))

    def test_wrong_request_link(self):
        data = fixture()
        data[3][0]['request_id'] = 1
        with self.assertRaisesRegex(ValueError, 'linkage mismatch'):
            self.check(data)

    def test_missing_request_gate_metadata(self):
        data = fixture()
        data[1][1].pop('pfgen')
        with self.assertRaisesRegex(ValueError, 'request gate link'):
            self.check(data)

    def test_erasing_raw_receipts_also_cannot_erase_parent_map_draws(self):
        c, r, g, p = fixture()
        c[0]['pfgen_trace']['raw_stop'] = 0
        for request in r:
            request['pfgen']['raw_calls'] = []
        with self.assertRaisesRegex(ValueError, 'raw request coverage'):
            self.check((c, r, g, []))

    def test_missing_inner_draw_with_outer_row_retained(self):
        data = fixture()
        data[3][0]['draws'] = []
        with self.assertRaisesRegex(ValueError, 'inner raw draws'):
            self.check(data)

    def test_trace_cannot_be_added_to_non_pf_request(self):
        data = fixture()
        outside = dict(data[1][0], proposal_id=3)
        data[1].append(outside)
        with self.assertRaisesRegex(ValueError, 'out-of-scope'):
            self.check(data)

    def test_gate_only_needs_requests_but_no_raw_intervention(self):
        c, r, g, p = fixture()
        c[0]['pfgen_trace']['raw_stop'] = 0
        for request in r:
            request['pfgen']['raw_calls'] = []
        self.assertEqual(self.check((c, r, g, []), 'PF_GATE')['gate_queries'], 2)

    def test_no_pf_candidates_is_not_false_missing_coverage(self):
        self.assertEqual(self.check(([], [], [], []))['gate_queries'], 0)

    def test_trace_window_counter_independent_of_row_array(self):
        trace = Trace()
        trace.set_context(dict(generator_pf=True, event=0, candidate=0))
        trace.register_gate({})
        trace.gates.clear()
        trace.finish_context()
        self.assertEqual(trace.windows[0, 0]['gate_stop'], 1)


if __name__ == '__main__':
    unittest.main()
