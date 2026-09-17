from __future__ import annotations

import hashlib
import json
import math
from pathlib import Path
import numpy as np

import v19r_rb3_pw2_close1 as m
from route_map_model import subseqs
from short_body_h2_sampler import (
    V21PretermShortBodyH2GlobalSampler,
    _external_only_h2_gain,
)


class ParagraphH1Baseline:
    def __init__(self, path: Path):
        obj = json.loads(Path(path).read_text(encoding='utf-8'))
        self.metadata = obj['metadata']
        self.by_bif = obj['by_bif']
        self.glyphs = tuple(self.metadata['glyphs'])
        if len(self.glyphs) != 22:
            raise ValueError('Expected stable-22 baseline')

    def probability(self, bif: str, length: int, boundary: str, prev_terminal: int):
        b = self.by_bif[str(bif)]
        key = f'{int(length)}|{str(boundary)}|{int(prev_terminal)}'
        row = b['table'].get(key)
        if row is None:
            # Runtime words are capped at 12; clip only as a safety fallback.
            L = min(12, max(2, int(length)))
            if int(prev_terminal) >= 0:
                key = f'{L}|SPACE|{int(prev_terminal)}'
            else:
                key = f'{L}|{str(boundary)}|-1'
            row = b['table'].get(key)
        if row is None:
            raise KeyError((bif, length, boundary, prev_terminal))
        p = np.asarray(row, dtype=float)
        p = np.maximum(p, 0.0)
        p /= p.sum()
        return p


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


