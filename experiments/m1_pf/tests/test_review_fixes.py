"""Regression reproductions of the independent review's four findings."""
from copy import deepcopy
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from experiments.m1_pf import ARMS
from experiments.m1_pf.audit import audit, final_rng, generation_binding
from experiments.m1_pf.common import digest, file_hash, write_json
from experiments.m1_pf.evaluation import audited
from experiments.m1_pf.inputs import verify_tree
from experiments.m1_pf.plan import endpoint_observation_map
from judges.v03.observations import endpoints, word_events


class ExpandedInputTests(unittest.TestCase):
    def test_configuration_change_is_rejected(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            p = root / 'FROZEN_FOLD_CONFIGS.json'
            p.write_text('{"beta":1}')
            expected = {p.name: {'bytes': p.stat().st_size, 'sha256': file_hash(p)}}
            verify_tree(root, expected)
            p.write_text('{"beta":2}')  # Same size, changed generation settings.
            with self.assertRaisesRegex(ValueError, 'runtime input changed'):
                verify_tree(root, expected)

    def test_additional_or_missing_input_is_rejected(self):
        with tempfile.TemporaryDirectory() as td:
            p = Path(td) / 'new_selector.json'; p.write_text('{}')
            with self.assertRaisesRegex(ValueError, 'input set changed'):
                verify_tree(td, {})

    def test_compiler_outputs_are_not_generation_inputs(self):
        with tempfile.TemporaryDirectory() as td:
            p = Path(td) / '__pycache__'; p.mkdir(); (p / 'a.pyc').write_bytes(b'cache')
            self.assertEqual(verify_tree(td, {})['files'], 0)


def document(mode, full, end='LINE_END'):
    frame = dict(whole_line_usable=full, paragraph=1, paragraph_line=2, paragraph_final=True,
                 segments=[{'end': end}])
    segment = {'mode': mode}
    if mode == 'FULL': segment['tokens'] = ['daiin', 'chol']
    if mode == 'END_ONLY': segment['end_word'] = 'chol'
    return {'layout': {'lines': [frame]}, 'observations': {'lines': [{'segments': [segment]}]}}


class ScopeTests(unittest.TestCase):
    def test_end_only_usable_by_endpoint_views_but_not_atoms(self):
        doc = document('END_ONLY', False)
        self.assertEqual(len(endpoints(doc)), 1)
        self.assertEqual(word_events(doc), [])
        self.assertEqual(endpoint_observation_map(doc), {})

    def test_full_atoms_match_frozen_judge(self):
        for boundary, expected in [('LINE_END', 'PARA_END'), ('PLANT', 'PLANT_END')]:
            doc = document('FULL', True, boundary)
            self.assertEqual(endpoint_observation_map(doc), {(0, 0): expected})

    def test_none_is_not_an_observed_endpoint(self):
        doc = document('NONE', False)
        self.assertFalse(endpoints(doc))
        self.assertFalse(endpoint_observation_map(doc))


class SealAndRngTests(unittest.TestCase):
    def fixture(self, root, reference=False):
        plan = {'plan_hash': 'fixed', 'bifolia': ['A:2'], 'runs': [91701]}
        records = []
        for arm in list(ARMS) + (['REFERENCE'] if reference else []):
            d = root / arm; d.mkdir()
            (d / 'token.data').write_text('original')
            records.append({'arm': arm, 'bif': 'A:2', 'run': 91701, 'path': arm,
                            'files': {'token.data': file_hash(d / 'token.data')}})
        write_json(root / 'plan.json', plan)
        write_json(root / 'STATUS.json', {'status': 'GENERATED_NOT_AUDITED', 'plan_hash': 'fixed'})
        write_json(root / 'manifest.json', {'plan_hash': 'fixed', 'records': records})
        self.seal(root, plan)
        return plan

    def seal(self, root, plan):
        binding = generation_binding(plan, root)
        report = root / 'report.json'
        write_json(report, {'schema_version': 2, 'plan_hash': 'fixed', 'status': 'PASS',
                            'generation_binding': binding, 'base_reference_checked': True,
                            'base_reference_main_rng_checked': True, 'repeat_checked': False})
        write_json(root / 'AUDIT.json', {'schema_version': 2, 'plan_hash': 'fixed',
                                        'generation_binding': binding, 'report': str(report),
                                        'report_sha256': file_hash(report)})

    def test_checksum_refresh_cannot_reuse_old_pass(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td); plan = self.fixture(root)
            with patch('experiments.m1_pf.evaluation.load_plan', return_value=plan):
                self.assertEqual(audited('plan', root), plan)
                p = root / 'BASE/token.data'; p.write_text('changed')
                m = json.loads((root / 'manifest.json').read_text())
                m['records'][0]['files']['token.data'] = file_hash(p)
                write_json(root / 'manifest.json', m)
                # All current per-file checksums are correct; the earlier PASS
                # still belongs to the previous manifest and must be rejected.
                generation_binding(plan, root)
                with self.assertRaisesRegex(ValueError, 'audit seal'):
                    audited('plan', root)

    def test_refreshing_seal_binding_alone_cannot_rebind_old_report(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td); plan = self.fixture(root)
            m = json.loads((root / 'manifest.json').read_text());m['note'] = 'new receipt'
            write_json(root / 'manifest.json', m)
            seal = json.loads((root / 'AUDIT.json').read_text())
            seal['generation_binding'] = generation_binding(plan, root)
            write_json(root / 'AUDIT.json', seal)
            with patch('experiments.m1_pf.evaluation.load_plan', return_value=plan):
                with self.assertRaisesRegex(ValueError, 'passing mechanical audit'):
                    audited('plan', root)

    def write_rng(self, path, state):
        write_json(path / 'M1_FINAL.json', {'final_main_rng_state': state,
                                          'final_main_rng_sha256': digest(state), 'final_state_sha256': 'same'})
        write_json(path / 'MECHANICAL.json', {'rng_end': state})

    def test_final_rng_must_match_mechanical_audit(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td);self.write_rng(root, {'state': 1})
            self.assertEqual(final_rng(root), {'state': 1})
            write_json(root / 'MECHANICAL.json', {'rng_end': {'state': 2}})
            with self.assertRaisesRegex(ValueError, 'differs from generator audit'):
                final_rng(root)

    def test_base_reference_rng_has_explicit_comparison(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td);plan = self.fixture(root, reference=True)
            for arm in list(ARMS) + ['REFERENCE']:
                self.write_rng(root / arm, {'state': 2 if arm == 'REFERENCE' else 1})
            m = json.loads((root / 'manifest.json').read_text())
            for row in m['records']:
                d = root / row['path'];row['files'] = {p.name: file_hash(p) for p in d.iterdir()}
            write_json(root / 'manifest.json', m)
            self.seal(root, plan)
            with patch('experiments.m1_pf.audit.load_plan', return_value=plan), \
                 patch('experiments.m1_pf.audit.audit_case', return_value={}), \
                 patch('experiments.m1_pf.audit.semantic_case', return_value={}):
                with self.assertRaisesRegex(ValueError, 'BASE final main RNG differs'):
                    audit('plan', root, root / 'audit-new')
            self.assertFalse((root / 'AUDIT.json').exists())
            self.assertEqual(json.loads((root / 'audit-new/report.json').read_text())['status'], 'FAIL')
