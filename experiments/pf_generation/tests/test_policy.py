from copy import deepcopy
from dataclasses import FrozenInstanceError
from types import SimpleNamespace
import unittest

import numpy as np

from experiments.pf_generation.common import digest
from experiments.pf_generation.gate import GateAdapter
from experiments.pf_generation.laws import Law, fit_length_gains, fit_offsets
from experiments.pf_generation.proposal import Trace, sampler_class


class State:
    row_phase = 'FINAL'
    word_index = 3

    def semantic_digest(self):
        return digest(dict(phase=self.row_phase, index=self.word_index))


class RawParent:
    def __init__(self, base, tables, patch):
        self.parent = base
        self.state = State()
        self.calls = 0

    def __call__(self, *args, **kwargs):
        self.calls += 1
        return self.parent(args[5])


class FakeRNG:
    def __init__(self, value):
        self.value = value
        self.bit_generator = SimpleNamespace(state={'counter': 0})

    def random(self):
        self.bit_generator.state['counter'] += 1
        return self.value


def build(law, generator=lambda rng: (0,)):
    m = SimpleNamespace(stable_width=len, word_str=lambda seq: 'q' * len(seq))
    trace = Trace()
    cls = sampler_class(RawParent, m)
    return cls(generator, None, None, law, trace), trace


def call(sampler, rng, pl=2, end=True, boundary=True):
    return sampler(None, None, 'BODY', pl, 1, rng, 9, None, None, None, end, None,
                   line_end_boundary=boundary)


IDENTITY = Law((0.,) * 4, ((1.,) * 4,) * 3)
WEIGHTED = Law((0.,) * 4, ((.25,) * 4, (4.,) * 4, (1.,) * 4))


class ProposalTests(unittest.TestCase):
    def test_identity_matches_parent_output_and_rng(self):
        generate = lambda rng: (int(rng.integers(22)),)
        sampler, trace = build(IDENTITY, generate)
        rng, reference = np.random.default_rng(17), np.random.default_rng(17)
        self.assertEqual(call(sampler, rng), generate(reference))
        self.assertEqual(rng.bit_generator.state, reference.bit_generator.state)
        self.assertEqual(sampler.calls, 1)
        self.assertIsNone(trace.proposals[0]['draws'][0]['uniform'])

    def test_fallback_is_first_anchor_and_bounded(self):
        count = iter(range(32))
        sampler, trace = build(WEIGHTED, lambda rng: (next(count),))
        self.assertEqual(call(sampler, FakeRNG(.99)), (0,))
        self.assertEqual(sampler.calls, 32)
        self.assertTrue(trace.proposals[0]['fallback'])
        self.assertEqual(len(trace.proposals[0]['draws']), 32)

    def test_supported_accepted_draw_returned(self):
        sampler, trace = build(WEIGHTED, lambda rng: (2,) * 5)
        self.assertEqual(call(sampler, FakeRNG(.99)), (2,) * 5)
        self.assertEqual(sampler.calls, 1)
        self.assertFalse(trace.proposals[0]['fallback'])

    def test_scope_excludes_plant_first_line_and_continue(self):
        for kwargs in [dict(pl=1), dict(end=False), dict(boundary=False)]:
            with self.subTest(kwargs=kwargs):
                sampler, trace = build(WEIGHTED)
                rng = FakeRNG(.99)
                call(sampler, rng, **kwargs)
                self.assertEqual(sampler.calls, 1)
                self.assertEqual(rng.bit_generator.state['counter'], 0)
                self.assertFalse(trace.proposals)

    def test_scope_excludes_nonfinal_paragraph(self):
        sampler, trace = build(WEIGHTED)
        sampler.state.row_phase = 'MIDDLE'
        call(sampler, FakeRNG(.99))
        self.assertFalse(trace.proposals)

    def test_empty_word_keeps_parent_retry_path_and_rng(self):
        sampler, trace = build(WEIGHTED, lambda rng: ())
        rng = FakeRNG(.99)
        self.assertEqual(call(sampler, rng), ())
        self.assertEqual(rng.bit_generator.state['counter'], 0)
        self.assertEqual(sampler.calls, 1)

    def test_raw_semantic_mutation_is_rejected(self):
        sampler, trace = build(IDENTITY)
        def corrupt(rng):
            sampler.state.word_index += 1
            return (0,)
        sampler.parent = corrupt
        with self.assertRaisesRegex(ValueError, 'semantic state'):
            call(sampler, np.random.default_rng(0))

    def test_trace_context_does_not_choose_candidates(self):
        sampler, trace = build(WEIGHTED)
        trace.context = {'candidate': 300, 'untrusted': 'observation only'}
        self.assertEqual(call(sampler, FakeRNG(0)), (0,))


