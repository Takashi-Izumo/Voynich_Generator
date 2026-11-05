from collections import Counter
from copy import deepcopy
from types import SimpleNamespace as NS
import unittest

import numpy as np
import pandas as pd

from judges.schema import GLYPHS, glyphs
from experiments.m1_pf.common import digest
from experiments.m1_pf.overlay import Overlay, terminal_facts


class State:
    def __init__(self):
        self.rare = {'budget': 100, 'used': set()}
        self.line_counts = {}
        self.prev_h1 = {}
        self.phw_cache = []
        self.motion = NS(history=[], step=0)

    def clone(self):
        return deepcopy(self)

    def digest(self):
        # Deliberately incomplete, like the legacy digest: the overlay must use
        # its full snapshot to detect a mutable payload leak.
        return 'LEGACY_DIGEST'


class Sampler:
    def __init__(self):
        self.base = NS(state=None)
        self.state = None
        self.last_request = None
        self.word_first_request = 0
        self.next_proposal_id = 0

    def rebind(self, state):
        self.state = self.base.state = state.motion


class Engine:
    PF_K = 2
    PF_RESCUE_EXTRA = 8
    PF_RESCUE_MAX_BASE_LEN = 5
    PF_RESCUE_TOL = 1.

    def __init__(self, scores=None, leak=None):
        self.calls = 0
        self.scores = scores or {'oin': 5., 'aiin': 6., 'aiiiy': 5.5, 'aiiin': 5.5, 'or': 0.}
        self.words = ['oin', 'aiin', 'aiiiy', 'aiiin'] + ['or'] * 6
        self.leak = leak
        self.m = NS(I2G=dict(enumerate(GLYPHS)),
                    v10=NS(tokenize=lambda s: tuple(GLYPHS.index(g) for g in glyphs(s))),
                    keyed_rng=lambda *a: np.random.default_rng(1000 + int(a[-2])))

    @staticmethod
    def is_pf(sr):
        return bool(sr.raw_para_final) and sr.boundary_type == 'LINE_END' and sr.para_line_raw >= 2

    @staticmethod
    def clone_rng(rng):
        out = np.random.default_rng()
        out.bit_generator.state = deepcopy(rng.bit_generator.state)
        return out

    @staticmethod
    def _rescue_ok(seq, width, score, base, bw, bs, tol, phw):
        return len(seq) == len(base) + 1 and width <= bw + 1 and score >= bs - tol

    def complete_segment(self, sr, run, cdf, quad, models, sampler, rng, state, *rest):
        j = self.calls
        self.calls += 1
        rng.random(j + 1)
        if self.leak:
            self.leak()
        state.rare['budget'] -= j
        state.motion.history.append(j)
        sampler.rebind(state)
        sampler.last_request = {'candidate': j}
        sampler.word_first_request = j
        sampler.next_proposal_id += 1
        word = self.words[j]
        row = dict(surface=word, stable_surface=word, phys_width=len(glyphs(word)),
                   glyph_len=len(glyphs(word)), segment_capacity=10)
        return NS(rows=[row], state=state, rng_state=deepcopy(rng.bit_generator.state),
                  stats=Counter(reject=j), phw_candidates=[])


def run(arm, engine=None, state=None, sampler=None, rng=None, segment=None):
    engine = engine or Engine()
    overlay = Overlay(engine, arm)
    rng = rng if rng is not None else np.random.default_rng(321)
    state, sampler = state or State(), sampler or Sampler()
    row = dict(bif='A:2', page='f7v', locus='f7v.4', para=1, segment_id=0,
               raw_para_final=True, boundary_type='LINE_END', para_line_raw=4, global_order=1)
    row.update(segment or {})
    seg = pd.DataFrame([row])
    selector = NS(score=lambda s, w, c: engine.scores[s])
    result = overlay(91701, 'A:2', None, None, seg, None, sampler, rng, state, None, None, None,
                     pf_selector=selector)
    return overlay, result, sampler, rng


