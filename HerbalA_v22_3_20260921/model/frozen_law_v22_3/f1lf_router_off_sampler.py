from __future__ import annotations

"""HerbalA-v22.2: clock-safe normal-F1-LF route-router OFF.

Parent: HerbalA-v22r-W2B2.

The first naive implementation disabled MapState.candidate_features() before the
parent selector.  A mechanical smoke showed that this can change the accepted
proposal/retry path itself.  v22.2 therefore keeps the parent proposal bank,
accept/retry decision and parent RNG trajectory intact for the current request,
then re-selects *within the accepted parent candidate bank* after acceptance is
known.

Scope:
  * role == 'F1'
  * row_phase == 'FIRST'
  * physical LF request: end and line_end_boundary
  * segment_id == 0 (plant-restart BODY excluded)
  * paragraph-final/single-line FIRST excluded
  * board == 'LF'

At a scoped request:
  1) the complete v22r-W2B2 parent request is generated normally;
  2) its stored candidate scores are decomposed as
       parent_score = nonroute_score + route_score;
  3) target probabilities are softmax(nonroute_score), i.e. route score OFF;
  4) a request-local SHA-256 side stream performs maximal coupling from the
     parent distribution to the route-neutral target distribution;
  5) the parent proposal is returned to the engine so the current request's
     accept/retry/proposal clock is parent-exact;
  6) if that request is committed, the route-neutral child is written and is
     committed normally to semantic/route state.

Thus the direct scope intervention is isolated from current-request proposal
clock changes, while genuine downstream causal effects of the selected word are
preserved.
"""

import hashlib
import math
from typing import Any

import numpy as np
import v19r_rb3_pw2_close1 as m

from w2_b2_sampler import V22rW2B2Sampler


def _side_rng(run_seed: int, bif: str, record: dict, namespace: str):
    payload = '|'.join([
        str(namespace), str(int(run_seed)), str(bif),
        str(record.get('page')), str(record.get('locus')),
        str(record.get('segment_id')), str(record.get('word_index')),
        str(record.get('proposal_id')),
    ]).encode('utf-8')
    dig = hashlib.sha256(payload).digest()
    seed = int.from_bytes(dig[:16], 'big', signed=False)
    return np.random.default_rng(seed), hashlib.sha256(payload).hexdigest()


def _parse_stable_word(s: str):
    s = str(s)
    multi = sorted([g for g in m.G2I if len(g) > 1], key=len, reverse=True)
    out = []
    i = 0
    while i < len(s):
        z = next((g for g in multi if s.startswith(g, i)), None)
        if z is None:
            if s[i] not in m.G2I:
                raise ValueError(f'Non-stable glyph in candidate: {s!r}')
            z = s[i]
        out.append(int(m.G2I[z]))
        i += len(z)
    return tuple(out)


def _softmax(x):
    x = np.asarray(x, dtype=float)
    if len(x) == 0:
        return x
    z = x - np.max(x)
    p = np.exp(z)
    p /= p.sum()
    return p


