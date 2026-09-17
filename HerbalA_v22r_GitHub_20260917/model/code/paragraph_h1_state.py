from __future__ import annotations

from copy import deepcopy
import numpy as np
from bti2_patch_state import PatchMapState


class ParagraphH1PatchMapState(PatchMapState):
    """PatchMapState plus transactional paragraph H1 running-residual memory.

    Only *completed previous eligible lines* are exposed to the next line.
    The current line is accumulated in a pending buffer and is flushed when the
    generator begins the next physical line of the same paragraph.  Paragraph
    changes reset the memory to neutral.  Because these fields live in the
    motion state, PF branches and packing retries clone them transactionally.
    """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.par_h1_paragraph_key = None
        self.par_h1_line_key = None
        self.par_h1_obs = np.zeros(22, dtype=float)
        self.par_h1_exp = np.zeros(22, dtype=float)
        self.par_h1_n = 0.0
        self.par_h1_pending_obs = np.zeros(22, dtype=float)
        self.par_h1_pending_exp = np.zeros(22, dtype=float)
        self.par_h1_pending_n = 0.0
        self.par_h1_para = None
        self.par_h1_para_line_raw = None
        self.par_h1_raw_para_final = False
        self.par_h1_boundary_type = None

    def __deepcopy__(self, memo):
        z = super().__deepcopy__(memo)
        # super() restores the dynamic subclass but does not know these fields.
        for k in (
            'par_h1_paragraph_key', 'par_h1_line_key', 'par_h1_n',
            'par_h1_pending_n', 'par_h1_para', 'par_h1_para_line_raw',
            'par_h1_raw_para_final', 'par_h1_boundary_type',
        ):
            setattr(z, k, deepcopy(getattr(self, k), memo))
        z.par_h1_obs = np.array(self.par_h1_obs, dtype=float, copy=True)
        z.par_h1_exp = np.array(self.par_h1_exp, dtype=float, copy=True)
        z.par_h1_pending_obs = np.array(self.par_h1_pending_obs, dtype=float, copy=True)
        z.par_h1_pending_exp = np.array(self.par_h1_pending_exp, dtype=float, copy=True)
        return z

    def _reset_paragraph_h1(self):
        self.par_h1_obs[:] = 0.0
        self.par_h1_exp[:] = 0.0
        self.par_h1_n = 0.0
        self.par_h1_pending_obs[:] = 0.0
        self.par_h1_pending_exp[:] = 0.0
        self.par_h1_pending_n = 0.0

    def _flush_pending_line(self):
        if self.par_h1_pending_n > 0:
            self.par_h1_obs += self.par_h1_pending_obs
            self.par_h1_exp += self.par_h1_pending_exp
            self.par_h1_n += float(self.par_h1_pending_n)
        self.par_h1_pending_obs[:] = 0.0
        self.par_h1_pending_exp[:] = 0.0
        self.par_h1_pending_n = 0.0

    def begin(self, sr):
        # Update paragraph/line memory before the parent updates physical keys.
        pkey = (str(sr.page), int(sr.para))
        lkey = (str(sr.page), str(sr.locus))
        if self.par_h1_paragraph_key != pkey:
            self._reset_paragraph_h1()
            self.par_h1_paragraph_key = pkey
            self.par_h1_line_key = lkey
        elif self.par_h1_line_key != lkey:
            # The just-completed line becomes available to this next line.
            self._flush_pending_line()
            self.par_h1_line_key = lkey

        self.par_h1_para = int(sr.para)
        self.par_h1_para_line_raw = int(sr.para_line_raw)
        self.par_h1_raw_para_final = bool(getattr(sr, 'raw_para_final', False))
        self.par_h1_boundary_type = str(getattr(sr, 'boundary_type', ''))
        super().begin(sr)

    def paragraph_h1_ratio(self, lam: float):
        """Continuous shrinkage ratio from completed prior lines only."""
        if self.par_h1_n <= 0 or not np.isfinite(lam) or lam <= 0:
            return np.ones(22, dtype=float)
        n = float(self.par_h1_n)
        m = np.asarray(self.par_h1_exp, float) / n
        obs = np.asarray(self.par_h1_obs, float)
        s = (obs + float(lam) * m) / (n + float(lam))
        ratio = np.ones(22, dtype=float)
        ok = m > 0
        ratio[ok] = s[ok] / m[ok]
        # Numerical guard only; baseline smoothing should keep all entries >0.
        ratio[~np.isfinite(ratio)] = 1.0
        ratio = np.maximum(ratio, 0.0)
        return ratio

    def paragraph_h1_note(self, h1: int, expected):
        p = np.asarray(expected, dtype=float)
        if p.shape != (22,) or not np.all(np.isfinite(p)) or p.sum() <= 0:
            raise AssertionError('Invalid paragraph H1 expected vector')
        p = p / p.sum()
        self.par_h1_pending_obs[int(h1)] += 1.0
        self.par_h1_pending_exp += p
        self.par_h1_pending_n += 1.0

    def semantic_payload(self):
        d = super().semantic_payload()
        d.update(
            par_h1_paragraph_key=self.par_h1_paragraph_key,
            par_h1_line_key=self.par_h1_line_key,
            par_h1_obs=self.par_h1_obs.tolist(),
            par_h1_exp=self.par_h1_exp.tolist(),
            par_h1_n=float(self.par_h1_n),
            par_h1_pending_obs=self.par_h1_pending_obs.tolist(),
            par_h1_pending_exp=self.par_h1_pending_exp.tolist(),
            par_h1_pending_n=float(self.par_h1_pending_n),
        )
        return d

    def digest_payload(self):
        d = super().digest_payload()
        d.update(
            par_h1_paragraph_key=self.par_h1_paragraph_key,
            par_h1_line_key=self.par_h1_line_key,
            par_h1_obs=self.par_h1_obs.tolist(),
            par_h1_exp=self.par_h1_exp.tolist(),
            par_h1_n=float(self.par_h1_n),
            par_h1_pending_obs=self.par_h1_pending_obs.tolist(),
            par_h1_pending_exp=self.par_h1_pending_exp.tolist(),
            par_h1_pending_n=float(self.par_h1_pending_n),
        )
        return d
