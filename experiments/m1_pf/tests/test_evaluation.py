from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from experiments.m1_pf.evaluation import distance_summary, evaluate


def row(k, cluster, status, correct=None):
    return dict(set_id=k, cluster_id=cluster, status=status, correct=correct)


class EvaluationTests(unittest.TestCase):
    def test_ties_half_na_excluded_bifolia_equal_weight(self):
        left = [row('1', 'A', 'DECIDED', 1), row('2', 'A', 'DECIDED', 1),
                row('3', 'B', 'TIE'), row('4', 'C', 'NA')]
        right = [row('1', 'A', 'DECIDED', 0), row('2', 'A', 'DECIDED', 1),
                 row('3', 'B', 'TIE'), row('4', 'C', 'DECIDED', 1)]
        r = distance_summary(left, right, 100)
        self.assertEqual(r['paired_bifolia'], 2)
        self.assertEqual(r['paired_cases'], 3)
        self.assertEqual(r['left_rate'], .75)
        self.assertEqual(r['right_rate'], .5)
        self.assertEqual(r['distance_change'], -.25)
        self.assertEqual(r['status_transitions']['NA->DECIDED'], 1)

    def test_zero_comparable_does_not_become_chance(self):
        r = distance_summary([row('1', 'A', 'NA')], [row('1', 'A', 'TIE')], 100)
        self.assertIsNone(r['left_rate'])
        self.assertIsNone(r['distance_change'])

    def test_below_chance_is_symmetric_and_direction_reversal_reported(self):
        r = distance_summary([row('1', 'A', 'DECIDED', 0)], [row('1', 'A', 'DECIDED', 1)], 100)
        self.assertEqual(r['distance_change'], 0.)
        self.assertTrue(r['direction_reversal'])

    def test_mismatched_or_duplicate_trials_rejected(self):
        with self.assertRaises(ValueError):
            distance_summary([row('1', 'A', 'NA')], [row('2', 'A', 'NA')], 100)
        with self.assertRaises(ValueError):
            distance_summary([row('1', 'A', 'NA')] * 2, [row('1', 'A', 'NA')], 100)

    def test_wrong_frozen_cal_model_rejected_before_output_or_predictions(self):
        with tempfile.TemporaryDirectory() as td:
            output = Path(td) / 'results'
            with patch('experiments.m1_pf.evaluation.load_plan', return_value={'required_model_set_hash': 'required'}), \
                 patch('judges.v03.calibration.load_models', return_value=({}, {})), \
                 patch('judges.v03.artifacts.predict_file') as predictor:
                with self.assertRaisesRegex(ValueError, 'Frozen CAL model'):
                    evaluate('plan', 'inputs', 'models', output)
                predictor.assert_not_called()
                self.assertFalse(output.exists())