class V222F1LFRouterOffSampler(V22rW2B2Sampler):
    """v22.2 = v22r-W2B2 + normal-F1-LF route-neutral bank re-selection."""

    MODEL_ID = 'HerbalA-v22.2'
    RUN_SEED = 0
    TARGET_BIF = ''
    F1LF_ROUTER_OFF_ENABLED = True
    F1LF_ROUTER_OFF_NAMESPACE = 'V22_2_F1LF_ROUTER_OFF_V1'
    F1LF_ROUTER_OFF_SCOPE = (
        'FIRST x physical-LF x role=F1 x segment_id=0 x non-paragraph-final'
    )

    @staticmethod
    def is_f1lf_router_off_scope(st: Any, args: tuple, kwargs: dict) -> bool:
        if st is None:
            return False
        role = str(args[2])
        end = bool(args[10])
        line_end = bool(kwargs.get('line_end_boundary', False))
        if role != 'F1':
            return False
        if str(getattr(st, 'row_phase', '')) != 'FIRST':
            return False
        if int(getattr(st, 'segment_id', -1)) != 0:
            return False
        if not (end and line_end):
            return False
        if bool(getattr(st, 'par_h1_raw_para_final', False)):
            return False
        try:
            return str(st.board(role, end, line_end)) == 'LF'
        except Exception:
            return False

    def _prepare_route_neutral_child(self, anchor_seq, st, record):
        candidates_s = list(record.get('candidates') or [])
        scores = list(record.get('scores') or [])
        parent_p = np.asarray(record.get('probabilities') or [], dtype=float)
        if not candidates_s or len(candidates_s) != len(scores):
            return None, 'NO_PARENT_BANK'
        if len(candidates_s) == 1:
            # No route choice exists.  Treat this as a no-op rather than an
            # applied patch; otherwise commit_word would expect a staged child.
            return None, 'SINGLE_CANDIDATE'

        candidates = [_parse_stable_word(x) for x in candidates_s]
        # Parent bank invariants: same stable length and width.
        L = len(anchor_seq)
        W = int(m.stable_width(anchor_seq))
        if not all(len(c) == L and int(m.stable_width(c)) == W for c in candidates):
            return None, 'PARENT_BANK_INVARIANT_FAIL'

        route_scores = np.asarray([float(st.candidate_features(c)[0]) for c in candidates], float)
        neutral_scores = np.asarray(scores, float) - route_scores
        target_p = _softmax(neutral_scores)
        if len(parent_p) != len(candidates) or parent_p.sum() <= 0:
            parent_p = _softmax(np.asarray(scores, float))
        else:
            parent_p = np.maximum(parent_p, 0.0)
            parent_p /= parent_p.sum()

        j0 = int(record.get('selected_index', 0))
        if j0 < 0 or j0 >= len(candidates) or tuple(candidates[j0]) != tuple(anchor_seq):
            # Fall back to exact anchor lookup.  Duplicate candidates are allowed;
            # use the first matching bank entry deterministically.
            hits = [i for i, c in enumerate(candidates) if tuple(c) == tuple(anchor_seq)]
            if not hits:
                return None, 'ANCHOR_NOT_IN_PARENT_BANK'
            j0 = int(hits[0])

        common = np.minimum(parent_p, target_p)
        keep = float(common[j0] / max(float(parent_p[j0]), 1e-300))
        rr, digest = _side_rng(
            int(self.RUN_SEED), str(self.TARGET_BIF), record,
            str(self.F1LF_ROUTER_OFF_NAMESPACE)
        )
        if float(rr.random()) < keep:
            j = j0
        else:
            resid = np.maximum(target_p - common, 0.0)
            if resid.sum() <= 0:
                j = j0
            else:
                resid /= resid.sum()
                j = int(rr.choice(len(candidates), p=resid))
        child = tuple(candidates[j])

        record.update(
            v22_2_parent_selected=m.word_str(anchor_seq),
            v22_2_parent_selected_index=int(j0),
            v22_2_child_selected=m.word_str(child),
            v22_2_child_selected_index=int(j),
            v22_2_changed=bool(child != tuple(anchor_seq)),
            v22_2_parent_probabilities=parent_p.tolist(),
            v22_2_route_scores=route_scores.tolist(),
            v22_2_neutral_scores=neutral_scores.tolist(),
            v22_2_target_probabilities=target_p.tolist(),
            v22_2_keep_probability=float(keep),
            v22_2_selection_digest=digest,
            v22_2_child_seq=[int(x) for x in child],
        )
        return child, 'OK'

    def __call__(self, *args, **kwargs):
        st = self.state
        scope = bool(
            self.F1LF_ROUTER_OFF_ENABLED
            and self.is_f1lf_router_off_scope(st, args, kwargs)
        )

        # Crucially, run the complete parent selector unchanged.  This preserves
        # the current request's bank generation, accept/retry path and parent RNG.
        anchor = tuple(super().__call__(*args, **kwargs))
        if st is None or not anchor:
            return anchor

        record = self.last_request
        if record is not None:
            record.update(
                v22_2_model_id=self.MODEL_ID,
                v22_2_f1lf_router_off_scope=bool(scope),
                v22_2_f1lf_router_off_applied=False,
                v22_2_clock_safe_postaccept=True,
                v22_2_scope_definition=self.F1LF_ROUTER_OFF_SCOPE,
            )
        if not scope or record is None:
            return anchor

        child, reason = self._prepare_route_neutral_child(anchor, st, record)
        if child is None:
            record['v22_2_skip_reason'] = reason
            return anchor

        record.update(
            v22_2_f1lf_router_off_applied=True,
            v22_2_prepare_reason=reason,
            v22_2_candidate_bank_changed_by_patch=False,
            v22_2_current_request_parent_proposal_returned=True,
        )

        # Return the true parent word.  If this proposal is rejected, no v22.2
        # child is ever committed.  If accepted, commit_word/commit_surface below
        # switch to the prepared route-neutral child.
        return anchor

    def commit_word(self, seq, role, sr):
        record = self.last_request
        if record is not None and bool(record.get('v22_2_f1lf_router_off_applied', False)):
            child = tuple(int(x) for x in record['v22_2_child_seq'])
            self.state.bump('v22_2_f1lf_router_off_committed')
            self.state.bump('v22_2_f1lf_router_off_changed', int(child != tuple(seq)))
            return super().commit_word(child, role, sr)
        return super().commit_word(seq, role, sr)

    @staticmethod
    def _replace_stable_positions(surface_seq, child):
        z = list(surface_seq)
        pos = [i for i, x in enumerate(z)
               if isinstance(x, (int, np.integer)) and 0 <= int(x) < 22]
        if len(pos) != len(child):
            raise AssertionError(('stable-surface length mismatch', len(pos), len(child)))
        for i, g in zip(pos, child):
            z[i] = int(g)
        return tuple(z)

    def commit_surface(self, rseq, stable_seq, role, sr, row):
        record = self.last_request
        if record is None or not bool(record.get('v22_2_f1lf_router_off_applied', False)):
            return super().commit_surface(rseq, stable_seq, role, sr, row)

        child = tuple(int(x) for x in record['v22_2_child_seq'])
        visible_surface = self._replace_stable_positions(tuple(rseq), child)
        if len(child) != len(stable_seq):
            raise AssertionError('v22.2 changed stable glyph length')
        if int(m.stable_width(child)) != int(m.stable_width(stable_seq)):
            raise AssertionError('v22.2 changed stable physical width')

        row['stable_surface'] = m.word_str(child)
        row['surface'] = m.word_str(visible_surface)
        record['v22_2_parent_final_surface'] = record.get('final_surface')
        record['selected'] = m.word_str(child)
        record['selected_index'] = int(record.get('v22_2_child_selected_index', record.get('selected_index', 0)))
        record['direct_reason'] = 'V22_2_F1LF_ROUTE_ROUTER_OFF_POSTACCEPT'
        record['v22_2_visible_committed'] = True
        return super().commit_surface(visible_surface, child, role, sr, row)
