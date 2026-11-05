"""Observe the literal frozen generator and replay on private sampler/state clones."""
from __future__ import annotations

from copy import deepcopy
import hashlib
import inspect
import json

from experiments.m1_pf.runtime import Runtime as SourceRuntime, GENERATION_LOCK
from experiments.pf_generation.overlay import SamplerControl
from . import NAMESPACE, SEED, BRANCHES
from .common import canonical, digest, require, seal, source_state, state_hash
from .proxy import facts


def class_data(cls):
    return {k:v for k,v in vars(cls).items() if not k.startswith('__')
            and not callable(v) and not isinstance(v,(classmethod,staticmethod,property))}


def effective_class_controls(cls):
    names={k for parent in cls.__mro__ for k in class_data(parent)}
    return {k:getattr(cls,k) for k in sorted(names)}


def class_control_payload(cls):
    values=effective_class_controls(cls)
    baseline=values.get('H1_BASELINE')
    if baseline is not None:
        require(type(baseline).__module__=='paragraph_h1_sampler' and type(baseline).__name__=='ParagraphH1Baseline'
                and set(vars(baseline))=={'metadata','by_bif','glyphs'},'Unknown paragraph-H1 baseline control')
        values['H1_BASELINE']=dict(type='paragraph_h1_sampler.ParagraphH1Baseline',payload=vars(baseline))
    return values


def restore_class_controls(saved):
    for cls,values in saved:
        for key in class_data(cls).keys()-values.keys():
            delattr(cls,key)
        for key,value in values.items():
            setattr(cls,key,value)


def sampler_payload(sampler):
    SamplerControl.capture(sampler)  # Reject unknown mutable fields.
    return dict(class_controls=class_control_payload(type(sampler)),
                control={k: v for k, v in vars(sampler).items() if k not in ('base', 'state')},
                fast={k: v for k, v in vars(sampler.base).items() if k not in ('parent', 'tables', 'patch', 'state')},
                motion=canonical({k: v for k, v in vars(sampler.state).items() if k != 'correction'})
                if sampler.state is not None else None)


def clone_sampler(sampler, state):
    fast = sampler.base
    memo = {id(fast.parent): fast.parent, id(fast.tables): fast.tables, id(fast.patch): fast.patch}
    if sampler.state is not None:
        memo[id(sampler.state)] = state.motion
    if fast.state is not None:
        memo[id(fast.state)] = state.motion
    clone = deepcopy(sampler, memo)
    clone.rebind(state)
    require(clone is not sampler and clone.base is not fast and clone.requests is not sampler.requests
            and clone.base.row_catalog is not fast.row_catalog and clone.state is state.motion
            and clone.base.state is state.motion, 'Replay clone aliases mutable parent')
    return clone


def immutable_fingerprint(core, tables):
    cdf, quad, models, base, ph, pf = core
    arrays = dict(cdf=cdf, quad=quad, dw=base.dw, dw2=base.dw2, hh2=base.hh2)
    return dict(arrays={k: dict(shape=list(v.shape), dtype=str(v.dtype),
                               sha256=hashlib.sha256(v.tobytes()).hexdigest()) for k, v in arrays.items()},
                correction=tables.content_fingerprint())


def validate_segment(rows, sr):
    require(rows and all(str(r['page']) == str(sr.page) and str(r['locus']) == str(sr.locus)
                        and int(r['segment_id']) == int(sr.segment_id) for r in rows), 'Donor context mismatch')
    require([int(r['segment_wordnum']) for r in rows] == list(range(1,len(rows)+1)), 'Incomplete donor word order')
    require([int(r['draw_segment_end']) for r in rows] == [0]*(len(rows)-1)+[1], 'Incomplete donor segment')
    require(sum(int(r['phys_width']) for r in rows)+len(rows)-1 == int(sr.segment_capacity)
            and int(rows[-1]['r_after_word']) == 0, 'Donor physical packing violation')
    require(all(str(r['boundary_type']) == str(sr.boundary_type) for r in rows), 'Donor PLANT boundary mismatch')
    require(not int(sr.segment_id) or all(r['role'] == 'BODY' for r in rows), 'PLANT restart became HEAD/W2')
    facts(rows)


