from __future__ import annotations

import hashlib
import json
import math
import numpy as np

import v19r_rb3_pw2_close1 as m
from route_map_model import subseqs
from paragraph_h1_sampler import V21ParagraphH1RunningSampler


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


def _normalize_nonend_cdf_row(row):
    p = np.maximum(np.diff(np.r_[0.0, np.asarray(row, dtype=float)])[:22], 0.0)
    s = float(p.sum())
    return p / s if s > 0 else p


def _known_only_gain(tab, key, p0, eta: float, tau: float):
    """Known-3 shrinkage around *p0*, with external correction disabled."""
    p0 = np.asarray(p0, dtype=float)
    if not eta:
        return np.ones(22, dtype=float)
    kn = tab.kn.get(key)
    pk = p0 if kn is None else (np.asarray(kn, float) + float(tau) * p0) / (float(np.asarray(kn).sum()) + float(tau))
    gain = np.ones(22, dtype=float)
    support = p0 > 0
    gain[support] = np.exp(float(eta) * np.clip(
        np.log(np.maximum(pk[support], 1e-15) / np.maximum(p0[support], 1e-15)),
        -2.0, 2.0,
    ))
    return gain


class V22rW2B2Sampler(V21ParagraphH1RunningSampler):
    """Accepted W2-B2 local repair layered over HerbalA-v22r.

    Scope (frozen by the 2026-09-17 validation):
      * row_phase == MIDDLE
      * role == board == W2
      * non-END request
      * exact stable glyph length 3..5
      * H2 only; H1/H3+/terminal/exact length/stable width frozen

    Target H2 law:
      * keep the W2-position CDF for H2 (cdf mo=3, wp=1, depth=1)
      * external H2 residual OFF
      * target-leaf known-3 H2 residual shrunk with tau=128

    The intervention is staged post-commit. Parent selection, route/bT state,
    packing, rare-glyph logic, paragraph-H1 state and the parent RNG all see
    the exact v22r parent anchor. Only the visible committed H2 is changed.
    """

    W2_B2_ENABLED = True
    W2_B2_MIN_LEN = 3
    W2_B2_MAX_LEN = 5
    W2_B2_KNOWN_TAU = 128.0
    W2_B2_NAMESPACE = 'V22R_W2_H2_B2_MINIMAL_V1'

    def _w2pos_h2_base(self, tab, lp: int, h1: int):
        # Literal parent CDF but keep W2 word-position layer (wp=1) for H2.
        row = tab.cdf[3, 1, int(lp), int(m.START), int(h1), 1]
        return _normalize_nonend_cdf_row(row)

    def _h2_distributions(self, anchor_seq, args, kwargs, st, board):
        role = str(args[2])
        lp = int(args[4])
        R = int(args[6])
        end = bool(args[10])
        line_end = bool(kwargs.get('line_end_boundary', False))
        L = len(anchor_seq)
        if L < int(self.W2_B2_MIN_LEN) or L > int(self.W2_B2_MAX_LEN):
            return None

        h1 = int(anchor_seq[0])
        h2_anchor = int(anchor_seq[1])
        tab = self.base.tables
        patch = self.base.patch
        physical_head = bool(st.word_index == 0 and st.segment_id == 0)
        g2_parent, g3 = tab.gains(role, lp, end, line_end, str(st.row_phase), str(board), physical_head, patch)

        p_parent_base = np.asarray(tab.base_nonend(role, lp, end, line_end, 1, m.START, h1), float)
        p_target_base = self._w2pos_h2_base(tab, lp, h1)
        key = (str(st.row_phase), str(board), 1, m.START, h1)
        g_target = _known_only_gain(tab, key, p_target_base, float(patch.eta_h2), float(self.W2_B2_KNOWN_TAU))

        parent_log = np.full(22, -np.inf, dtype=float)
        target_log = np.full(22, -np.inf, dtype=float)
        legal = np.zeros(22, dtype=bool)
        h2_width = int(m.WIDTH[h2_anchor])
        excluded_end = end and line_end if st.patch.boundary_policy == 'B_ALIGN' else end

        for h2 in range(22):
            if int(m.WIDTH[h2]) != h2_width:
                continue
            if p_parent_base[h2] <= 0 or g2_parent[h1, h2] <= 0:
                continue
            if p_target_base[h2] <= 0 or g_target[h2] <= 0:
                continue
            cand = list(anchor_seq)
            cand[1] = int(h2)
            cand = tuple(cand)
            if int(m.stable_width(cand)) != int(m.stable_width(anchor_seq)):
                continue
            if int(m.stable_width(cand)) + 2 > R:
                continue

            lp_parent = math.log(max(float(p_parent_base[h2] * g2_parent[h1, h2]), 1e-300))
            lp_target = math.log(max(float(p_target_base[h2] * g_target[h2]), 1e-300))

            # Condition on frozen H3+ exactly as far as the H2 choice can affect
            # the parent Markov/quad probability (H3 and H4/H5 quad bridge).
            h3 = int(anchor_seq[2])
            p3 = np.asarray(tab.base_nonend(role, lp, end, line_end, 2, h1, h2), float)
            p3 = p3 * np.asarray(g3[h1, h2], float)
            if p3[h3] <= 0:
                continue
            z = math.log(max(float(p3[h3]), 1e-300))
            lp_parent += z; lp_target += z

            if L >= 4:
                h4 = int(anchor_seq[3])
                p4 = np.asarray(tab.base_nonend(role, lp, end, line_end, 3, h2, h3), float)
                if p4[h4] <= 0:
                    continue
                z = math.log(max(float(p4[h4]), 1e-300))
                if args[1][h1, h2, h3, h4] == 0:
                    z += math.log(0.80)
                lp_parent += z; lp_target += z

            if L >= 5:
                h4 = int(anchor_seq[3]); h5 = int(anchor_seq[4])
                # At depth 4 the base row no longer depends on H2 directly, but
                # the 4-gram gate does. Include it to condition on frozen H5.
                p5 = np.asarray(tab.base_nonend(role, lp, end, line_end, 4, h3, h4), float)
                if p5[h5] <= 0:
                    continue
                z = math.log(max(float(p5[h5]), 1e-300))
                if args[1][h2, h3, h4, h5] == 0:
                    z += math.log(0.80)
                lp_parent += z; lp_target += z

            # Preserve parent selector pressures; only the local H2 law changes.
            sc, _ = st.candidate_features(cand)
            bt_enabled = self._bank_bt_enabled(st, role, cand, excluded_end, end, line_end)
            bt = tuple(int(x) for x in cand[-2:]) if len(cand) >= 2 else None
            if bt_enabled and bt in st.bt_active and st.bt_lambda:
                sc += st.bt_lambda
            if bt_enabled and bt is not None and st.bt_profile_lambda:
                sc += st.bt_profile_lambda * max(-2.0, min(2.0, float(st.bt_leafex.get(bt, 0.0))))

            legal[h2] = True
            parent_log[h2] = lp_parent + float(sc)
            target_log[h2] = lp_target + float(sc)

        if not legal[h2_anchor]:
            return None

        def norm(logv):
            q = np.zeros(22, dtype=float)
            good = legal & np.isfinite(logv)
            z = logv[good].copy()
            z -= np.max(z)
            q[good] = np.exp(z)
            q /= q.sum()
            return q

        return norm(parent_log), norm(target_log), legal, p_parent_base, p_target_base, g2_parent[h1].copy(), g_target.copy()

    def __call__(self, *args, **kwargs):
        st = self.state
        anchor_seq = tuple(super().__call__(*args, **kwargs))
        if st is None or not anchor_seq:
            return anchor_seq

        record = self.last_request
        role = str(args[2])
        R = int(args[6])
        end = bool(args[10])
        line_end = bool(kwargs.get('line_end_boundary', False))
        board = st.board(role, end, line_end)
        if record is not None:
            record.update(
                b2_h2_applied=False,
                b2_h2_changed=False,
                b2_h2_scope='MIDDLE_W2_LEN3_5_H2_ONLY_W2POS_EXT_OFF_KNOWN_TAU128',
                b2_h2_known_tau=float(self.W2_B2_KNOWN_TAU),
            )

        if (
            record is None or not self.W2_B2_ENABLED or
            role != 'W2' or str(board) != 'W2' or str(st.row_phase) != 'MIDDLE' or end or
            len(anchor_seq) < int(self.W2_B2_MIN_LEN) or len(anchor_seq) > int(self.W2_B2_MAX_LEN)
        ):
            return anchor_seq

        rng_before = json.dumps(args[5].bit_generator.state, sort_keys=True, default=str)
        sem_before = st.semantic_digest()
        out = self._h2_distributions(anchor_seq, args, kwargs, st, board)
        if out is None:
            record['b2_h2_skip_reason'] = 'NO_LEGAL_H2_CONDITIONAL'
            return anchor_seq
        q_parent, q_target, legal, p_parent_base, p_target_base, g_parent, g_target = out

        h2_0 = int(anchor_seq[1])
        common = np.minimum(q_parent, q_target)
        keep_prob = float(common[h2_0] / max(q_parent[h2_0], 1e-300))
        rr, digest = _side_rng(int(self.RUN_SEED), str(self.TARGET_BIF), record, self.W2_B2_NAMESPACE)
        if float(rr.random()) < keep_prob:
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
            b2_h2_applied=True,
            b2_h2_changed=bool(changed),
            b2_h2_anchor=m.word_str(anchor_seq),
            b2_h2_anchor_seq=[int(x) for x in anchor_seq],
            b2_h2_selected=m.word_str(selected),
            b2_h2_anchor_h2=int(h2_0),
            b2_h2_selected_h2=int(h2_sel),
            b2_h2_anchor_len=int(len(anchor_seq)),
            b2_h2_anchor_width=int(m.stable_width(anchor_seq)),
            b2_h2_parent_prob=float(q_parent[h2_0]),
            b2_h2_target_prob=float(q_target[h2_sel]),
            b2_h2_keep_prob=float(keep_prob),
            b2_h2_parent_distribution=q_parent.tolist(),
            b2_h2_target_distribution=q_target.tolist(),
            b2_h2_selection_digest=digest,
            b2_h2_staged_postcommit=True,
        )
        st.bump('w2_b2_events')
        st.bump('w2_b2_changed', int(changed))
        assert json.dumps(args[5].bit_generator.state, sort_keys=True, default=str) == rng_before
        assert st.semantic_digest() == sem_before
        record['b2_h2_parent_rng_untouched'] = True
        record['b2_h2_semantic_state_untouched'] = True
        # Keep exact parent anchor in all semantic/packing machinery.
        return anchor_seq

    def commit_surface(self, rseq, stable_seq, role, sr, row):
        st = self.state
        record = self.last_request
        super().commit_surface(rseq, stable_seq, role, sr, row)
        if record is None or not bool(record.get('b2_h2_changed', False)):
            return

        h2_sel = int(record['b2_h2_selected_h2'])
        actual_stable = tuple(stable_seq)
        if len(actual_stable) < 2:
            raise AssertionError('B2 committed stable word too short')
        z = list(actual_stable)
        z[1] = h2_sel
        actual_stable = tuple(z)
        if int(m.WIDTH[int(stable_seq[1])]) != int(m.WIDTH[h2_sel]):
            raise AssertionError('B2 H2 postcommit width mismatch')
        if int(m.stable_width(actual_stable)) != int(m.stable_width(stable_seq)):
            raise AssertionError('B2 stable width mismatch')

        actual_surface = tuple(rseq)
        zr = list(actual_surface)
        stable_positions = [i for i, x in enumerate(zr) if isinstance(x, (int, np.integer))]
        if len(stable_positions) < 2:
            raise AssertionError('B2 surface has fewer than two stable glyphs')
        pos = stable_positions[1]
        if int(m.WIDTH[int(zr[pos])]) != int(m.WIDTH[h2_sel]):
            raise AssertionError('B2 surface H2 width mismatch')
        zr[pos] = h2_sel
        actual_surface = tuple(zr)

        row['stable_surface'] = m.word_str(actual_stable)
        row['surface'] = m.word_str(actual_surface)
        st.surface_commits[-1]['stable_surface'] = row['stable_surface']
        st.surface_commits[-1]['surface'] = row['surface']
        record['final_surface'] = row['surface']
        record['b2_h2_postcommit_written'] = True
        record['b2_h2_route_state_frozen'] = True


class V22rW2B2NoOpSampler(V22rW2B2Sampler):
    W2_B2_ENABLED = False
