from __future__ import annotations

"""HerbalA-v22.3 Stage-3D candidate: strict F1-LF terminal proposal only.

Parent: HerbalA-v22.2.

The parent request, candidate bank, accept/retry path, packing and RNG clock run
unchanged.  v22.2 first stages its route-neutral accepted child.  For the frozen
strict F1-LF scope only, this class then freezes that child's prefix and proposes
one terminal glyph from the Stage-2-confirmed length-aware terminal law.

No post-commit terminal-index rewrite is used.  The final child is staged
before commit.  To keep the 5--6g route mechanism frozen, commit_word follows
v22.2 exactly and commits the v22.2 route-neutral base child to MapState.  The
Stage3D terminal-modified final child is materialized only in commit_surface,
where it becomes both the visible terminal and semantic prev_terminal.
STOP/CONTINUE is inherited unchanged from v22.2.
"""

import hashlib
from typing import Any
import numpy as np
import v19r_rb3_pw2_close1 as m

from f1lf_router_off_sampler import V222F1LFRouterOffSampler
from f1lf_length_terminal_law import TerminalLaw, law_invariants


def _stage3_rng(run_seed: int, bif: str, record: dict, namespace: str):
    payload = '|'.join([
        str(namespace), str(int(run_seed)), str(bif),
        str(record.get('page')), str(record.get('locus')),
        str(record.get('segment_id')), str(record.get('word_index')),
        str(record.get('proposal_id')),
    ]).encode('utf-8')
    dig = hashlib.sha256(payload).digest()
    seed = int.from_bytes(dig[:16], 'big', signed=False)
    return np.random.default_rng(seed), hashlib.sha256(payload).hexdigest()


