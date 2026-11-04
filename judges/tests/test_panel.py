from collections import Counter
from copy import deepcopy
import json
from pathlib import Path
import tempfile
import unittest

from judges.contest import run_predict, run_score, summarize, write_jsonl
from judges.features import Feature, extract
from judges.registry import ATOMS, NAMES
from judges.schema import events, glyphs, validate_case
from judges.scoring import CONFIG_HASH, aggregate, compare, jsd, predict


def doc(words, *, plant=False):
    segs = [{'end': 'LINE_END', 'tokens': words}]
    if plant:
        segs = [{'end': 'PLANT', 'tokens': words[:1]}, {'end': 'LINE_END', 'tokens': words[1:]}]
    return {'lines': [{'paragraph': 0, 'segments': segs}]}


def case():
    a = doc(['qokar', 'daiin', 'ol', 'chol', 'qotar'])
    b = doc(['qokar', 'daiin', 'chol', 'ol', 'qotar'])
    return {'schema_version': 1, 'set_id': 'toy-001', 'cluster_id': 'toy-cluster', 'seed': 1,
            'text_profile': 'stable22', 'known': [a, doc(['daiin','chol','qokar']), doc(['qotar','ol','daiin'])],
            'candidates': {'A': a, 'B': b}}


class PanelTests(unittest.TestCase):
    def test_glyphs_and_unknown(self):
        self.assertEqual(glyphs('chom'), ('ch','o','m'))
        self.assertEqual(glyphs('bgchom'), ('ch','o','m'))
        self.assertIsNone(glyphs('?'))

    def test_plant_is_closed_but_not_physical_lf(self):
        d = doc(['qokar','daiin','chol'], plant=True)
        e = events(d)
        self.assertEqual([x.boundary for x in e], ['P','I','L'])
        self.assertIsNone(e[1].prev)
        self.assertEqual(e[1].role, 'BODY')
        f = extract(d, [], 'stable22')
        self.assertEqual(sum(f['J22/plant_end/word'].counts.values()), 1)
        self.assertEqual(sum(f['J06/word'].counts.values()), 1)

    def test_unknown_does_not_create_head_or_space(self):
        d = doc([None,'qokar',None,'daiin'])
        e = events(d)
        self.assertEqual(e[1].ordinal, 1)
        self.assertIsNone(e[1].prev)
        self.assertIsNone(e[3].prev)
        f = extract(d, [], 'stable22')
        self.assertNotIn('J01/word', f)
        self.assertNotIn('J15/T_H1', f)
        self.assertNotIn('J25/word_pair', f)

    def test_single_line_single_word_has_both_flags(self):
        e = events(doc(['daiin']))[0]
        self.assertTrue(e.first and e.final)
        self.assertEqual(e.boundary, 'L')
        self.assertEqual(e.atom, 'PARA_END')

    def test_atoms_form_a_partition(self):
        d = doc(['qokar','daiin','chol'], plant=True)
        d['lines'].append({'paragraph': 0, 'segments': [{'end':'LINE_END','tokens':['ol','qotar','daiin']}]})
        f = extract(d, [], 'stable22')
        self.assertEqual(sum(sum(f.get('ATOM:'+a+'/word', Feature()).counts.values()) for a in ATOMS), 6)

    def test_excluded_line_prevents_false_vertical_adjacency(self):
        d = doc(['daiin'])
        d['lines'] += [{'paragraph':0,'segments':[],'excluded':True}, doc(['qokar'])['lines'][0]]
        self.assertNotIn('J10/vertical', extract(d, [], 'stable22'))

    def test_conditional_score_is_not_joint_score(self):
        r = Feature(Counter({(('a',),'x'):10, (('b',),'y'):10}), True)
        a = Feature(Counter({(('a',),'x'):100, (('b',),'y'):1}), True)
        b = Feature(Counter({(('a',),'x'):1, (('b',),'y'):100}), True)
        s = compare([r], a, b)
        self.assertAlmostEqual(s['A'], 0)
        self.assertAlmostEqual(s['B'], 0)

    def test_empty_is_na(self):
        self.assertIsNone(compare([Feature()], Feature(), Feature())['delta'])
        with self.assertRaises(ValueError):
            jsd(Counter(), Counter())

    def test_candidate_swap(self):
        c = case()
        a = predict(c)
        c['candidates'] = {'A':c['candidates']['B'], 'B':c['candidates']['A']}
        b = predict(c)
        for k in a['channels']:
            x, y = a['channels'][k]['delta'], b['channels'][k]['delta']
            if x is None:
                self.assertIsNone(y)
            else:
                self.assertAlmostEqual(x, -y)
        if not a['final_tie']:
            self.assertNotEqual(a['prediction'], b['prediction'])

    def test_known_order(self):
        c = case()
        a = predict(c)
        c['known'].reverse()
        b = predict(c)
        self.assertAlmostEqual(a['delta'], b['delta'])

    def test_informative_primary_swap_and_neutral_ties(self):
        c = case()
        c['candidates']['B'] = doc(['ol','ol','ol'])
        a = predict(c)
        self.assertFalse(a['final_tie'])
        c['candidates'] = {'A':c['candidates']['B'], 'B':c['candidates']['A']}
        b = predict(c)
        self.assertAlmostEqual(a['delta'], -b['delta'])
        self.assertNotEqual(a['prediction'], b['prediction'])
        self.assertGreater(aggregate([1.0]+[0.0]*15), 0)

    def test_word_order_is_visible_to_J25(self):
        c = case()
        a = extract(c['candidates']['A'], c['known'], 'stable22')
        b = extract(c['candidates']['B'], c['known'], 'stable22')
        self.assertEqual(a['J23/global/word'].counts, b['J23/global/word'].counts)
        self.assertNotEqual(a['J25/word_pair'].counts, b['J25/word_pair'].counts)

    def test_order_information_reaches_primary_without_random_tie_votes(self):
        c = case()
        c['known'] = [deepcopy(c['candidates']['A']) for _ in range(3)]
        p = predict(c)
        self.assertFalse(p['final_tie'])
        self.assertGreater(p['delta'], 0)
        self.assertEqual(p['prediction'], 'A')

    def test_all_views_and_raw_profile(self):
        c = case()
        p = predict(c)
        self.assertTrue(set(NAMES) <= p['views'].keys())
        self.assertEqual(p['views']['J21']['status'], 'NA')
        c['text_profile'] = 'raw'
        c['candidates']['A']['lines'][0]['segments'][0]['tokens'][0] = 'gqokar'
        self.assertIn('J21/rare_presence', predict(c)['channels'])

    def test_answer_fields_rejected(self):
        c = case()
        c['truth'] = 'A'
        with self.assertRaises(ValueError):
            validate_case(c)

    def test_invalid_schema_boundaries(self):
        c = case()
        c['candidates']['A']['lines'][0]['segments'][0]['end'] = 'PLANT'
        with self.assertRaises(ValueError):
            validate_case(c)

    def test_primary_accuracy_not_margin_sign(self):
        predictions, keys = [], []
        for i in range(11):
            predictions.append({'set_id':str(i), 'cluster_id':'one' if i<10 else 'two', 'seed':i, 'config_hash':CONFIG_HASH, 'prediction':'A', 'final_tie':False})
            keys.append({'set_id':str(i),'truth':'A' if i<9 else 'B'})
        s = summarize(predictions, keys, 100)
        self.assertAlmostEqual(s['cluster_equal_weight_accuracy'], .45)
        self.assertAlmostEqual(s['raw_accuracy'], 9/11)

    def test_seal_reveal_and_tampering(self):
        with tempfile.TemporaryDirectory() as t:
            root = Path(t)
            write_jsonl(root/'input.jsonl', [case()])
            run_predict(root/'input.jsonl', root/'sealed')
            # Deliberately no key existed when predictions were sealed.
            write_jsonl(root/'key.jsonl', [{'set_id':'toy-001','truth':'A'}])
            s = run_score(root/'sealed', root/'key.jsonl', root/'scores', 100)
            self.assertEqual(s['sets'], 1)
            self.assertIsNone(s['cluster_bootstrap_percentile_95'])
            self.assertEqual(s['diagnostic_views']['J24']['decision_coverage'], 1)
            with self.assertRaises(FileExistsError):
                run_predict(root/'input.jsonl', root/'sealed')
            (root/'sealed/predictions.jsonl').write_text('{}\n')
            with self.assertRaises(ValueError):
                run_score(root/'sealed', root/'key.jsonl', root/'bad', 100)

    def test_wrong_key_and_duplicate_trial_rejected(self):
        p = predict(case())
        with self.assertRaises(ValueError):
            summarize([p], [{'set_id':'other','truth':'A'}], 100)
        q = deepcopy(p); q['set_id'] = 'different-id'
        with self.assertRaises(ValueError):
            summarize([p,q], [{'set_id':p['set_id'],'truth':'A'},{'set_id':q['set_id'],'truth':'B'}], 100)


if __name__ == '__main__':
    unittest.main()
