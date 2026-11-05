from copy import deepcopy
import json
from pathlib import Path
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch

from experiments.pf_generation import ARMS, BASE_COMMIT, CONTRASTS, DESIGN, EXTRACTOR_HASH, MODEL_SET_HASH, POLICY, PROTOCOL_HASH
from experiments.pf_generation.common import ROOT, digest, file_hash, write_json
from experiments.pf_generation.evaluation import audited
from experiments.pf_generation.audit import generation_binding
from experiments.pf_generation.overlay import SamplerControl
from experiments.pf_generation.plan import load_plan


class PlanIntegrityTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.plan = dict(schema_version=1, experiment='PF_GENERATION_DESIGN_007_STUDY_1', base_commit=BASE_COMMIT,
                         arms=list(ARMS), contrasts=[list(c) for c in CONTRASTS], policy=POLICY,
                         bifolia=['T0'], folds={'T0': 0}, runtime_inputs={}, frozen_sources={}, implementation_sources={},
                         design_sha256=file_hash(ROOT / DESIGN), scope_ledger_hash=digest([]), identity_override=True,
                         required_model_set_hash=MODEL_SET_HASH, extractor_hash=EXTRACTOR_HASH, protocol_hash=PROTOCOL_HASH,
                         primary='J24.CAL', local_primary='ATOM.PARA_END.CAL', laws={'0': dict(
                             fold=0, theta=[0.] * 4, gains=[[1.] * 4] * 3, known3_used=False,
                             training_bifolia=[f'A{i}' for i in range(16)], excluded_bifolia=[f'T{i}' for i in range(4)],
                             identity_override=True, runtime_inputs={})})
        write_json(self.root / 'scope_ledger.json', [])
        self.save()
        for name in ['frozen_sources', 'implementation_sources', 'runtime_inputs']:
            p = patch('experiments.pf_generation.plan.' + name, return_value={})
            p.start()
            self.addCleanup(p.stop)

    def save(self):
        self.plan.pop('plan_hash', None)
        self.plan['plan_hash'] = digest(self.plan)
        write_json(self.root / 'plan.json', self.plan)

    def test_sealed_law_change_is_rejected(self):
        self.assertEqual(load_plan(self.root / 'plan.json'), self.plan)
        self.plan['laws']['0']['theta'][0] = 2.
        write_json(self.root / 'plan.json', self.plan)
        with self.assertRaisesRegex(ValueError, 'Sealed PF plan changed'):
            load_plan(self.root / 'plan.json')

    def test_expanded_settings_change_is_rejected(self):
        with patch('experiments.pf_generation.plan.runtime_inputs', return_value={'changed': 1}):
            with self.assertRaisesRegex(ValueError, 'Expanded runtime inputs changed'):
                load_plan(self.root / 'plan.json')

    def test_new_law_cannot_use_known3_even_with_new_seal(self):
        self.plan['laws']['0']['known3_used'] = True
        self.save()
        with self.assertRaisesRegex(ValueError, 'training scope'):
            load_plan(self.root / 'plan.json')

    def test_target_cannot_enter_training_scope(self):
        self.plan['laws']['0']['training_bifolia'][0] = 'T0'
        self.save()
        with self.assertRaisesRegex(ValueError, 'training scope'):
            load_plan(self.root / 'plan.json')


class ReceiptTests(unittest.TestCase):
    def test_refreshed_artifact_checksums_do_not_reuse_old_pass(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            plan = dict(plan_hash='sealed', bifolia=['A:2'], runs=[1])
            write_json(root / 'plan.json', plan)
            write_json(root / 'STATUS.json', dict(status='GENERATED_NOT_AUDITED', plan_hash='sealed'))
            rows = []
            for arm in (*ARMS, 'REFERENCE'):
                dest = root / arm
                dest.mkdir()
                write_json(dest / 'M1_FINAL.json', dict(arm=arm, bif='A:2', run=1))
                (dest / 'tokens.txt').write_text('original')
                rows.append(dict(arm=arm, bif='A:2', run=1, path=arm,
                                 files={p.name: file_hash(p) for p in dest.iterdir()}))
            manifest = dict(plan_hash='sealed', records=rows)
            write_json(root / 'manifest.json', manifest)
            binding = generation_binding(plan, root)
            report = dict(schema_version=1, plan_hash='sealed', generation_binding=binding, status='PASS',
                          base_reference_checked=True, base_reference_main_rng_checked=True, repeat_checked=False)
            write_json(root / 'report.json', report)
            write_json(root / 'AUDIT.json', dict(schema_version=1, plan_hash='sealed', generation_binding=binding,
                       report=str(root / 'report.json'), report_sha256=file_hash(root / 'report.json')))
            with patch('experiments.pf_generation.evaluation.load_plan', return_value=plan):
                self.assertEqual(audited('unused', root), plan)
                (root / 'BASE/tokens.txt').write_text('changed but rechecksummed')
                rows[0]['files']['tokens.txt'] = file_hash(root / 'BASE/tokens.txt')
                write_json(root / 'manifest.json', manifest)
                with self.assertRaisesRegex(ValueError, 'mechanical audit seal'):
                    audited('unused', root)


class ControlTests(unittest.TestCase):
    def test_unknown_fast_sampler_mutable_field_is_rejected(self):
        sampler = SimpleNamespace(last_request=None, word_first_request=0,
                                  base=SimpleNamespace(row_catalog={}, unknown_mutable=[]))
        with self.assertRaisesRegex(ValueError, 'Unaudited fast-sampler'):
            SamplerControl.capture(sampler)


if __name__ == '__main__':
    unittest.main()
