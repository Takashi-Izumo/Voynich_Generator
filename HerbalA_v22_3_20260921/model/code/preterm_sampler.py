from __future__ import annotations

import hashlib
import json
import math
import numpy as np

import v19r_rb3_pw2_close1 as m
from route_map_model import subseqs
from integrated_sampler_v21 import V21SafeLeftBtOffSampler


TERMINAL_LR = frozenset((int(m.G2I['l']), int(m.G2I['r'])))
TERMINAL_NMY = frozenset((int(m.G2I['n']), int(m.G2I['m']), int(m.G2I['y'])))


def terminal_close_score(g: int) -> int:
    g = int(g)
    if g in TERMINAL_NMY:
        return 1
    if g in TERMINAL_LR:
        return -1
    return 0


def _rng_from_record(run_seed: int, bif: str, record: dict, namespace: str):
    payload = '|'.join([
        str(namespace), str(int(run_seed)), str(bif),
        str(record.get('page')), str(record.get('locus')),
        str(record.get('segment_id')), str(record.get('word_index')),
        str(record.get('proposal_id')),
    ]).encode('utf-8')
    dig = hashlib.sha256(payload).digest()
    seed = int.from_bytes(dig[:16], 'big', signed=False)
    return np.random.default_rng(seed), hashlib.sha256(payload).hexdigest()


