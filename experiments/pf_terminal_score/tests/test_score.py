"""Standard-library unit fixtures. Native tokenizer, folds and LEN1 are in native_checks."""
import hashlib
import json
import math
import sys
import unittest
from types import SimpleNamespace
from unittest.mock import Mock, patch

from experiments.pf_terminal_score.score import EWeightSelector


class ScoreTests(unittest.TestCase):
    def setUp(self):
        # Recorded shape of one native call. Deliberately include both E= and EF=.
        self.keys = ("W=6", "WB=3", "WR=5", "E=ckh", "EF=OTHER")
        self.features = Mock(return_value=self.keys)
        self.enterContext(patch.dict(sys.modules, {
            "sel42_selectors": SimpleNamespace(pf_features=self.features),
        }))
        self.coefficients = dict(zip(self.keys, (8.0, -3.0, 1.5, -4.0, 11.0)))
        self.coefficients["E=h"] = 64.0
        self.parent = SimpleNamespace(kind="PF", intercept=2.0, coefficients=self.coefficients,
                                      score=Mock(return_value=15.5))
        self.args = ("ockh", 6, 12)

    def test_only_exact_terminal_changes_and_parent_dictionary_is_shared_intact(self):
        def payload_hash():
            payload = (self.parent.kind, self.parent.intercept, self.parent.coefficients)
            return hashlib.sha256(json.dumps(payload, sort_keys=True).encode()).digest()

        before = payload_hash()
        for weight, expected in ((0.0, 19.5), (0.5, 17.5), (1.0, 15.5), (0.5, 17.5)):
            with self.subTest(weight=weight):
                adapter = EWeightSelector(self.parent, weight)
                self.assertIs(adapter.original, self.parent)
                self.assertEqual(adapter.score(*self.args), expected)
                detail = adapter.breakdown(*self.args)
                self.assertEqual((detail.original_score, detail.adjusted_score), (15.5, expected))
                self.assertEqual((detail.terminal_key, detail.terminal_coefficient), ("E=ckh", -4.0))
                self.assertEqual(detail.intercept, 2.0)
                self.assertEqual(detail.feature_contributions,
                                 tuple(zip(self.keys, (8.0, -3.0, 1.5, -4.0, 11.0))))
                self.features.assert_called_with(*self.args)
                self.parent.score.assert_called_with(*self.args)
                self.assertIs(self.parent.coefficients, self.coefficients)
                self.assertEqual(payload_hash(), before)

    def test_identity_returns_original_object_before_a_second_feature_call(self):
        self.parent.score.return_value = -0.0
        score = EWeightSelector(self.parent, 1.0).score(*self.args)
        self.assertIs(score, self.parent.score.return_value)
        self.parent.score.assert_called_once_with(*self.args)
        self.features.assert_not_called()

    def test_missing_and_explicit_zero_return_original_signed_zero(self):
        self.parent.score.return_value = -0.0
        self.coefficients.pop("E=ckh")
        for present in (False, True):
            if present:
                self.coefficients["E=ckh"] = 0.0
            for weight in (0.0, 0.5):
                with self.subTest(present=present, weight=weight):
                    adapter = EWeightSelector(self.parent, weight)
                    self.assertIs(adapter.score(*self.args), self.parent.score.return_value)
                    detail = adapter.breakdown(*self.args)
                    self.assertEqual(detail.adjusted_score.hex(), "-0x0.0p+0")
                    self.assertEqual(detail.terminal_coefficient, 0.0)
                    self.assertEqual("E=ckh" in self.coefficients, present)

    def test_uses_specified_float_operation_order(self):
        self.coefficients["E=ckh"] = 0.2
        self.parent.score.return_value = 1.2
        score = EWeightSelector(self.parent, 0.5).score(*self.args)
        self.assertEqual(score.hex(), (1.2 + (-0.5) * 0.2).hex())
        self.assertNotEqual(score, (1.2 - 0.2) + 0.5 * 0.2)

    def test_refuses_unsupported_selectors_and_weights(self):
        for weight in (0.25, -1, 2, math.nan, math.inf, True, 1+0j, "0.5", None):
            with self.subTest(weight=weight), self.assertRaises(ValueError):
                EWeightSelector(self.parent, weight)
        for kind in ("PHW", "", "pf"):
            self.parent.kind = kind
            with self.subTest(kind=kind), self.assertRaises(ValueError):
                EWeightSelector(self.parent, 0.5)

    def test_rejects_nonfinite_inputs_and_scores_including_identity(self):
        for weight in (1.0, 0.5, 0.0):
            adapter = EWeightSelector(self.parent, weight)
            for method in (adapter.score, adapter.breakdown):
                self.parent.score.reset_mock()
                self.parent.score.return_value = 15.5
                for width, capacity in ((math.nan, 1), (1, math.inf)):
                    with self.assertRaises(ValueError):
                        method("n", width, capacity)
                self.parent.score.assert_not_called()
                self.parent.score.return_value = math.inf
                with self.assertRaises(ValueError):
                    method(*self.args)
        self.parent.score.return_value = sys.float_info.max
        self.coefficients["E=ckh"] = -sys.float_info.max
        with self.assertRaises(ValueError):
            EWeightSelector(self.parent, 0.0).score(*self.args)

    def test_rejects_nonfinite_frozen_payload(self):
        self.coefficients["unused"] = math.nan
        with self.assertRaises(ValueError):
            EWeightSelector(self.parent, 0.5)
        self.coefficients.clear()
        self.parent.intercept = math.inf
        with self.assertRaises(ValueError):
            EWeightSelector(self.parent, 1.0)

    def test_requires_one_individual_terminal_feature(self):
        for keys in (("EF=OTHER",), ("E=y", "EF=NMY", "E=y")):
            self.features.return_value = keys
            with self.subTest(keys=keys), self.assertRaises(ValueError):
                EWeightSelector(self.parent, 0.0).score(*self.args)


if __name__ == "__main__":
    unittest.main()
