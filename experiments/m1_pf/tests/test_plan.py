import tempfile
from pathlib import Path
import unittest
from unittest.mock import patch

from experiments.m1_pf import ARMS, BASE_COMMIT
from experiments.m1_pf.common import digest, write_json
from experiments.m1_pf.plan import load_plan


class SealedPlanTests(unittest.TestCase):
    def setUp(self):
        self.runtime = patch('experiments.m1_pf.plan.runtime_inputs', return_value={'tree': 'original'})
        self.runtime.start()
        self.addCleanup(self.runtime.stop)

    def fixture(self, directory):
        path = Path(directory) / 'plan.json'
        ledger = [{'generator_pf': False, 'judge_atom': 'PARA_END', 'observation_mode': 'END_ONLY'}]
        p = dict(schema_version=2, runtime_inputs={'tree': 'original'},
                 base_commit=BASE_COMMIT, arms=list(ARMS), primary='J24.CAL',
                 frozen_sources={'frozen': 'original'}, overlay_sources={'overlay': 'original'},
                 scope_ledger_hash=digest(ledger))
        p['plan_hash'] = digest(p)
        write_json(path, p)
        write_json(path.parent / 'scope_ledger.json', ledger)
        return path

    def test_code_change_invalidates_existing_plan(self):
        with tempfile.TemporaryDirectory() as td, \
             patch('experiments.m1_pf.plan.frozen_sources', return_value={'frozen': 'original'}), \
             patch('experiments.m1_pf.plan.overlay_sources', return_value={'overlay': 'changed'}):
            with self.assertRaisesRegex(ValueError, 'Overlay code changed'):
                load_plan(self.fixture(td))

    def test_mask_change_invalidates_existing_plan(self):
        with tempfile.TemporaryDirectory() as td, \
             patch('experiments.m1_pf.plan.frozen_sources', return_value={'frozen': 'original'}), \
             patch('experiments.m1_pf.plan.overlay_sources', return_value={'overlay': 'original'}):
            path = self.fixture(td)
            write_json(path.parent / 'scope_ledger.json', [])
            with self.assertRaisesRegex(ValueError, 'scope ledger changed'):
                load_plan(path)

    def test_arm_change_without_resealing_is_rejected(self):
        with tempfile.TemporaryDirectory() as td:
            path = self.fixture(td)
            import json
            p = json.loads(path.read_text());p['arms'] = ['BASE']
            write_json(path, p)
            with self.assertRaisesRegex(ValueError, 'Plan was changed'):
                load_plan(path)