class V21ParagraphH1RunningSampler(V21PretermShortBodyH2GlobalSampler):
    """Current parent plus causal paragraph-local continuous H1 running residual.

    Validated state parameterization:
      * all BODY words with exact stable glyph length >=2
      * paragraph line >=2
      * paragraph-final line excluded
      * segment-final word excluded
      * only completed prior eligible lines update the state
      * no decay; shrinkage lambda = 32
      * paragraph change resets to neutral

    The intervention is deliberately H1-only. H2+, exact length and physical
    width are frozen. A request-local side RNG leaves the parent RNG untouched.
    """

    PARAGRAPH_H1_ENABLED = True
    PARAGRAPH_H1_LAMBDA = 32.0
    PARAGRAPH_H1_NAMESPACE = 'V21_PARAGRAPH_H1_RUNNING_V1'
    H1_BASELINE = None

    @classmethod
    def configure_baseline(cls, path):
        cls.H1_BASELINE = ParagraphH1Baseline(Path(path))

    def _boundary_key(self, st, record):
        t = record.get('prev_terminal')
        if t is not None:
            return 'SPACE', int(t)
        if int(record.get('segment_id', st.segment_id)) > 0:
            return 'PLANT', -1
        return 'UNKNOWN_GAP', -1

    def _eligible_request(self, st, role: str, board: str, end: bool, seq):
        return bool(
            self.PARAGRAPH_H1_ENABLED
            and role == 'BODY'
            and str(board) == 'BODY'
            and not bool(end)
            and len(seq) >= 2
            and int(getattr(st, 'par_h1_para_line_raw', 0) or 0) >= 2
            and not bool(getattr(st, 'par_h1_raw_para_final', False))
        )

    def _validated_baseline(self, st, record, seq):
        if self.H1_BASELINE is None:
            raise RuntimeError('Paragraph H1 baseline is not configured')
        boundary, t = self._boundary_key(st, record)
        return self.H1_BASELINE.probability(
            str(self.TARGET_BIF), int(len(seq)), boundary, int(t)
        ), boundary, int(t)

    def _h1_conditional_distributions(self, anchor_seq, args, kwargs, st, board, ratio):
        role = str(args[2])
        lp = int(args[4])
        R = int(args[6])
        end = bool(args[10])
        line_end = bool(kwargs.get('line_end_boundary', False))
        L = len(anchor_seq)
        if L < 2:
            return None

        tab = self.base.tables
        patch = self.base.patch
        physical_head = bool(st.word_index == 0 and st.segment_id == 0)
        p1_base = np.asarray(tab.base_nonend(role, lp, end, line_end, 0, m.START, m.START), float)
        g1 = np.ones(22, dtype=float)
        if patch.eta_entry and st.prev_terminal is not None and not physical_head and role != 'HEAD':
            g1 = np.exp(float(patch.eta_entry) * np.asarray(tab.bridge[st.row_phase, board][st.prev_terminal], float))
        g2_parent, g3 = tab.gains(role, lp, end, line_end, str(st.row_phase), str(board), physical_head, patch)

        h1_anchor = int(anchor_seq[0])
        h2 = int(anchor_seq[1])
        h1_width = int(m.WIDTH[h1_anchor])
        parent_log = np.full(22, -np.inf, dtype=float)
        target_log = np.full(22, -np.inf, dtype=float)
        legal = np.zeros(22, dtype=bool)
        excluded_end = end and line_end if st.patch.boundary_policy == 'B_ALIGN' else end

        for h1 in range(22):
            if int(m.WIDTH[h1]) != h1_width:
                continue
            if p1_base[h1] <= 0 or g1[h1] <= 0:
                continue

            cand = list(anchor_seq)
            cand[0] = int(h1)
            cand = tuple(cand)
            if int(m.stable_width(cand)) != int(m.stable_width(anchor_seq)):
                continue
            if int(m.stable_width(cand)) + 2 > R:
                continue

            lpv = math.log(max(float(p1_base[h1] * g1[h1]), 1e-300))

            p2_base = np.asarray(tab.base_nonend(role, lp, end, line_end, 1, m.START, h1), float)
            if 2 <= L <= 4:
                key = (str(st.row_phase), str(board), 1, m.START, h1)
                g2_row = _external_only_h2_gain(tab, key, p2_base, float(patch.eta_h2))
            else:
                g2_row = np.asarray(g2_parent[h1], float)
            if p2_base[h2] <= 0 or g2_row[h2] <= 0:
                continue
            lpv += math.log(max(float(p2_base[h2] * g2_row[h2]), 1e-300))

            if L >= 3:
                h3 = int(anchor_seq[2])
                p3 = np.asarray(tab.base_nonend(role, lp, end, line_end, 2, h1, h2), float)
                p3 = p3 * np.asarray(g3[h1, h2], float)
                if p3[h3] <= 0:
                    continue
                lpv += math.log(max(float(p3[h3]), 1e-300))

            if L >= 4:
                h3 = int(anchor_seq[2]); h4 = int(anchor_seq[3])
                p4 = np.asarray(tab.base_nonend(role, lp, end, line_end, 3, h2, h3), float)
                if p4[h4] <= 0:
                    continue
                z = math.log(max(float(p4[h4]), 1e-300))
                if args[1][h1, h2, h3, h4] == 0:
                    z += math.log(0.80)
                lpv += z

            # Preserve the current parent's route/bT selection pressures.
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

            legal[h1] = True
            parent_log[h1] = lpv + float(sc)
            if ratio[h1] > 0:
                target_log[h1] = lpv + float(sc) + math.log(max(float(ratio[h1]), 1e-300))

        if not legal[h1_anchor] or not np.isfinite(target_log[legal]).any():
            return None

        def norm(logv):
            q = np.zeros(22, dtype=float)
            good = legal & np.isfinite(logv)
            z = logv[good].copy()
            z -= np.max(z)
            q[good] = np.exp(z)
            q /= q.sum()
            return q

        return norm(parent_log), norm(target_log), legal

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
                paragraph_h1_applied=False,
                paragraph_h1_changed=False,
                paragraph_h1_lambda=float(self.PARAGRAPH_H1_LAMBDA),
                paragraph_h1_scope='BODY_LEN2PLUS_NONFINALPARA_NONSEGEND_PRIOR_LINES_ONLY',
                paragraph_h1_state_n=float(getattr(st, 'par_h1_n', 0.0)),
            )

        if record is None or not self._eligible_request(st, role, board, end, anchor_seq):
            return anchor_seq

        baseline, boundary, t = self._validated_baseline(st, record, anchor_seq)
        record['paragraph_h1_expected'] = baseline.tolist()
        record['paragraph_h1_boundary'] = boundary
        record['paragraph_h1_prev_terminal_key'] = int(t)
        record['paragraph_h1_commit_eligible'] = True

        # The first eligible line after reset has no completed prior-line state.
        if float(getattr(st, 'par_h1_n', 0.0)) <= 0 or not self.PARAGRAPH_H1_ENABLED:
            record['paragraph_h1_skip_reason'] = 'NO_PRIOR_ELIGIBLE_LINE_STATE'
            return anchor_seq

        ratio = st.paragraph_h1_ratio(float(self.PARAGRAPH_H1_LAMBDA))
        rng_before = json.dumps(args[5].bit_generator.state, sort_keys=True, default=str)
        sem_before = st.semantic_digest()
        out = self._h1_conditional_distributions(anchor_seq, args, kwargs, st, board, ratio)
        if out is None:
            record['paragraph_h1_skip_reason'] = 'NO_LEGAL_H1_CONDITIONAL'
            return anchor_seq
        q_parent, q_target, legal = out

        h1_0 = int(anchor_seq[0])
        common = np.minimum(q_parent, q_target)
        keep_prob = float(common[h1_0] / max(q_parent[h1_0], 1e-300))
        rr, digest = _side_rng(int(self.RUN_SEED), str(self.TARGET_BIF), record, self.PARAGRAPH_H1_NAMESPACE)
        if float(rr.random()) < keep_prob:
            h1_sel = h1_0
            changed = False
        else:
            resid = np.maximum(q_target - common, 0.0)
            if resid.sum() <= 0:
                h1_sel = h1_0
                changed = False
            else:
                resid /= resid.sum()
                h1_sel = int(rr.choice(22, p=resid))
                changed = (h1_sel != h1_0)

        selected = list(anchor_seq)
        selected[0] = int(h1_sel)
        selected = tuple(selected)
        assert selected[1:] == anchor_seq[1:]
        assert len(selected) == len(anchor_seq)
        assert int(m.WIDTH[selected[0]]) == int(m.WIDTH[anchor_seq[0]])
        assert int(m.stable_width(selected)) == int(m.stable_width(anchor_seq))
        assert int(m.stable_width(selected)) + 2 <= R
        assert legal[h1_sel]

        record.update(
            paragraph_h1_applied=True,
            paragraph_h1_changed=bool(changed),
            paragraph_h1_anchor=m.word_str(anchor_seq),
            paragraph_h1_anchor_seq=[int(x) for x in anchor_seq],
            paragraph_h1_selected=m.word_str(selected),
            paragraph_h1_anchor_h1=int(h1_0),
            paragraph_h1_selected_h1=int(h1_sel),
            paragraph_h1_anchor_h1_name=m.I2G[int(h1_0)],
            paragraph_h1_selected_h1_name=m.I2G[int(h1_sel)],
            paragraph_h1_parent_prob=float(q_parent[h1_0]),
            paragraph_h1_target_prob=float(q_target[h1_sel]),
            paragraph_h1_keep_prob=float(keep_prob),
            paragraph_h1_ratio=ratio.tolist(),
            paragraph_h1_selection_digest=digest,
            paragraph_h1_staged_postcommit=True,
        )
        st.bump('paragraph_h1_events')
        st.bump('paragraph_h1_changed', int(changed))
        # Do not expose the H1 write to packing, rare-glyph logic, route memory,
        # or the parent RNG.  The selected H1 is materialized only after the
        # exact parent word has committed.
        assert json.dumps(args[5].bit_generator.state, sort_keys=True, default=str) == rng_before
        assert st.semantic_digest() == sem_before
        record['paragraph_h1_parent_rng_untouched'] = True
        record['paragraph_h1_semantic_state_untouched'] = True
        return anchor_seq

    def commit_surface(self, rseq, stable_seq, role, sr, row):
        st = self.state
        record = self.last_request
        # Exact parent commit first.  commit_word has already committed the parent
        # anchor to route memory, and rare/packing logic has already run on it.
        super().commit_surface(rseq, stable_seq, role, sr, row)

        actual_stable = tuple(stable_seq)
        actual_surface = tuple(rseq)
        if record is not None and bool(record.get('paragraph_h1_changed', False)):
            h1_sel = int(record['paragraph_h1_selected_h1'])
            z = list(actual_stable)
            z[0] = h1_sel
            actual_stable = tuple(z)
            zr = list(actual_surface)
            first_stable = next((i for i,x in enumerate(zr) if isinstance(x,(int,np.integer))), None)
            if first_stable is None:
                raise AssertionError('No stable glyph in rare surface for paragraph H1 write')
            if int(m.WIDTH[int(zr[first_stable])]) != int(m.WIDTH[h1_sel]):
                raise AssertionError('Paragraph H1 postcommit width mismatch')
            zr[first_stable] = h1_sel
            actual_surface = tuple(zr)
            row['stable_surface'] = m.word_str(actual_stable)
            row['surface'] = m.word_str(actual_surface)
            # The last surface commit is this accepted BODY word.
            st.surface_commits[-1]['stable_surface'] = row['stable_surface']
            st.surface_commits[-1]['surface'] = row['surface']
            record['final_surface'] = row['surface']
            record['paragraph_h1_postcommit_written'] = True
            record['paragraph_h1_route_state_frozen'] = True

        if record is None or not bool(record.get('paragraph_h1_commit_eligible', False)):
            return
        if role != 'BODY' or int(row.get('stable_glyph_len', 0)) < 2:
            return
        if int(row.get('draw_segment_end', 0)) != 0:
            return
        if int(getattr(st, 'par_h1_para_line_raw', 0) or 0) < 2 or bool(getattr(st, 'par_h1_raw_para_final', False)):
            return
        expected = record.get('paragraph_h1_expected')
        if expected is None or not actual_stable:
            return
        st.paragraph_h1_note(int(actual_stable[0]), expected)
        record['paragraph_h1_committed_to_pending_line'] = True
        record['paragraph_h1_pending_line_n_after'] = float(st.par_h1_pending_n)


class V21ParagraphH1NoOpSampler(V21ParagraphH1RunningSampler):
    """No-op audit arm: identical parent output, paragraph state still audited."""
    PARAGRAPH_H1_ENABLED = False
    PARAGRAPH_H1_NAMESPACE = 'V21_PARAGRAPH_H1_NOOP_V1'
