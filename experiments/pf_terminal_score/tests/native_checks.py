"""Explicit frozen-runtime checks, including a fixed-bank native generate_bif fixture.

From the repository root with the v22.3 release sources restored, run
PYTHONPATH=HerbalA_v22_3_20260921/model/code python -m unittest experiments.pf_terminal_score.tests.native_checks
Missing core caches or mismatched source/payload hashes fail the checks.
"""
from collections import Counter
from copy import deepcopy
import json
import math
from pathlib import Path
import unittest
from unittest.mock import Mock, patch

import numpy as np
import pandas as pd

import run_v22_3_stage3d as source  # Initializes the native module search paths.
import bti2_patch_engine as engine
import sel42_selectors as selectors
from experiments.m1_pf.common import digest, file_hash
from experiments.pf_terminal_score.score import EWeightSelector

ROOT = Path(__file__).resolve().parents[3]
AUDIT = json.loads((ROOT / "sandbox/m1-review/reports/025-pf-exact-terminal-design-20261107"
                    / "SOURCE_AUDIT.json").read_text())


class FrozenScoreTests(unittest.TestCase):
    def test_five_frozen_payloads_all_glyphs_and_widths(self):
        for name, module in (("selector", selectors), ("engine", engine)):
            self.assertEqual(file_hash(module.__file__), AUDIT["source_files"][name]["sha256"])
        context = source.benv.e.context()
        self.assertEqual([row["fold"] for row in AUDIT["folds"]], list(range(5)))
        for row in AUDIT["folds"]:
            bif = row["representative_bif"]
            fc = source.FoldContext.create(context, row["fold"], bif, context.pages[bif][-1],
                                           "LEGACY_SCOPE", source.POLICY)
            core, metadata = source.load_core(context, fc)
            self.assertEqual(metadata["mode"], "FROZEN_18")
            self.assertEqual(metadata["sha256"], row["core_cache_sha256"])
            parent = core[5]
            coefficients = parent.coefficients
            self.assertEqual(digest(parent.to_dict()), row["selector_payload_sha256"])
            for weight in (1.0, 0.5, 0.0):
                adapter = EWeightSelector(parent, weight)
                for glyph in ("", *(engine.m.I2G[i] for i in range(22))):
                    key = "E=" + (glyph or "EMPTY")
                    e = coefficients.get(key, 0.0)
                    for width, capacity in ((1, 5), (5, 12), (12, 12)):
                        with self.subTest(fold=row["fold"], glyph=glyph, width=width, weight=weight):
                            args = (glyph, width, capacity)
                            s0 = parent.score(*args)
                            expected = s0 if weight == 1.0 or e == 0.0 else s0 + (weight - 1.0) * e
                            self.assertEqual(adapter.score(*args).hex(), expected.hex())
                            detail = adapter.breakdown(*args)
                            self.assertEqual(detail.original_score.hex(), s0.hex())
                            self.assertEqual(detail.adjusted_score.hex(), expected.hex())
                            self.assertEqual((detail.terminal_key, detail.terminal_coefficient), (key, e))
                            features = selectors.pf_features(*args)
                            self.assertEqual(detail.feature_contributions,
                                             tuple((k, coefficients.get(k, 0.0)) for k in features))
                            self.assertEqual(detail.intercept, parent.intercept)
            self.assertIs(parent.coefficients, coefficients)
            self.assertEqual(digest(parent.to_dict()), row["selector_payload_sha256"])
            del core

    def test_compound_uses_native_glyph_in_a_multiglyph_word(self):
        coefficients = {"E=ckh": 4.0, "E=ch": 2.0, "E=h": 96.0, "EF=OTHER": 8.0}
        parent = selectors.LinearSelector("PF", 1.0, coefficients, (), {})
        adapter = EWeightSelector(parent, 0.5)
        for surface, key, score in (("oickh", "E=ckh", 11.0), ("oich", "E=ch", 10.0)):
            self.assertEqual(adapter.breakdown(surface, 6, 12).terminal_key, key)
            self.assertEqual(adapter.score(surface, 6, 12), score)


# Only candidate completion is stubbed. The frozen engine owns all PF scoring,
# branch creation, eligibility, selection, sampler rebinding and RNG continuation.
INITIAL = (("aaaaay", 8), ("aaachn", 7))  # Six vs five *glyphs*.
RESCUE = (
    ("aaaaam", 7),  # First eligible at initial score - 1 under HALF.
    ("aaaaan", 6),  # Tie with first eligible.
    ("aaaaal", 7),  # Wrong family, higher score.
    ("aaaaay", 9),  # Too wide, higher score.
    ("aaaay", 7),   # Wrong length, higher score.
    ("aaaaam", 6),  # Below score floor.
    ("aaaaam", 7), ("aaaaan", 6),
)


