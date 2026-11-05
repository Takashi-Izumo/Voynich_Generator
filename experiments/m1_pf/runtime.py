from __future__ import annotations

import importlib
import json
from pathlib import Path
import sys
import zipfile
from copy import deepcopy
import inspect
from threading import RLock

from .common import PACKAGE, file_hash, frozen_sources, state_hash, write_json
from .overlay import Overlay
from .inputs import runtime_inputs

GENERATION_LOCK = RLock()


class Runtime:
    def __init__(self):
        self.frozen = frozen_sources()
        self.input_snapshot = runtime_inputs()
        import csv
        with (PACKAGE / 'model/sources/SOURCE_ARCHIVES_SHA256.csv').open(newline='') as f:
            sources = list(csv.DictReader(f))
        self.archives = {}
        for r in sources:
            p = PACKAGE / 'model/sources' / r['filename']
            if file_hash(p) != r['sha256'] or p.stat().st_size != int(r['bytes']):
                raise ValueError('Parent archive mismatch: ' + r['filename'])
            self.archives[r['filename']] = r['sha256']
        sys.path.insert(0, str(PACKAGE / 'model/code'))
        self.active = importlib.import_module('run_v22_3_stage3d')
        self.rb = self.active.rb
        self.engine = importlib.import_module('bti2_patch_engine')
        # Verify the actual imported engine/state/sampler against the trusted ZIP,
        # rather than assuming a previously extracted runtime was never edited.
        import hashlib
        parent = PACKAGE / 'model/sources/EHC1_E1GLOBAL_FULL_20260911.zip'
        self.runtime_hashes = {}
        with zipfile.ZipFile(parent) as z:
            for name in ['bti2_patch_engine', 'bti2_patch_state', 'bti2_patch_sampler', 'sel42_selectors', 'route_map_model']:
                path = Path(sys.modules[name].__file__)
                member = path.relative_to(PACKAGE / 'model/runtime').as_posix()
                expected = hashlib.sha256(z.read(member)).hexdigest()
                if file_hash(path) != expected:
                    raise ValueError('Extracted runtime was modified: ' + name)
                self.runtime_hashes[name] = expected
        self.C = self.active.benv.e.context()
        self.cores = {}

    def case_inputs(self, bif):
        a, C = self.active, self.C
        fold = int(a.SEL.reset_index().set_index('bif').loc[bif, 'fold'])
        page = C.pages[bif][-1]
        fc = a.FoldContext.create(C, fold, bif, page, 'LEGACY_SCOPE', a.POLICY)
        if fold not in self.cores:
            self.cores[fold] = a.load_core(C, fc)
        core, ca = self.cores[fold]
        frozen = json.loads((a.benv.EHC / 'parent/HerbalA_RMW1_BTI2_20260909/parameters/FROZEN_FOLD_CONFIGS.json').read_text())
        cfg = a.MapConfig(**frozen[f'fold{fold}'])
        eta = a.pd.read_csv(a.ST / 'parameters/SELECTED_ETA_BY_OUTER_FOLD.csv').set_index('outer_fold').loc[fold]
        ex = C.events[C.events.bif.isin(fc.complete_train_bifs)]
        kn = C.events[C.events.page.isin(fc.known_pages)]
        tab = a.DecomposedEntryTablesUV(ex, kn, *core[:2], core[3], fc, ca,
                                       eta_u=float(eta.eta_u), eta_v=float(eta.eta_v))
        return fc, core, cfg, a.rb.page_prevalence(C, fc), a.puv_config(), tab

    def generate(self, bif, run, arm, dest):
        # The frozen runner configures module/class attributes. Threaded callers
        # are serialized; process parallelism uses distinct output roots.
        with GENERATION_LOCK:
            return self._generate(bif, run, arm, dest)

    def _generate(self, bif, run, arm, dest):
        if runtime_inputs() != self.input_snapshot:
            raise ValueError('Runtime inputs changed during generation')
        a, rb = self.active, self.rb
        fc, core, cfg, prev, patch, tab = self.case_inputs(bif)
        alpha = float(a.SEL.loc[(fc.fold, bif), 'selected_alpha'])
        previous = rb.PatchSampler, rb.PatchMapState, rb.build_bt_leafex, rb.patch_generate
        overlay = None if arm == 'REFERENCE' else Overlay(self.engine, arm)
        captured = {}

        def reference(*args, **kwargs):
            rng = inspect.signature(self.engine.generate_bif).bind(*args, **kwargs).arguments['rand']
            result = self.engine.generate_bif(*args, **kwargs)
            captured['final_state_sha256'] = state_hash(result[2])
            captured['final_main_rng_state'] = deepcopy(rng.bit_generator.state)
            return result

        try:
            rb.PatchSampler = a.configure(run, bif)
            rb.PatchMapState = a.ParagraphH1PatchMapState
            rb.build_bt_leafex = lambda ref, ext, a0=32.: a.real_build(ref, ext, alpha)
            rb.patch_generate = overlay if overlay is not None else reference
            result = rb.generate(self.C, fc, core, cfg, prev, patch, tab, run)
        finally:
            rb.PatchSampler, rb.PatchMapState, rb.build_bt_leafex, rb.patch_generate = previous
        rb.save_result(dest, result, fc, patch, tab)
        if overlay is not None:
            rb.dump_jsonl(dest / 'm1_events.jsonl.gz', overlay.events)
            rb.dump_jsonl(dest / 'm1_candidates.jsonl.gz', overlay.candidates)
        from .common import digest
        rng_state = overlay.final_main_rng_state if overlay else captured['final_main_rng_state']
        final = dict(arm=arm, run=run, bif=bif, page=fc.target_page,
                     final_state_sha256=overlay.final_state_sha256 if overlay else captured['final_state_sha256'],
                     final_main_rng_state=rng_state, final_main_rng_sha256=digest(rng_state),
                     generation_input_sha256=result[1]['generation_input_sha256'],
                     archives=self.archives, runtime_sources=self.runtime_hashes, runtime_inputs=self.input_snapshot)
        write_json(dest / 'M1_FINAL.json', final)
        return result[1]
