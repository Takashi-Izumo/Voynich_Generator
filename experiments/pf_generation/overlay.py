"""PF generation overlay, derived from pinned M1; original M1 remains untouched."""
from __future__ import annotations

from collections import Counter
from copy import deepcopy
import json

from judges.schema import glyphs
from . import ARMS
from .common import digest, state_hash
from .laws import Law
from .proposal import Trace


def family(terminal):
    return 'NMY' if terminal in ('n', 'm', 'y') else 'LR' if terminal in ('l', 'r') else 'OTHER'


def terminal_facts(row, engine):
    stable = tuple(engine.m.v10.tokenize(str(row['stable_surface'])))
    names = [engine.m.I2G[int(g)] for g in stable]
    visible = glyphs(str(row['surface']))
    if not stable or not visible:
        raise ValueError('Empty/invalid PF endpoint')
    return dict(stable_surface=row['stable_surface'], surface=row['surface'],
                stable_glyph_length=len(stable), visible_glyph_length=len(visible),
                stable_terminal=names[-1], visible_terminal=visible[-1],
                stable_family=family(names[-1]), visible_family=family(visible[-1]),
                stable_m=names.count('m'), visible_m=visible.count('m'),
                visible_length_crossings=[n for n in (2, 3, 4, 5, 6) if (len(stable) <= n) != (len(visible) <= n)],
                phys_width=int(row['phys_width']), segment_capacity=int(row['segment_capacity']))


class SamplerControl:
    """Only request IDs/logs, counters and deterministic row caches are shared."""
    ALLOWED = {'state', 'base', 'requests', 'head_rows', 'next_proposal_id',
               'word_first_request', 'last_request', 'tx_checks', 'head_draws'}
    FAST_ALLOWED = {'parent', 'tables', 'patch', 'state', 'row_audit', 'calls',
                    'phw_delegations', 'delegate_calls', 'row_catalog', 'pf_law', 'pf_trace'}

    @classmethod
    def capture(cls, sampler):
        extra = set(vars(sampler)) - cls.ALLOWED
        if extra:
            raise ValueError(f'Unaudited sampler control fields: {sorted(extra)}')
        if hasattr(sampler.base, 'row_catalog'):
            extra = set(vars(sampler.base)) - cls.FAST_ALLOWED
            if extra:
                raise ValueError(f'Unaudited fast-sampler fields: {sorted(extra)}')
        if hasattr(sampler.base, 'pf_law'):
            if not isinstance(sampler.base.pf_law, Law) or not isinstance(sampler.base.pf_trace, Trace):
                raise ValueError('Unknown PF policy control')
        return sampler.last_request, sampler.word_first_request

    @staticmethod
    def restore(sampler, state, control):
        sampler.rebind(state)
        sampler.last_request, sampler.word_first_request = control
        if sampler.state is not state.motion or sampler.base.state is not state.motion:
            raise AssertionError('Sampler/state rebind failed')


