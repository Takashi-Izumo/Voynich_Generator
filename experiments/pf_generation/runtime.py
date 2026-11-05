"""Frozen v22.3 construction with case-local PF hooks and complete restoration."""
from __future__ import annotations

from copy import deepcopy
import inspect
from pathlib import Path

from experiments.m1_pf.runtime import Runtime as FrozenRuntime, GENERATION_LOCK
from . import ARMS, TRACE_SCHEMA
from .common import digest, file_hash, implementation_sources, require, runtime_inputs, state_hash, write_json
from .gate import models_view
from .laws import Law
from .overlay import Overlay
from .proposal import Trace, sampler_class, request_sampler_class


class Runtime(FrozenRuntime):
    def __init__(self, plan):
        super().__init__()
        self.plan = deepcopy(plan)
        require(self.input_snapshot == plan['runtime_inputs'], 'Sealed PF runtime inputs differ')
        require(implementation_sources() == plan['implementation_sources'], 'PF implementation changed')

    def _generate(self, bif, run, arm, dest):
        require(arm in (*ARMS, 'REFERENCE') and bif in self.plan['bifolia'] and run in self.plan['runs'],
                'Case outside sealed PF plan')
        unsealed = {k: v for k, v in self.plan.items() if k != 'plan_hash'}
        require(digest(unsealed) == self.plan['plan_hash'], 'PF plan mutated during generation')
        require(implementation_sources() == self.plan['implementation_sources'], 'PF source changed during generation')
        require(runtime_inputs() == self.input_snapshot, 'Runtime inputs changed during generation')
        dest = Path(dest)
        require(not dest.exists(), 'Case output already exists')
        a, rb, e = self.active, self.rb, self.engine
        fc, core, cfg, prev, patch, tab = self.case_inputs(bif)
        payload = self.plan['laws'][str(fc.fold)]
        require(tuple(payload['training_bifolia']) == tuple(fc.complete_train_bifs)
                and tuple(payload['excluded_bifolia']) == tuple(fc.outer_test_bifs), 'Law has wrong outer fold')
        law, trace = Law.load(payload), Trace()

        def prepare_segment(sr, models, event, candidate):
            trace.set_context(dict(page=str(sr.page), locus=str(sr.locus), segment_id=int(sr.segment_id),
                                 generator_pf=bool(e.is_pf(sr)), event=event, candidate=candidate,
                                 split_end=bool(int(sr.nsegments) > 1 and int(sr.segment_id) == int(sr.nsegments) - 1
                                                and str(sr.boundary_type) == 'LINE_END')))
            if arm in ('PF_GATE', 'PF_GATE_LENGTH') and e.is_pf(sr):
                return models_view(models, law, e.m, trace.context, trace)
            return models

        overlay = None if arm == 'REFERENCE' else Overlay(e, arm, prepare_segment)
        captured = {}

        def reference(*args, **kwargs):
            rng = inspect.signature(e.generate_bif).bind(*args, **kwargs).arguments['rand']
            result = e.generate_bif(*args, **kwargs)
            captured['state'] = state_hash(result[2])
            captured['rng'] = deepcopy(rng.bit_generator.state)
            return result

        previous = rb.PatchSampler, rb.PatchMapState, rb.build_bt_leafex, rb.patch_generate, rb.EntryFastSampler
        alpha = float(a.SEL.loc[(fc.fold, bif), 'selected_alpha'])
        try:
            rb.PatchSampler = a.configure(run, bif)
            if arm in ('PF_GATE', 'PF_GATE_LENGTH'):
                rb.PatchSampler = request_sampler_class(rb.PatchSampler, trace)
            rb.PatchMapState = a.ParagraphH1PatchMapState
            rb.build_bt_leafex = lambda ref, ext, a0=32.: a.real_build(ref, ext, alpha)
            rb.patch_generate = reference if overlay is None else overlay
            if arm == 'PF_GATE_LENGTH':
                cls = sampler_class(previous[4], e.m)
                rb.EntryFastSampler = lambda base, tables, patch: cls(base, tables, patch, law, trace)
            result = rb.generate(self.C, fc, core, cfg, prev, patch, tab, run)
        finally:
            rb.PatchSampler, rb.PatchMapState, rb.build_bt_leafex, rb.patch_generate, rb.EntryFastSampler = previous
        require(digest(law) == digest(Law.load(payload)), 'Immutable PF law changed')
        trace.finish_context()
        if overlay is not None and arm != 'BASE':
            for candidate in overlay.candidates:
                candidate['pfgen_trace'] = dict(trace_schema=TRACE_SCHEMA,
                    **trace.windows[candidate['event'], candidate['candidate']])
        rb.save_result(dest, result, fc, patch, tab)
        if overlay is not None:
            rb.dump_jsonl(dest / 'm1_events.jsonl.gz', overlay.events)
            rb.dump_jsonl(dest / 'm1_candidates.jsonl.gz', overlay.candidates)
        rb.dump_jsonl(dest / 'pfgen_gates.jsonl.gz', trace.gates)
        rb.dump_jsonl(dest / 'pfgen_proposals.jsonl.gz', trace.proposals)
        rng = captured['rng'] if overlay is None else overlay.final_main_rng_state
        final = dict(arm=arm, run=run, bif=bif, page=fc.target_page,
                     final_state_sha256=captured['state'] if overlay is None else overlay.final_state_sha256,
                     final_main_rng_state=rng, final_main_rng_sha256=digest(rng),
                     generation_input_sha256=result[1]['generation_input_sha256'],
                     archives=self.archives, runtime_sources=self.runtime_hashes, runtime_inputs=self.input_snapshot)
        write_json(dest / 'M1_FINAL.json', final)  # Explicit inherited state/RNG contract.
        write_json(dest / 'PF_GENERATION_FINAL.json', dict(trace_schema=TRACE_SCHEMA, plan_hash=self.plan['plan_hash'],
                   law_sha256=digest(payload), effective_law_sha256=digest(law), fold=fc.fold,
                   arm=arm, bif=bif, run=run, source_sha256=digest(self.plan['implementation_sources']),
                   gate_calls=trace.next_gate_id, proposal_calls=trace.next_raw_id,
                   raw_draws=sum(len(p['draws']) for p in trace.proposals),
                   anchor_fallbacks=sum(p['fallback'] for p in trace.proposals),
                   gate_changed_calls=sum(g['parent_probability'] != g['adapted_probability'] for g in trace.gates),
                   identity_override=self.plan['identity_override']))
        return result[1]
