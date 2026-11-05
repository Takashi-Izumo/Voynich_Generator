"""Design regression: CAL is central null typicality, not monotone distance."""
import unittest

from judges.v03.calibration import typicality
from judges.v03.protocol import DEFAULT


class CalibrationDirectionTests(unittest.TestCase):
    def null_rows(self):
        n = max(DEFAULT['fitting']['min_null_bifolia'], DEFAULT['fitting']['min_null_target_pages'], 20)
        return [dict(cluster_id=str(i), distance=float(i), n=20) for i in range(n)]

    def test_central_null_scores_above_both_tails(self):
        rows = self.null_rows()
        left, _ = typicality(rows, -1., 20)
        center, _ = typicality(rows, (len(rows) - 1) / 2, 20)
        right, _ = typicality(rows, len(rows) + 1., 20)
        self.assertEqual(left, 0.)
        self.assertEqual(right, 0.)
        self.assertGreater(center, .9)

    def test_increasing_distance_from_lower_tail_can_increase_cal(self):
        rows = self.null_rows()
        near, _ = typicality(rows, -1., 20)
        farther, _ = typicality(rows, (len(rows) - 1) / 2, 20)
        self.assertLess(near, farther)


if __name__ == '__main__':
    unittest.main()