class Overlay:
    def __init__(self, engine, arm, prepare_segment):
        if arm not in ARMS:
            raise ValueError(arm)
        if engine.PF_K != 2 or engine.PF_RESCUE_EXTRA != 8:
            raise ValueError('M1 requires the pinned two-branch/eight-rescue engine')
        self.e, self.arm, self.prepare_segment = engine, arm, prepare_segment
        self.events, self.candidates = [], []
        self.final_state_sha256 = None
        self.final_main_rng_state = None

    def __call__(self, run, bif, cdf, quad, seg, models, sampler, rand, state, mm, feats, gm,
                 phw_selector=None, pf_selector=None, seed=20260906, proposal_limit=4096):
        e = self.e
        if pf_selector is None:
            raise ValueError('M1 keeps the PF bank and scorer in all three arms')
        out, stats, phlogs, pflogs, pfbank = [], Counter(), [], [], []
        for sr in seg[seg.bif.astype(str).eq(bif)].sort_values('global_order').itertuples(index=False):
            if e.is_pf(sr):
                pre = state.digest()
                full_pre = state_hash(state)
                budget_before = int(state.rare['budget'])
                rng0 = deepcopy(rand.bit_generator.state)
                control0 = SamplerControl.capture(sampler)
                branches, scores, controls = [], [], []
                event_index = len(self.events)

                def branch(j, rescue=False):
                    SamplerControl.restore(sampler, state, control0)
                    branch_state = state.clone()
                    if state_hash(branch_state) != full_pre:
                        raise AssertionError('Incomplete branch clone (including paragraph/rare state)')
                    if not rescue and j == 0:
                        br = e.clone_rng(rand)
                        lineage = 'MAIN_CLONE'
                    else:
                        lineage = 'PF_LEN1_RESCUE' if rescue else 'PF_BRANCH'
                        number = j - e.PF_K if rescue else j
                        br = e.m.keyed_rng(seed, run, bif, str(sr.locus), int(sr.segment_id),
                                           lineage, number, json.dumps(rng0, sort_keys=True))
                    start_rng = digest(br.bit_generator.state)
                    proposal_start = sampler.next_proposal_id
                    scoped_models = self.prepare_segment(sr, models, event_index, j)
                    b = e.complete_segment(sr, run, cdf, quad, scoped_models, sampler, br, branch_state,
                                           mm, feats, gm, phw_selector, proposal_limit)
                    control = SamplerControl.capture(sampler)
                    if state_hash(state) != full_pre or digest(rand.bit_generator.state) != digest(rng0):
                        raise AssertionError('Uncommitted PF branch contaminated parent state/main RNG')
                    last = b.rows[-1]
                    score = float(pf_selector.score(last['stable_surface'], last['phys_width'], last['segment_capacity']))
                    branches.append(b)
                    scores.append(score)
                    controls.append(control)
                    return dict(arm=self.arm, run=run, bif=bif, page=str(sr.page), locus=str(sr.locus),
                                para=int(sr.para), segment_id=int(sr.segment_id), event=event_index,
                                pf_intervention=True, candidate=j, is_rescue=rescue, rng_lineage=lineage,
                                input_state_sha256=full_pre, output_state_sha256=state_hash(b.state),
                                rng_entry_sha256=start_rng, rng_exit_sha256=digest(b.rng_state),
                                proposal_id_start=proposal_start, proposal_id_end=sampler.next_proposal_id,
                                proposal_id_contract='legacy_shared_all_attempts_including_discarded_branches',
                                rare_budget_before=budget_before, rare_budget_after=int(b.state.rare['budget']),
                                score=score, nwords=len(b.rows), parent_isolation=True,
                                **terminal_facts(last, e))

                audit_rows = [branch(j) for j in range(e.PF_K)]
                base_chosen = max(range(e.PF_K), key=lambda j: (scores[j], -j))
                base_win = branches[base_chosen]
                chosen = base_chosen
                base_last = base_win.rows[-1]
                base_seq = tuple(e.m.v10.tokenize(str(base_last['stable_surface'])))
                base_w, base_score = int(base_last['phys_width']), scores[base_chosen]
                rescue_target = len(base_seq) <= e.PF_RESCUE_MAX_BASE_LEN
                for r in audit_rows:
                    r['rescue_eligible'] = None
                if rescue_target:
                    for jj in range(e.PF_RESCUE_EXTRA):
                        j = e.PF_K + jj
                        record = branch(j, rescue=True)
                        b = branches[j]
                        seq = tuple(e.m.v10.tokenize(str(b.rows[-1]['stable_surface'])))
                        eligible = e._rescue_ok(seq, int(b.rows[-1]['phys_width']), scores[j],
                                                base_seq, base_w, base_score, e.PF_RESCUE_TOL, False)
                        record['rescue_eligible'] = bool(eligible)
                        audit_rows.append(record)
                        if eligible and (chosen == base_chosen or scores[j] > scores[chosen]):
                            chosen = j
                    if chosen != base_chosen:
                        stats['pf_length_rescue'] += 1
                win = branches[chosen]
                continuation = base_chosen
                future_rng_state = branches[continuation].rng_state
                for j, b in enumerate(branches):
                    last = b.rows[-1]
                    # The inherited export tables retain their exact BASE schema.
                    pflogs.append(dict(run=run, bif=bif, page=str(sr.page), locus=str(sr.locus), para=int(sr.para),
                                       segment_id=int(sr.segment_id), candidate=j, selected=int(j == chosen),
                                       surface=last['surface'], stable_surface=last['stable_surface'],
                                       phys_width=last['phys_width'], glyph_len=last['glyph_len'],
                                       segment_capacity=last['segment_capacity'], score=scores[j], nwords=len(b.rows),
                                       input_state_sha256=pre, output_state_sha256=b.state.digest(),
                                       rare_budget_before=budget_before, rare_budget_after=b.state.rare['budget']))
                    pfbank.extend([dict(**r, candidate=j, selected=int(j == chosen)) for r in b.rows])
                    audit_rows[j].update(selected=j == chosen, original_argmax=base_chosen,
                                         chosen=chosen, continuation_candidate=continuation)
                state = win.state
                SamplerControl.restore(sampler, state, controls[chosen])
                if state_hash(state) != audit_rows[chosen]['output_state_sha256']:
                    raise AssertionError('Committed state differs from the selected branch')
                rand.bit_generator.state = future_rng_state
                if digest(rand.bit_generator.state) != audit_rows[continuation]['rng_exit_sha256']:
                    raise AssertionError('Wrong main RNG continuation')
                stats.update(win.stats)
                stats['pf_selection_events'] += 1
                stats['pf_candidates'] += e.PF_K
                stats['pf_rescue_candidates'] += max(0, len(branches) - e.PF_K)
                stats['pf_selected_candidate1'] += int(base_chosen == 1)
                stats['pf_length_rescue_selected'] += int(chosen >= e.PF_K)
                stats['pf_counterfactual_rejects'] += sum(b.stats['reject'] for j, b in enumerate(branches) if j != chosen)
                out.extend(win.rows)
                phlogs.extend(win.phw_candidates)
                self.candidates.extend(audit_rows)
                self.events.append(dict(arm=self.arm, run=run, bif=bif, page=str(sr.page), locus=str(sr.locus),
                                        para=int(sr.para), segment_id=int(sr.segment_id), event=event_index,
                                        original_argmax=base_chosen, chosen=chosen, rescue_target=rescue_target,
                                        rescue_explored=len(branches) - 2, rescue_adopted=chosen >= 2,
                                        reason='RESCUE' if chosen >= 2 else 'ARGMAX',
                                        continuation_candidate=continuation, input_state_sha256=full_pre,
                                        output_state_sha256=state_hash(state), rng_entry_sha256=digest(rng0),
                                        rng_continuation_sha256=digest(rand.bit_generator.state),
                                        sampler_rebound=True, rare_budget_after=int(state.rare['budget'])))
            else:
                self.prepare_segment(sr, models, None, None)
                win = e.complete_segment(sr, run, cdf, quad, models, sampler, rand, state, mm, feats, gm,
                                         phw_selector, proposal_limit)
                state = win.state
                if hasattr(sampler, 'rebind'):
                    sampler.rebind(state)
                out.extend(win.rows)
                stats.update(win.stats)
                phlogs.extend(win.phw_candidates)
        self.final_state_sha256 = state_hash(state)
        self.final_main_rng_state = deepcopy(rand.bit_generator.state)
        return out, stats, state, phlogs, pflogs, pfbank