class LawTests(unittest.TestCase):
    def test_law_is_deeply_immutable(self):
        with self.assertRaises(FrozenInstanceError):
            IDENTITY.theta = (1.,) * 4
        with self.assertRaises(TypeError):
            IDENTITY.gains[0][0] = 2.

    def test_nonfinite_or_out_of_bounds_law_rejected(self):
        for bad in [float('nan'), 0., 4.1]:
            with self.subTest(bad=bad), self.assertRaises(ValueError):
                Law.load(dict(theta=[0.] * 4, gains=[[bad] * 4] * 3))

    def test_missing_training_bin_backs_off(self):
        pf, ordinary = np.zeros((3, 4)), np.zeros((3, 4))
        pf[2, 2], ordinary[1, 2] = 12, 30
        gains = np.array(fit_length_gains(pf, ordinary))
        np.testing.assert_array_equal(gains[:, [0, 1, 3]], np.ones((3, 3)))
        self.assertTrue((gains > 0).all())
        self.assertGreater(gains[2, 2], gains[1, 2])

    def test_gate_recovers_offset_direction_and_empty_bins(self):
        theta = fit_offsets(np.zeros(10), [1] * 8 + [0] * 2, [1] * 10, np.ones(10))
        self.assertGreater(theta[1], 0)
        self.assertEqual([theta[0], theta[2], theta[3]], [0., 0., 0.])
        p = 1 / (1 + np.exp(-theta[1]))
        self.assertAlmostEqual(10 * p - 8 + 20 * theta[1], 0, places=8)


class GateTests(unittest.TestCase):
    @staticmethod
    def m():
        import math
        return SimpleNamespace(sigmoid=lambda v: 1 / (1 + math.exp(-max(-30, min(30, v)))),
                               logit=lambda p: math.log(p / (1 - p)), FINAL_SEG_CLOSE_GAIN=.8)

    def test_identity_preserves_parent_probabilities_exactly(self):
        p = np.array([[.3, .7], [.01, .99]])
        parent = SimpleNamespace(predict_proba=lambda x: p)
        events = []
        adapter = GateAdapter(parent, IDENTITY, self.m(), {'split_end': False}, events)
        np.testing.assert_array_equal(adapter.predict_proba([[5, 0, 0, 20], [8, 0, 0, 20]]), p)
        self.assertEqual(len(events), 2)

    def test_split_gain_is_recorded_once_after_offset(self):
        p = np.array([[.5, .5]])
        parent = SimpleNamespace(predict_proba=lambda x: p)
        events = []
        m = self.m()
        law = Law((1.,) * 4, IDENTITY.gains)
        adapter = GateAdapter(parent, law, m, {'split_end': True}, events)
        result = adapter.predict_proba([[5, 0, 0, 20]])
        self.assertAlmostEqual(result[0, 1], m.sigmoid(1.))
        import math
        self.assertAlmostEqual(events[0]['engine_probability'], m.sigmoid(1. + math.log(.8)))


if __name__ == '__main__':
    unittest.main()