class OverlayTests(unittest.TestCase):
    def test_base_rescue_commits_rescue_state_but_argmax_rng(self):
        overlay, result, sampler, rng = run('BASE')
        event = overlay.events[0]
        self.assertEqual(event['chosen'], 2)
        self.assertEqual(event['continuation_candidate'], 1)
        self.assertEqual(result[2].rare['budget'], 98)
        self.assertEqual(result[0][0]['surface'], 'aiiiy')  # n -> y retains NMY, not exact terminal.
        self.assertEqual(digest(rng.bit_generator.state), overlay.candidates[1]['rng_exit_sha256'])
        self.assertNotEqual(digest(rng.bit_generator.state), overlay.candidates[2]['rng_exit_sha256'])
        self.assertIs(sampler.state, result[2].motion)
        self.assertEqual(sampler.last_request['candidate'], 2)
        self.assertEqual(len(overlay.candidates), 10)

    def test_no_rescue_keeps_initial_argmax_and_generates_exactly_two(self):
        overlay, result, sampler, rng = run('PF_NO_RESCUE')
        self.assertEqual(overlay.events[0]['chosen'], 1)
        self.assertEqual(len(overlay.candidates), 2)
        self.assertEqual(result[2].rare['budget'], 99)

    def test_anchor_records_candidate1_but_commits_candidate0_and_its_rng(self):
        overlay, result, sampler, rng = run('PF_ANCHOR')
        self.assertEqual(overlay.events[0]['original_argmax'], 1)
        self.assertEqual(overlay.events[0]['chosen'], 0)
        self.assertEqual(result[2].rare['budget'], 100)
        self.assertEqual(digest(rng.bit_generator.state), overlay.candidates[0]['rng_exit_sha256'])
        self.assertEqual(len(overlay.candidates), 2)

    def test_initial_tie_prefers_candidate0(self):
        e = Engine(); e.scores['aiin'] = e.scores['oin']
        overlay, *_ = run('PF_NO_RESCUE', e)
        self.assertEqual(overlay.events[0]['chosen'], 0)

    def test_hidden_mutable_parent_payload_leak_is_rejected(self):
        state = State()
        engine = Engine(leak=lambda: state.motion.history.append('LEAK'))
        with self.assertRaisesRegex(AssertionError, 'contaminated'):
            run('BASE', engine, state=state)

    def test_main_rng_leak_is_rejected(self):
        rng = np.random.default_rng(321)
        with self.assertRaisesRegex(AssertionError, 'contaminated'):
            run('BASE', Engine(leak=lambda: rng.random()), rng=rng)

    def test_unknown_pending_field_fails_closed(self):
        sampler = Sampler(); sampler.pending_future_candidate = [1]
        with self.assertRaisesRegex(ValueError, 'Unaudited sampler'):
            run('BASE', sampler=sampler)

    def test_visible_m_and_compound_glyph_threshold_crossings(self):
        row = dict(stable_surface='choiin', surface='choiim', phys_width=6, segment_capacity=9)
        facts = terminal_facts(row, Engine())
        self.assertEqual(facts['stable_glyph_length'], 5)
        self.assertEqual(facts['visible_m'], 1)
        self.assertEqual(facts['visible_terminal'], 'm')
        row['surface'] = 'choiinm'
        self.assertEqual(terminal_facts(row, Engine())['visible_length_crossings'], [5])

    def test_pf_boundary_population(self):
        for final, boundary, line, expected in [(True, 'LINE_END', 2, True), (True, 'PLANT', 2, False),
                                                (True, 'LINE_END', 1, False), (False, 'LINE_END', 3, False)]:
            e = Engine()
            overlay, *_ = run('PF_NO_RESCUE', e, segment=dict(raw_para_final=final, boundary_type=boundary, para_line_raw=line))
            self.assertEqual(len(overlay.events), int(expected))
            self.assertEqual(e.calls, 2 if expected else 1)
