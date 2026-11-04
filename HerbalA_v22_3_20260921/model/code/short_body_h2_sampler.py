from __future__ import annotations

import hashlib
import json
import math
import numpy as np

import v19r_rb3_pw2_close1 as m
from route_map_model import subseqs
from preterm_sampler import V21PretermQMap9Sampler, terminal_close_score


def _request_rng(run_seed: int, bif: str, record: dict, namespace: str):
    payload = '|'.join([
        str(namespace), str(int(run_seed)), str(bif),
        str(record.get('page')), str(record.get('locus')),
        str(record.get('segment_id')), str(record.get('word_index')),
        str(record.get('proposal_id')),
    ]).encode('utf-8')
    dig = hashlib.sha256(payload).digest()
    seed = int.from_bytes(dig[:16], 'big', signed=False)
    return np.random.default_rng(seed), hashlib.sha256(payload).hexdigest()


def _external_only_h2_gain(tab, key, p0, eta: float):
    """Reproduce CorrectionTables.local_gain with KNOWN-3 removed.

    This deliberately retains the complete external Pure-A training residual
    (pe/p0) and removes only the target-leaf known-3 residual (pk/pe).
    """
    p0 = np.asarray(p0, dtype=float)
    if not eta:
        return np.ones(22, dtype=float)
    ex = tab.ex.get(key)
    pe = p0 if ex is None else (np.asarray(ex, float) + 16.0 * p0) / (float(np.asarray(ex).sum()) + 16.0)
    gain = np.ones(22, dtype=float)
    support = p0 > 0
    gain[support] = np.exp(float(eta) * np.clip(
        np.log(np.maximum(pe[support], 1e-15) / np.maximum(p0[support], 1e-15)),
        -2.0, 2.0,
    ))
    return gain


