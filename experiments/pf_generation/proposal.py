"""Supported raw-word rejection sampling, before Map selection and rare work."""
from __future__ import annotations

from . import POLICY
from .common import band, length_band, digest, require


class Trace:
    """Shared observations only; context and rows never choose a word or RNG."""
    def __init__(self):
        self.context = {}
        self.gates = []
        self.proposals = []


def sampler_class(parent_class, m):
    class PFEndProposalSampler(parent_class):
        def __init__(self, base, tables, patch, law, trace):
            super().__init__(base, tables, patch)
            self.pf_law, self.pf_trace = law, trace

        def __call__(self, *args, **kwargs):
            st = self.state
            end = bool(args[10])
            line_end = bool(kwargs.get('line_end_boundary', args[14] if len(args) > 14 else False))
            if st is None or int(args[3]) < 2 or st.row_phase != 'FINAL' or not end or not line_end:
                return super().__call__(*args, **kwargs)
            trace, law, rng = self.pf_trace, self.pf_law, args[5]
            semantic = st.semantic_digest()
            rng_before = digest(rng.bit_generator.state)
            draws, anchor = [], None
            fallback, chosen = False, None
            for index in range(POLICY['max_raw_draws']):
                seq = tuple(super().__call__(*args, **kwargs))
                if anchor is None:
                    anchor = seq
                width = int(m.stable_width(seq))
                gain = law.gains[length_band(len(seq))][band(width)] if seq else None
                u = None if not seq or law.identity else float(rng.random())
                accepted = not seq or law.identity or u < gain / law.normalizer
                draws.append(dict(glyphs=list(seq), stable_surface=m.word_str(seq), length=len(seq), width=width, gain=gain,
                                  uniform=u, accepted=bool(accepted)))
                if accepted:
                    chosen = index
                    result = seq
                    break
            else:
                fallback, chosen, result = True, 0, anchor
            require(semantic == st.semantic_digest(), 'Raw PF sampler changed semantic state')
            trace.proposals.append(dict(trace.context, role=str(args[2]), paragraph_line=int(args[3]),
                                        row_phase=str(st.row_phase), end=end, line_end_boundary=line_end,
                                        word_index=int(st.word_index), rstart=int(args[6]),
                                        identity=law.identity, law_sha256=digest(law), draws=draws,
                                        chosen_draw=chosen, fallback=fallback,
                                        selected_glyphs=list(result), state_unchanged=True,
                                        rng_entry_sha256=rng_before, rng_exit_sha256=digest(rng.bit_generator.state)))
            return result
    return PFEndProposalSampler