class V21PretermTerminalSampler(V21SafeLeftBtOffSampler):
    """v21r SAFE_LEFT_BT_OFF + localized preterminal terminal-family hold.

    Scope:
      * role=BODY
      * board=BODY (therefore not the actual LF word)
      * non-END request
      * runtime remaining width R <= PRETERM_R_MAX
      * exact glyph length is frozen
      * prefix H1..H(L-1) is frozen
      * terminal physical glyph width is frozen

    The only behavioral change is an exponential tilt of the terminal family:
      close_score = +1 for n/m/y, -1 for l/r, 0 otherwise
      weight *= exp(PRETERM_CLOSE_LAMBDA * close_score)

    PRETERM_CLOSE_LAMBDA is negative, so n/m/y are suppressed and l/r promoted.
    Selection uses a SHA-256 request-local side stream and maximal coupling,
    so lambda=0 is an exact no-op and the parent RNG/semantic state are untouched.
    """

    PRETERM_R_MAX = 9
    PRETERM_CLOSE_LAMBDA = -0.29704000178961015
    RUN_SEED = 0
    TARGET_BIF = ''
    PRETERM_NAMESPACE = 'V21_PRETERM_TERMINAL_V1'

    def _parent_terminal_distribution(self, anchor_seq, args, kwargs, st, board):
        role = args[2]
        lp = int(args[4])
        R = int(args[6])
        end = bool(args[10])
        line_end = bool(kwargs.get('line_end_boundary', False))
        d = len(anchor_seq) - 1
        if d < 1:
            return None, None

        a = int(m.START if d < 2 else anchor_seq[d-2])
        b = int(anchor_seq[d-1])
        tab = self.base.tables
        p = np.asarray(tab.base_nonend(role, lp, end, line_end, d, a, b), float).copy()

        # Restore the same early-depth non-END corrections used by the live entry sampler.
        physical_head = bool(st.word_index == 0 and st.segment_id == 0)
        g2, g3 = tab.gains(role, lp, end, line_end, str(st.row_phase), str(board), physical_head, self.base.patch)
        if d == 1:
            p *= np.asarray(g2[b], float)
        elif d == 2:
            p *= np.asarray(g3[a, b], float)

        # Restore the parent's 4-gram support penalty at depth >= 3.
        if d >= 3:
            p3, p2, p1 = map(int, anchor_seq[d-3:d])
            quad = args[1]
            for t in range(22):
                if quad[p3, p2, p1, t] == 0:
                    p[t] *= 0.80

        # Hard invariants: preserve exact word length, prefix and terminal glyph width;
        # keep the non-END packing fit identical to the parent request.
        anchor_tw = int(m.WIDTH[int(anchor_seq[-1])])
        prefix_w = int(sum(int(m.WIDTH[int(x)]) for x in anchor_seq[:-1]))
        legal = np.zeros(22, dtype=bool)
        parent_scores = np.full(22, -np.inf, dtype=float)
        excluded_end = end and line_end if st.patch.boundary_policy == 'B_ALIGN' else end
        bt_enabled = self._bank_bt_enabled(st, role, anchor_seq, excluded_end, end, line_end)

        for t in range(22):
            if p[t] <= 0 or int(m.WIDTH[t]) != anchor_tw:
                continue
            if prefix_w + int(m.WIDTH[t]) + 2 > R:
                continue
            cand = tuple(anchor_seq[:-1]) + (int(t),)
            sc, _ = st.candidate_features(cand)
            if role == 'BODY' and st.cfg.min_n <= 4 and len(cand) >= 4:
                ss = subseqs(tuple(int(x) for x in cand), 4)
                hits = ss & st.paths.get(4, frozenset())
                if hits:
                    pref = tuple(int(x) for x in cand[:4])
                    nh = len(hits) - int(pref in hits)
                    rest = float(st.cfg.beta * 2.0 * nh)
                    sc -= (1.0 - float(self.BODY_R4_LAMBDA)) * rest
            bt = tuple(int(x) for x in cand[-2:]) if len(cand) >= 2 else None
            if bt_enabled and bt in st.bt_active and st.bt_lambda:
                sc += st.bt_lambda
            if bt_enabled and bt is not None and st.bt_profile_lambda:
                sc += st.bt_profile_lambda * max(-2., min(2., float(st.bt_leafex.get(bt, 0.))))
            legal[t] = True
            parent_scores[t] = math.log(max(float(p[t]), 1e-300)) + float(sc)

        if not legal[int(anchor_seq[-1])]:
            # The live anchor itself must always remain a legal option. If not, fail safe.
            return None, None
        z = parent_scores[legal]
        z -= np.max(z)
        q = np.zeros(22, float)
        q[legal] = np.exp(z)
        q /= q.sum()
        return q, legal

    def __call__(self, *args, **kwargs):
        st = self.state
        anchor_seq = tuple(super().__call__(*args, **kwargs))
        if st is None or not anchor_seq:
            return anchor_seq

        role = args[2]
        R = int(args[6])
        end = bool(args[10])
        line_end = bool(kwargs.get('line_end_boundary', False))
        board = st.board(role, end, line_end)
        record = self.last_request
        if record is not None:
            record.update(
                preterm_applied=False,
                preterm_threshold=int(self.PRETERM_R_MAX),
                preterm_close_lambda=float(self.PRETERM_CLOSE_LAMBDA),
            )

        if (
            record is None or role != 'BODY' or str(board) != 'BODY' or end or
            R > int(self.PRETERM_R_MAX) or len(anchor_seq) < 2
        ):
            return anchor_seq

        rng_before = json.dumps(args[5].bit_generator.state, sort_keys=True, default=str)
        sem_before = st.semantic_digest()
        q, legal = self._parent_terminal_distribution(anchor_seq, args, kwargs, st, board)
        if q is None:
            record['preterm_skip_reason'] = 'NO_LEGAL_DISTRIBUTION'
            return anchor_seq

        feature = np.asarray([terminal_close_score(i) for i in range(22)], float)
        q2 = q * np.exp(float(self.PRETERM_CLOSE_LAMBDA) * feature)
        q2[~legal] = 0.0
        if not np.all(np.isfinite(q2)) or q2.sum() <= 0:
            record['preterm_skip_reason'] = 'INVALID_TILTED_DISTRIBUTION'
            return anchor_seq
        q2 /= q2.sum()

        # Maximal coupling q -> q2. This minimizes changes and is exact no-op at lambda=0.
        common = np.minimum(q, q2)
        t0 = int(anchor_seq[-1])
        keep_prob = float(common[t0] / max(q[t0], 1e-300))
        rr, digest = _rng_from_record(int(self.RUN_SEED), str(self.TARGET_BIF), record, self.PRETERM_NAMESPACE)
        u = float(rr.random())
        if u < keep_prob:
            tsel = t0
            changed = False
        else:
            resid = q2 - common
            resid = np.maximum(resid, 0.0)
            if resid.sum() <= 0:
                tsel = t0
                changed = False
            else:
                resid /= resid.sum()
                tsel = int(rr.choice(22, p=resid))
                changed = (tsel != t0)

        selected = tuple(anchor_seq[:-1]) + (tsel,)
        assert selected[:-1] == anchor_seq[:-1]
        assert len(selected) == len(anchor_seq)
        assert int(m.WIDTH[selected[-1]]) == int(m.WIDTH[anchor_seq[-1]])
        assert int(m.stable_width(selected)) == int(m.stable_width(anchor_seq))
        assert int(m.stable_width(selected)) + 2 <= R
        assert legal[tsel]

        record.update(
            preterm_applied=True,
            preterm_changed=bool(changed),
            preterm_anchor=m.word_str(anchor_seq),
            preterm_selected=m.word_str(selected),
            preterm_anchor_terminal=int(t0),
            preterm_selected_terminal=int(tsel),
            preterm_anchor_terminal_name=m.I2G[int(t0)],
            preterm_selected_terminal_name=m.I2G[int(tsel)],
            preterm_anchor_close_score=int(terminal_close_score(t0)),
            preterm_selected_close_score=int(terminal_close_score(tsel)),
            preterm_parent_prob=float(q[t0]),
            preterm_tilted_prob=float(q2[tsel]),
            preterm_keep_prob=float(keep_prob),
            preterm_selection_digest=digest,
            selected=m.word_str(selected),
            direct=False,
            direct_reason='V21_PRETERM_TERMINAL_HOLD_V1',
        )
        st.bump('preterm_events')
        st.bump('preterm_changed', int(changed))
        st.bump('preterm_close_score_delta', int(terminal_close_score(tsel) - terminal_close_score(t0)))
        st.last_proposal.update(
            preterm=True,
            preterm_changed=bool(changed),
            preterm_anchor=m.word_str(anchor_seq),
            preterm_selected=m.word_str(selected),
            preterm_rstart=int(R),
        )
        assert json.dumps(args[5].bit_generator.state, sort_keys=True, default=str) == rng_before
        assert st.semantic_digest() == sem_before
        record['preterm_parent_rng_untouched'] = True
        record['preterm_semantic_state_untouched'] = True
        return selected


class V21PretermR6Sampler(V21PretermTerminalSampler):
    PRETERM_R_MAX = 6
    PRETERM_NAMESPACE = 'V21_PRETERM_TERMINAL_R6_V1'


class V21PretermQMap9Sampler(V21PretermTerminalSampler):
    PRETERM_R_MAX = 9
    PRETERM_NAMESPACE = 'V21_PRETERM_TERMINAL_QMAP9_V1'
