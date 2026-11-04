"""Regression cases from the pre-push audit; no corpus/runtime dependency."""

from collections import Counter
from copy import deepcopy
from itertools import combinations
import unittest

from judges.features import Feature, extract
from judges.registry import ATOMS, CONFIG
from judges.schema import validate_case
from judges.scoring import aggregate_atoms, compare, digest, predict, validate_config
from judges.tests.test_panel import case, doc


class AuditRegressionTests(unittest.TestCase):
    def test_mix_joint_before_conditioning_rare_context(self):
        r1 = Feature(Counter({(('x',), 'a'): 90, (('z',), 'z'): 10}), True)
        r2 = Feature(Counter({(('x',), 'b'): 1, (('z',), 'z'): 99}), True)
        correct = Feature(Counter({(('x',), 'a'): 45, (('x',), 'b'): 1, (('z',), 'z'): 1}), True)
        wrong = Feature(Counter({(('x',), 'a'): 1, (('x',), 'b'): 2, (('z',), 'z'): 1}), True)
        result = compare([r1, r2, r2], correct, wrong)
        self.assertAlmostEqual(result['A'], 0)
        self.assertLess(result['B'], 0)
        self.assertGreater(result['delta'], 0)
        self.assertAlmostEqual(result['reference_context_coverage'], 1)

    def test_joint_mixture_is_invariant_to_whole_document_replication(self):
        r1 = Feature(Counter({(('x',), 'a'): 9, (('z',), 'z'): 1}), True)
        r2 = Feature(Counter({(('x',), 'b'): 1, (('z',), 'z'): 9}), True)
        a = Feature(Counter({(('x',), 'a'): 9, (('x',), 'b'): 1}), True)
        b = Feature(Counter({(('x',), 'a'): 1, (('x',), 'b'): 1}), True)
        before = compare([r1, r2], a, b)
        multiplied = Feature(Counter({k: 100*v for k, v in r1.counts.items()}), True)
        after = compare([multiplied, r2], a, b)
        self.assertAlmostEqual(before['delta'], after['delta'])

    def test_asymmetric_exclusion_mask_rejected(self):
        c = case()
        c['candidates']['B'] = {'lines': [{'paragraph': 0, 'segments': [], 'excluded': True}]}
        with self.assertRaisesRegex(ValueError, 'shared layout/exclusion'):
            validate_case(c)

    def test_shared_mask_is_allowed(self):
        c = case()
        for side in ('A', 'B'):
            c['candidates'][side]['lines'].append({'paragraph': 0, 'segments': [], 'excluded': True})
        validate_case(c)
        self.assertTrue(predict(c)['active_atoms'])

    def test_layout_mismatches_rejected(self):
        for change in ('plant', 'line', 'paragraph'):
            with self.subTest(change=change):
                c = case()
                if change == 'plant':
                    c['candidates']['B'] = doc(['qokar', 'daiin'], plant=True)
                elif change == 'line':
                    c['candidates']['B']['lines'].append(deepcopy(c['candidates']['B']['lines'][0]))
                else:
                    for side in ('A', 'B'):
                        c['candidates'][side]['lines'].append(deepcopy(c['candidates'][side]['lines'][0]))
                    c['candidates']['B']['lines'][-1]['paragraph'] = 1
                with self.assertRaisesRegex(ValueError, 'shared layout/exclusion'):
                    validate_case(c)

    def test_local_paragraph_id_names_do_not_change_layout(self):
        c = case()
        before = predict(c)
        c['candidates']['B']['lines'][0]['paragraph'] = 'local-name'
        after = predict(c)
        self.assertAlmostEqual(before['delta'], after['delta'])

    def test_all_unknown_document_rejected(self):
        c = case()
        c['candidates']['B'] = doc([None])
        with self.assertRaisesRegex(ValueError, 'observable glyphs'):
            validate_case(c)

    def test_no_comparable_atoms_rejected_instead_of_random_guess(self):
        c = case()
        c['candidates']['A'] = doc(['qokar', None], plant=True)
        c['candidates']['B'] = doc([None, 'daiin'], plant=True)
        validate_case(c)
        with self.assertRaisesRegex(ValueError, 'no comparable'):
            predict(c)

    def test_genuine_score_tie_remains_a_valid_contest(self):
        c = case()
        c['candidates']['B'] = deepcopy(c['candidates']['A'])
        result = predict(c)
        self.assertTrue(result['active_atoms'])
        self.assertTrue(result['final_tie'])

    def test_route_sharing_uses_two_page_subsets(self):
        refs = [doc(['qokar']), doc(['daiin']), doc(['chol'])]
        d = doc(['qokar'])
        result = extract(d, refs, 'stable22')['J17/share5'].counts
        self.assertAlmostEqual(result[(True, True)], 2/3)
        self.assertAlmostEqual(result[(True, False)], 1/3)
        expected = Counter()
        for pair in combinations(refs, 2):
            view = extract(d, list(pair), 'stable22')['J17/share5'].counts
            for key, value in view.items():
                expected[key] += value/3
        self.assertEqual(result.keys(), expected.keys())
        for key in expected:
            self.assertAlmostEqual(result[key], expected[key])

    def test_route_persistence_has_a_separate_state_per_pair(self):
        refs = [doc(['qokar']), doc(['daiin']), doc(['chol'])]
        d = doc(['qokar', 'qokar'])
        result = extract(d, refs, 'stable22')['J17/visible_persistence'].counts
        self.assertAlmostEqual(result['start'], .5)
        self.assertAlmostEqual(result['same'], .5)
        self.assertEqual(result['switch'], 0)

    def test_phw_only_weights_change_actual_prediction_delta(self):
        c = case()
        c['candidates']['B'] = doc(['ol', 'ol', 'ol'])
        default = predict(c)
        config = deepcopy(CONFIG)
        config['atom_weights'] = {a: float(a == 'PHW') for a in ATOMS}
        result = predict(c, config=config)
        self.assertAlmostEqual(result['delta'], default['views']['ATOM:PHW']['delta'])
        self.assertNotAlmostEqual(result['delta'], default['delta'])
        self.assertEqual(result['active_atoms'], ['PHW'])
        self.assertEqual(result['config_hash'], digest(config))
        self.assertNotEqual(result['config_hash'], default['config_hash'])

    def test_primary_atom_selection_is_applied(self):
        c = case()
        config = deepcopy(CONFIG)
        config['primary_atoms'] = ['PARA_END']
        config['atom_weights'] = {'PARA_END': 1}
        result = predict(c, config=config)
        self.assertEqual(result['active_atoms'], ['PARA_END'])
        self.assertAlmostEqual(result['delta'], result['views']['ATOM:PARA_END']['delta'])

    def test_weighted_mean_and_available_weight_renormalization(self):
        config = deepcopy(CONFIG)
        config['primary_atoms'] = ['PHW', 'FIRST_INTERIOR']
        config['atom_weights'] = {'PHW': 1, 'FIRST_INTERIOR': 3}
        views = {'ATOM:PHW': {'delta': 1}, 'ATOM:FIRST_INTERIOR': {'delta': -1}}
        self.assertAlmostEqual(aggregate_atoms(views, config)[0], -.5)
        views['ATOM:FIRST_INTERIOR']['delta'] = None
        self.assertEqual(aggregate_atoms(views, config), (1, ['PHW']))

    def test_invalid_weight_configs_rejected(self):
        for bad in (-1, float('nan'), float('inf'), True, 10**1000):
            with self.subTest(weight=bad):
                config = deepcopy(CONFIG)
                config['atom_weights']['PHW'] = bad
                with self.assertRaises(ValueError):
                    validate_config(config)
        config = deepcopy(CONFIG)
        config['atom_weights'] = {a: 0 for a in ATOMS}
        with self.assertRaises(ValueError):
            validate_config(config)
        for atoms in ([], ['PHW', 'PHW'], ['unknown']):
            config = deepcopy(CONFIG)
            config['primary_atoms'] = atoms
            with self.assertRaises(ValueError):
                validate_config(config)
        config = deepcopy(CONFIG)
        del config['atom_weights']['PHW']
        with self.assertRaises(ValueError):
            validate_config(config)


if __name__ == '__main__':
    unittest.main()