class NativeLen1Tests(unittest.TestCase):
    def run_bank(self, weight, *, rescues=RESCUE, width6=1.5, width7=2.5):
        coefficients = {"W=6": width6, "W=7": width7, "W=9": 3.0,
                        "E=y": 4.0, "E=m": -2.0, "E=l": 8.0}
        parent = selectors.LinearSelector("PF", 0.0, coefficients, (), {})
        selector = parent if weight is None else EWeightSelector(parent, weight)
        bank = INITIAL + rescues
        attempts = []
        sampler = Mock(spec=["rebind"])
        rng = np.random.default_rng(91701)
        start = engine.GenerationState(rare={"budget": 10})
        schedule = pd.DataFrame([dict(bif="fixture", page="p", locus="p.1", para=1,
                                      segment_id=0, raw_para_final=True, boundary_type="LINE_END",
                                      para_line_raw=2, global_order=0)])

        def complete(sr, run, cdf, quad, models, sampler, br, state, *rest):
            j = len(attempts)
            word, width = bank[j]
            self.assertIsNot(state, start)
            self.assertEqual(state.digest(), start.digest())
            state.rare["budget"] -= j
            state.prev_h1["fixture"] = j
            br.random(j + 1)
            row = dict(stable_surface=word, surface="m", phys_width=width,
                       glyph_len=len(engine.m.v10.tokenize(word)), segment_capacity=12)
            branch = engine.SegmentResult([row], state, deepcopy(br.bit_generator.state),
                                          Counter(), [])
            attempts.append(branch)
            return branch

        with patch.object(engine, "complete_segment", complete):
            rows, _, final, _, log, _ = engine.generate_bif(
                91701, "fixture", None, None, schedule, None, sampler, rng, start, None, None, None,
                pf_selector=selector,
            )
        self.assertEqual([entry["candidate"] for entry in log], list(range(len(attempts))))
        for entry, (word, width) in zip(log, bank[:len(attempts)], strict=True):
            s0 = parent.score(word, width, 12)
            terminal = engine.m.I2G[engine.m.v10.tokenize(word)[-1]]
            e = coefficients.get("E=" + terminal, 0.0)
            expected = s0 if weight is None or weight == 1.0 or e == 0.0 else s0 + (weight - 1.0) * e
            self.assertEqual(entry["score"].hex(), expected.hex())
        selected, = [entry["candidate"] for entry in log if entry["selected"]]
        self.assertIs(final, attempts[selected].state)
        self.assertEqual(rows, attempts[selected].rows)
        sampler.rebind.assert_called_once_with(final)
        continuation, = [j for j, branch in enumerate(attempts)
                         if branch.rng_state == rng.bit_generator.state]
        return len(attempts), selected, continuation

    def test_reweighting_changes_initial_winner_and_rescue_trigger(self):
        for weight in (None, 1.0):
            self.assertEqual(self.run_bank(weight), (2, 0, 0))
        for weight in (0.5, 0.0):
            # Under HALF, rescue 2 is below initial winner 1 and has a different
            # exact terminal. Its state wins, but main RNG continues from 1.
            self.assertEqual(self.run_bank(weight), (10, 2, 1))

    def test_later_strictly_better_rescue_wins_and_later_tie_loses(self):
        rescues = RESCUE[:6] + (("aaaaan", 7), ("aaaaan", 7))
        self.assertEqual(self.run_bank(0.5, rescues=rescues), (10, 8, 1))

    def test_width_one_above_initial_is_allowed(self):
        rescues = (("aaaaay", 8),) * 8
        self.assertEqual(self.run_bank(0.5, rescues=rescues), (10, 2, 1))

    def test_initial_tie_and_one_ulp_above_tie(self):
        self.assertEqual(self.run_bank(0.5, width7=2.0), (2, 0, 0))
        count, _, continuation = self.run_bank(0.5, width7=math.nextafter(2.0, math.inf))
        self.assertEqual((count, continuation), (10, 1))

    def test_rescue_score_floor_is_inclusive_with_no_epsilon(self):
        rescues = (("aaaaan", 6),) * 8
        self.assertEqual(self.run_bank(0.5, rescues=rescues, width6=1.5), (10, 2, 1))
        below = math.nextafter(1.5, -math.inf)
        self.assertEqual(self.run_bank(0.5, rescues=rescues, width6=below), (10, 1, 1))


if __name__ == "__main__":
    unittest.main()