class V21PretermShortBodyH2GlobalSampler(V21PretermQMap9Sampler):
    """v21r+PRETERM with short-BODY H2|H1 KNOWN-3 residual disabled.

    Scope is intentionally narrow:
      * role=BODY and board=BODY (not W1/W2/LF/F1)
      * non-END word
      * exact glyph length 2..4
      * H1 is frozen, preserving the validated leaf-shared H1 signal
      * H3+ / terminal are frozen
      * H2 glyph physical width is frozen, therefore total word width is frozen
      * the complete external Pure-A H2 residual is retained
      * only target-leaf known-3 H2 residual is removed

    The transformation is implemented as a request-local maximal coupling from
    an explicit parent conditional over legal H2 alternatives to the same
    conditional with the known-3 component removed.  Parent RNG and semantic
    state are untouched.
    """

    SHORT_BODY_MIN_LEN = 2
    SHORT_BODY_MAX_LEN = 4
    SHORT_BODY_H2_KNOWN3_STRENGTH = 0.0  # 0 = fully external-only; 1 = parent known-3
    SHORT_BODY_H2_NAMESPACE = 'V21_SHORT_BODY_H2_EXTERNAL_ONLY_V1'

    def _h2_conditional_distributions(self, anchor_seq, args, kwargs, st, board, record):
        role = str(args[2])
        lp = int(args[4])
        R = int(args[6])
        end = bool(args[10])
        line_end = bool(kwargs.get('line_end_boundary', False))
        L = len(anchor_seq)
        if L < self.SHORT_BODY_MIN_LEN or L > self.SHORT_BODY_MAX_LEN:
            return None

        h1 = int(anchor_seq[0])
        h2_anchor = int(anchor_seq[1])
        tab = self.base.tables
        patch = self.base.patch
        physical_head = bool(st.word_index == 0 and st.segment_id == 0)
        g2_parent, g3 = tab.gains(role, lp, end, line_end, str(st.row_phase), str(board), physical_head, patch)
        p2_base = np.asarray(tab.base_nonend(role, lp, end, line_end, 1, m.START, h1), float)
        key = (str(st.row_phase), str(board), 1, m.START, h1)
        g2_external = _external_only_h2_gain(tab, key, p2_base, float(patch.eta_h2))

        strength = float(self.SHORT_BODY_H2_KNOWN3_STRENGTH)
        # strength=0 => external-only; strength=1 => exact parent gain.
        g2_target = np.exp(
            (1.0 - strength) * np.log(np.maximum(g2_external, 1e-300))
            + strength * np.log(np.maximum(np.asarray(g2_parent[h1], float), 1e-300))
        )

        parent_log = np.full(22, -np.inf, dtype=float)
        target_log = np.full(22, -np.inf, dtype=float)
        legal = np.zeros(22, dtype=bool)
        h2_width = int(m.WIDTH[h2_anchor])
        excluded_end = end and line_end if st.patch.boundary_policy == 'B_ALIGN' else end

        for h2 in range(22):
            if int(m.WIDTH[h2]) != h2_width:
                continue
            if p2_base[h2] <= 0 or g2_parent[h1, h2] <= 0 or g2_target[h2] <= 0:
                continue

            cand = list(anchor_seq)
            cand[1] = int(h2)
            cand = tuple(cand)
            if int(m.stable_width(cand)) != int(m.stable_width(anchor_seq)):
                continue
            if int(m.stable_width(cand)) + 2 > R:
                continue

            lp_parent = math.log(max(float(p2_base[h2] * g2_parent[h1, h2]), 1e-300))
            lp_target = math.log(max(float(p2_base[h2] * g2_target[h2]), 1e-300))

            # Condition on the already-selected H3+ so the intervention changes
            # H2 only and preserves all downstream glyphs.
            if L >= 3:
                h3 = int(anchor_seq[2])
                p3 = np.asarray(tab.base_nonend(role, lp, end, line_end, 2, h1, h2), float)
                p3 = p3 * np.asarray(g3[h1, h2], float)
                if p3[h3] <= 0:
                    continue
                z = math.log(max(float(p3[h3]), 1e-300))
                lp_parent += z
                lp_target += z

            if L >= 4:
                h3 = int(anchor_seq[2]); h4 = int(anchor_seq[3])
                p4 = np.asarray(tab.base_nonend(role, lp, end, line_end, 3, h2, h3), float)
                if p4[h4] <= 0:
                    continue
                z = math.log(max(float(p4[h4]), 1e-300))
                quad = args[1]
                if quad[h1, h2, h3, h4] == 0:
                    z += math.log(0.80)
                lp_parent += z
                lp_target += z

            # Preserve route/R4/bT selection pressures.  We remove only the
            # known-3 H2 local gain, not route memory or terminal calibration.
            sc, _ = st.candidate_features(cand)
            if role == 'BODY' and st.cfg.min_n <= 4 and len(cand) >= 4:
                ss = subseqs(tuple(int(x) for x in cand), 4)
                hits = ss & st.paths.get(4, frozenset())
                if hits:
                    pref = tuple(int(x) for x in cand[:4])
                    nh = len(hits) - int(pref in hits)
                    rest = float(st.cfg.beta * 2.0 * nh)
                    sc -= (1.0 - float(self.BODY_R4_LAMBDA)) * rest

            bt_enabled = self._bank_bt_enabled(st, role, cand, excluded_end, end, line_end)
            bt = tuple(int(x) for x in cand[-2:]) if len(cand) >= 2 else None
            if bt_enabled and bt in st.bt_active and st.bt_lambda:
                sc += st.bt_lambda
            if bt_enabled and bt is not None and st.bt_profile_lambda:
                sc += st.bt_profile_lambda * max(-2.0, min(2.0, float(st.bt_leafex.get(bt, 0.0))))

            # For L=2 H2 is also the terminal.  PRETERM has already been applied
            # by super().__call__; retain its terminal-family tilt in both arms.
            if L == 2 and bool(record.get('preterm_applied', False)):
                sc += float(self.PRETERM_CLOSE_LAMBDA) * float(terminal_close_score(h2))

            legal[h2] = True
            parent_log[h2] = lp_parent + float(sc)
            target_log[h2] = lp_target + float(sc)

        if not legal[h2_anchor]:
            return None

        def norm(logv):
            z = logv[legal].copy()
            z -= np.max(z)
            q = np.zeros(22, dtype=float)
            q[legal] = np.exp(z)
            q /= q.sum()
            return q

        return norm(parent_log), norm(target_log), legal, g2_parent[h1].copy(), g2_external.copy()

    def __call__(self, *args, **kwargs):
        st = self.state
        anchor_seq = tuple(super().__call__(*args, **kwargs))
        if st is None or not anchor_seq:
            return anchor_seq

        role = str(args[2])
        R = int(args[6])
        end = bool(args[10])
        line_end = bool(kwargs.get('line_end_boundary', False))
        board = st.board(role, end, line_end)
        record = self.last_request
        if record is not None:
            record.update(
                short_body_h2_applied=False,
                short_body_h2_known3_strength=float(self.SHORT_BODY_H2_KNOWN3_STRENGTH),
                short_body_h2_scope='BODY_LEN2_4_EXTERNAL_ONLY_H2_GIVEN_H1',
            )

        if (
            record is None or role != 'BODY' or str(board) != 'BODY' or end or
            len(anchor_seq) < int(self.SHORT_BODY_MIN_LEN) or
            len(anchor_seq) > int(self.SHORT_BODY_MAX_LEN)
        ):
            return anchor_seq

        rng_before = json.dumps(args[5].bit_generator.state, sort_keys=True, default=str)
        sem_before = st.semantic_digest()
        out = self._h2_conditional_distributions(anchor_seq, args, kwargs, st, board, record)
        if out is None:
            record['short_body_h2_skip_reason'] = 'NO_LEGAL_CONDITIONAL'
            return anchor_seq
        q_parent, q_target, legal, g_parent, g_external = out

        h2_0 = int(anchor_seq[1])
        common = np.minimum(q_parent, q_target)
        keep_prob = float(common[h2_0] / max(q_parent[h2_0], 1e-300))
        rr, digest = _request_rng(int(self.RUN_SEED), str(self.TARGET_BIF), record, self.SHORT_BODY_H2_NAMESPACE)
        u = float(rr.random())
        if u < keep_prob:
            h2_sel = h2_0
            changed = False
        else:
            resid = np.maximum(q_target - common, 0.0)
            if resid.sum() <= 0:
                h2_sel = h2_0
                changed = False
            else:
                resid /= resid.sum()
                h2_sel = int(rr.choice(22, p=resid))
                changed = (h2_sel != h2_0)

        selected = list(anchor_seq)
        selected[1] = int(h2_sel)
        selected = tuple(selected)

        assert selected[0] == anchor_seq[0]
        assert selected[2:] == anchor_seq[2:]
        assert len(selected) == len(anchor_seq)
        assert int(m.WIDTH[selected[1]]) == int(m.WIDTH[anchor_seq[1]])
        assert int(m.stable_width(selected)) == int(m.stable_width(anchor_seq))
        assert int(m.stable_width(selected)) + 2 <= R
        assert legal[h2_sel]

        record.update(
            short_body_h2_applied=True,
            short_body_h2_changed=bool(changed),
            short_body_h2_anchor=m.word_str(anchor_seq),
            short_body_h2_selected=m.word_str(selected),
            short_body_h2_anchor_h1=int(anchor_seq[0]),
            short_body_h2_anchor_h2=int(h2_0),
            short_body_h2_selected_h2=int(h2_sel),
            short_body_h2_anchor_h1_name=m.I2G[int(anchor_seq[0])],
            short_body_h2_anchor_h2_name=m.I2G[int(h2_0)],
            short_body_h2_selected_h2_name=m.I2G[int(h2_sel)],
            short_body_h2_parent_known_gain=float(g_parent[h2_0]),
            short_body_h2_external_gain=float(g_external[h2_sel]),
            short_body_h2_parent_prob=float(q_parent[h2_0]),
            short_body_h2_target_prob=float(q_target[h2_sel]),
            short_body_h2_keep_prob=float(keep_prob),
            short_body_h2_selection_digest=digest,
            selected=m.word_str(selected),
            direct=False,
            direct_reason='V21_PRETERM_SHORT_BODY_H2_EXTERNAL_ONLY_V1',
        )
        st.bump('short_body_h2_events')
        st.bump('short_body_h2_changed', int(changed))
        st.last_proposal.update(
            short_body_h2_global=True,
            short_body_h2_changed=bool(changed),
            short_body_h2_anchor=m.word_str(anchor_seq),
            short_body_h2_selected=m.word_str(selected),
            short_body_h2_length=int(len(selected)),
        )
        assert json.dumps(args[5].bit_generator.state, sort_keys=True, default=str) == rng_before
        assert st.semantic_digest() == sem_before
        record['short_body_h2_parent_rng_untouched'] = True
        record['short_body_h2_semantic_state_untouched'] = True
        return selected


class V21PretermShortBodyH2NoOpSampler(V21PretermShortBodyH2GlobalSampler):
    """Audit arm: strength=1 must reproduce PRETERM_QMAP9 exactly."""
    SHORT_BODY_H2_KNOWN3_STRENGTH = 1.0
    SHORT_BODY_H2_NAMESPACE = 'V21_SHORT_BODY_H2_NOOP_V1'