class V223F1LFLengthTerminalSampler(V222F1LFRouterOffSampler):
    MODEL_ID = 'HerbalA-v22.3-STAGE3D-R1-CANDIDATE'
    PARENT_MODEL_ID = 'HerbalA-v22.2'
    STAGE3D_ENABLED = True
    STAGE3D_NAMESPACE = 'V22_3_F1LF_LENGTH_TERMINAL_STAGE3D_V1'
    STAGE3D_STRICT_KEYS = frozenset()
    STAGE3D_LAW: TerminalLaw | None = None

    @classmethod
    def configure_stage3d(cls, strict_keys, law: TerminalLaw, namespace: str | None = None):
        cls.STAGE3D_STRICT_KEYS = frozenset((str(p), str(l)) for p, l in strict_keys)
        cls.STAGE3D_LAW = law
        if namespace:
            cls.STAGE3D_NAMESPACE = str(namespace)
        inv = law_invariants(law)
        if (inv['probability_sum_error'] > 1e-12 or inv['l_inheritance_error'] > 1e-12 or
                inv['non_l_ratio_error'] > 1e-10 or inv['y_n_ratio_error'] > 1e-10 or
                inv['support_changes'] != 0 or not inv['finite'] or not inv['nonnegative']):
            raise AssertionError(('Invalid Stage3D terminal law', inv))
        return cls

    @classmethod
    def _strict_record_scope(cls, st: Any, record: dict | None) -> bool:
        if not cls.STAGE3D_ENABLED or st is None or record is None:
            return False
        if not bool(record.get('v22_2_f1lf_router_off_scope', False)):
            return False
        key = (str(record.get('page')), str(record.get('locus')))
        if key not in cls.STAGE3D_STRICT_KEYS:
            return False
        # Reassert live invariants rather than trusting the ledger alone.
        return (
            str(record.get('role')) == 'F1'
            and str(record.get('row_phase')) == 'FIRST'
            and int(record.get('segment_id', -1)) == 0
            and str(record.get('board')) == 'LF'
            and bool(record.get('end'))
            and bool(record.get('line_end_boundary'))
        )

    @staticmethod
    def _legal_terminal_mask(seq, args):
        """Preserve live support, exact glyph length and physical width.

        Support comes from the parent's F1-LF non-END row at the frozen prefix.
        The selector never creates a new candidate-bank entry; it only resolves
        the terminal slot of the already accepted same-width child.
        """
        d = len(seq) - 1
        if d < 0:
            return None, None
        a = int(m.START if d < 2 else seq[d-2])
        b = int(m.START if d < 1 else seq[d-1])
        sampler = None
        # ``args`` is only used for the immutable quad table below; the calling
        # method supplies the parent row through self.base.tables.
        return (d, a, b), np.asarray(args[1])

    def _live_support(self, seq, args, kwargs, st):
        key, quad = self._legal_terminal_mask(seq, args)
        if key is None:
            return None
        d, a, b = key
        role = str(args[2])
        lp = int(args[4])
        end = bool(args[10])
        line_end = bool(kwargs.get('line_end_boundary', False))
        tab = self.base.tables
        p = np.asarray(tab.base_nonend(role, lp, end, line_end, d, a, b), float).copy()
        # Support only: restore the same early correction / quad zero policy used
        # by the parent, though positive gains cannot create new support.
        physical_head = bool(st.word_index == 0 and st.segment_id == 0)
        g2, g3 = tab.gains(role, lp, end, line_end, str(st.row_phase), 'LF', physical_head, self.base.patch)
        if d == 1:
            p *= np.asarray(g2[b], float)
        elif d == 2:
            p *= np.asarray(g3[a, b], float)
        if d >= 3:
            p3, p2, p1 = map(int, seq[d-3:d])
            for t in range(22):
                if quad[p3, p2, p1, t] == 0:
                    p[t] *= 0.80
        tw = int(m.WIDTH[int(seq[-1])])
        legal = (p > 0) & (np.asarray(m.WIDTH[:22], int) == tw)
        if not legal[int(seq[-1])]:
            return None
        return legal

    def _stage_terminal_child(self, base_child, args, kwargs, st, record):
        law = self.STAGE3D_LAW
        if law is None:
            return None, 'NO_STAGE3D_LAW'
        seq = tuple(int(x) for x in base_child)
        if not seq:
            return None, 'EMPTY_CHILD'
        legal = self._live_support(seq, args, kwargs, st)
        if legal is None or not np.any(legal):
            return None, 'NO_LEGAL_TERMINAL_SUPPORT'

        short = len(seq) <= 3
        raw = law.short() if short else law.long()
        target = np.asarray(raw, float).copy()
        target[~legal] = 0.0
        if not np.all(np.isfinite(target)) or target.sum() <= 0:
            return None, 'INVALID_TARGET_AFTER_LEGAL_MASK'
        target /= target.sum()

        rr, digest = _stage3_rng(
            int(self.RUN_SEED), str(self.TARGET_BIF), record, str(self.STAGE3D_NAMESPACE)
        )
        tsel = int(rr.choice(22, p=target))
        out = tuple(seq[:-1]) + (tsel,)
        if out[:-1] != seq[:-1]:
            raise AssertionError('Stage3D changed F1 prefix')
        if len(out) != len(seq):
            raise AssertionError('Stage3D changed glyph length')
        if int(m.WIDTH[out[-1]]) != int(m.WIDTH[seq[-1]]):
            raise AssertionError('Stage3D changed terminal physical width')
        if int(m.stable_width(out)) != int(m.stable_width(seq)):
            raise AssertionError('Stage3D changed word physical width')
        if not legal[tsel]:
            raise AssertionError('Stage3D selected unsupported terminal')

        record.update(
            v22_3_stage3d_applied=True,
            v22_3_stage3d_selector=('SHORT_NORMAL_MIDDLE_LF' if short else 'LONG_F1_PLUS_NORMAL_LF_L'),
            v22_3_stage3d_base_child=m.word_str(seq),
            v22_3_stage3d_final_child=m.word_str(out),
            v22_3_stage3d_base_terminal=int(seq[-1]),
            v22_3_stage3d_final_terminal=int(tsel),
            v22_3_stage3d_base_terminal_name=m.I2G[int(seq[-1])],
            v22_3_stage3d_final_terminal_name=m.I2G[int(tsel)],
            v22_3_stage3d_changed=bool(out != seq),
            v22_3_stage3d_target_probabilities=target.tolist(),
            v22_3_stage3d_legal_support=[bool(x) for x in legal],
            v22_3_stage3d_selection_digest=digest,
            v22_3_stage3d_child_seq=[int(x) for x in out],
            v22_3_stage3d_prefix_frozen=True,
            v22_3_stage3d_stop_changed=False,
            v22_3_stage3d_candidate_bank_changed=False,
            v22_3_stage3d_parent_rng_untouched=True,
        )
        return out, 'OK'

    def __call__(self, *args, **kwargs):
        st = self.state
        # Complete v22.2 request first.  It preserves the parent's current
        # request clock and stages the route-neutral child if applicable.
        anchor = tuple(super().__call__(*args, **kwargs))
        record = self.last_request
        if record is not None:
            record.update(
                v22_3_model_id=self.MODEL_ID,
                v22_3_parent_model_id=self.PARENT_MODEL_ID,
                v22_3_stage3d_applied=False,
                v22_3_stage3d_strict_scope=False,
            )
        if st is None or not anchor or record is None:
            return anchor
        strict = self._strict_record_scope(st, record)
        record['v22_3_stage3d_strict_scope'] = bool(strict)
        if not strict:
            return anchor

        base_child = tuple(int(x) for x in record.get('v22_2_child_seq', anchor))
        final_child, reason = self._stage_terminal_child(base_child, args, kwargs, st, record)
        if final_child is None:
            record['v22_3_stage3d_skip_reason'] = reason
            return anchor
        record['v22_3_stage3d_prepare_reason'] = reason
        # Return the exact parent anchor to packing/retry.  The final child is
        # used only if this request is actually committed.
        return anchor

    def commit_word(self, seq, role, sr):
        record = self.last_request
        if record is not None and bool(record.get('v22_3_stage3d_applied', False)):
            final_child = tuple(int(x) for x in record['v22_3_stage3d_child_seq'])
            base_child = tuple(int(x) for x in record.get('v22_2_child_seq', seq))
            if len(final_child) != len(base_child):
                raise AssertionError('Stage3D route/base glyph length mismatch')
            if int(m.stable_width(final_child)) != int(m.stable_width(base_child)):
                raise AssertionError('Stage3D route/base physical width mismatch')
            self.state.bump('v22_3_stage3d_committed')
            self.state.bump('v22_3_stage3d_changed', int(final_child != base_child))
            record['v22_3_stage3d_route_commit_child'] = m.word_str(base_child)
            record['v22_3_stage3d_visible_commit_child'] = m.word_str(final_child)
            record['v22_3_stage3d_route_uses_v22_2_base_child'] = True
            # IMPORTANT: use the exact v22.2 commit path here.  V222's
            # commit_word substitutes v22_2_child_seq and therefore commits the
            # parent's route-neutral child to MapState.  The Stage3D final
            # terminal is deliberately withheld until commit_surface below.
            return super().commit_word(seq, role, sr)
        return super().commit_word(seq, role, sr)

    def commit_surface(self, rseq, stable_seq, role, sr, row):
        record = self.last_request
        if record is None or not bool(record.get('v22_3_stage3d_applied', False)):
            return super().commit_surface(rseq, stable_seq, role, sr, row)

        child = tuple(int(x) for x in record['v22_3_stage3d_child_seq'])
        visible_surface = self._replace_stable_positions(tuple(rseq), child)
        if len(child) != len(stable_seq):
            raise AssertionError('Stage3D changed stable glyph length')
        if int(m.stable_width(child)) != int(m.stable_width(stable_seq)):
            raise AssertionError('Stage3D changed stable physical width')

        row['stable_surface'] = m.word_str(child)
        row['surface'] = m.word_str(visible_surface)
        record['v22_3_parent_final_surface'] = record.get('final_surface')
        record['selected'] = m.word_str(child)
        record['direct_reason'] = 'V22_3_STAGE3D_F1LF_LENGTH_TERMINAL_PRECOMMIT'
        record['v22_3_visible_committed'] = True
        # Skip v22.2 commit_surface substitution: route memory was already
        # committed from the v22.2 base child in commit_word.  Here only the
        # visible surface and semantic prev_terminal receive the Stage3D child.
        route_before = self.state.current
        ret = super(V222F1LFRouterOffSampler, self).commit_surface(
            visible_surface, child, role, sr, row
        )
        if self.state.current != route_before:
            raise AssertionError(('Stage3D commit_surface changed route current', route_before, self.state.current))
        record['v22_3_stage3d_route_state_frozen_on_surface_commit'] = True
        expected = m.I2G[self.state.prev_terminal] if self.state.prev_terminal is not None else None
        if expected != m.I2G[int(child[-1])]:
            raise AssertionError(('Visible/semantic terminal mismatch', expected, m.I2G[int(child[-1])]))
        record['v22_3_visible_semantic_terminal_match'] = True
        return ret