class Runtime(SourceRuntime):
    def collect(self, bif, observe=True, branches=BRANCHES):
        require(branches == BRANCHES, 'Replay budget is fixed at 64')
        with GENERATION_LOCK:
            return self._collect(bif, observe)

    def _collect(self, bif, observe):
        a, rb, e = self.active, self.rb, self.engine
        fc, core, cfg, prev, patch, tab = self.case_inputs(bif)
        alpha = float(a.SEL.loc[(fc.fold, bif), 'selected_alpha'])
        previous = rb.PatchSampler, rb.PatchMapState, rb.build_bt_leafex, rb.patch_generate, e.complete_segment
        class_before=[(cls,deepcopy(class_data(cls))) for cls in a.V223F1LFLengthTerminalSampler.__mro__ if cls is not object]
        snapshots, bank, seen = [], [], set()
        immutable = immutable_fingerprint(core, tab)
        final = {}

        def observed_segment(sr, run, cdf, quad, models, sampler, rand, state, mm, feats, gm, ph, limit):
            key = str(sr.page), str(sr.locus), int(sr.segment_id)
            if e.is_pf(sr) and key not in seen:
                seen.add(key)
                ctx = dict(bif=str(bif), run=SEED, page=key[0], locus=key[1], segment_id=key[2], event=len(snapshots))
                entry = state_hash(state)
                rng = deepcopy(rand.bit_generator.state)  # Candidate 0 is an exact main-RNG clone.
                control = canonical(sampler_payload(sampler))
                snapshot = seal(dict(**ctx, state=canonical(source_state(state)), state_sha256=entry,
                         main_rng=rng, main_rng_sha256=digest(rng), sampler=control,
                         sampler_sha256=digest(control), next_proposal_id=int(sampler.next_proposal_id),
                         immutable=immutable, fold=int(fc.fold), known3=list(fc.known_pages),
                         layout=canonical(sr._asdict()), namespace=NAMESPACE, branches=BRANCHES))
                snapshots.append(snapshot)
                for j in range(BRANCHES):
                    bs = state.clone()
                    require(state_hash(bs) == entry, 'Incomplete GenerationState clone')
                    private = clone_sampler(sampler, bs)
                    br = e.m.keyed_rng(NAMESPACE, SEED, bif, key[0], key[1], key[2], ctx['event'], j,
                                       json.dumps(rng, sort_keys=True))
                    rng_entry = deepcopy(br.bit_generator.state)
                    start = private.next_proposal_id
                    old_requests = len(private.requests)
                    prior_rows = set(private.base.row_catalog)
                    result = previous[4](sr, run, cdf, quad, models, private, br, bs, mm, feats, gm, ph, limit)
                    validate_segment(result.rows, sr)
                    audit = private.base.row_audit
                    require(audit[3] <= 1e-12 and audit[4] <= 1e-12 and audit[5] == 0 and audit[6] == 0,
                            'Replay changed support or probability normalization')
                    require(private.state is result.state.motion and private.base.state is result.state.motion,
                            'Replay sampler not rebound to committed state')
                    record = dict(**ctx, branch=j, snapshot_sha256=snapshot['sha256'],
                                  rng_entry=rng_entry, rng_exit=result.rng_state,
                                  input_state_sha256=entry, output_rare=canonical(result.state.rare),
                                  output_state_sha256=state_hash(result.state), rows=result.rows,
                                  stats=dict(result.stats), proposal_start=int(start), proposal_end=int(private.next_proposal_id),
                                  requests=private.requests[old_requests:],
                                  new_probability_rows=canonical({k:v for k,v in private.base.row_catalog.items() if k not in prior_rows}),
                                  probability_audit=audit.tolist(),
                                  restored_parent=True, support_violations=0, physical_packing=True)
                    bank.append(seal(record))
                require(state_hash(state) == entry and digest(rand.bit_generator.state) == digest(rng)
                        and canonical(sampler_payload(sampler)) == control,
                        'Replay contaminated BASE state/RNG/rare/route/sampler/request counters')
                require(immutable_fingerprint(core, tab) == immutable, 'Replay mutated immutable inputs')
            return previous[4](sr, run, cdf, quad, models, sampler, rand, state, mm, feats, gm, ph, limit)

        def generate(*args, **kwargs):
            rand = inspect.signature(e.generate_bif).bind(*args, **kwargs).arguments['rand']
            result = e.generate_bif(*args, **kwargs)
            final.update(state=canonical(source_state(result[2])), state_sha256=state_hash(result[2]),
                         main_rng=deepcopy(rand.bit_generator.state))
            return result

        try:
            rb.PatchSampler = a.configure(SEED, bif)
            rb.PatchMapState = a.ParagraphH1PatchMapState
            rb.build_bt_leafex = lambda ref, ext, a0=32.: a.real_build(ref, ext, alpha)
            rb.patch_generate = generate
            if observe:
                e.complete_segment = observed_segment
            result = rb.generate(self.C, fc, core, cfg, prev, patch, tab, SEED)
        finally:
            rb.PatchSampler, rb.PatchMapState, rb.build_bt_leafex, rb.patch_generate, e.complete_segment = previous
            restore_class_controls(class_before)
        require(immutable_fingerprint(core, tab) == immutable, 'Generator mutated immutable inputs')
        rr, md, segments, logs, trace, phlog, pflog, pfbank = result
        mechanical = {k:v for k,v in md.items() if k != 'elapsed_seconds'}
        base = dict(rows=rr, mechanical=mechanical, segments=segments, logs=logs, trace=trace,
                    phlog=phlog, pflog=pflog, pfbank=pfbank, final=final)
        # Entire semantic record, not only text: logs, IDs, rare/route/state, actual main RNG.
        return dict(bif=bif, fold=int(fc.fold), page=str(fc.target_page), known3=list(fc.known_pages),
                    base=base, snapshots=snapshots, donors=bank, base_sha256=digest(base))
