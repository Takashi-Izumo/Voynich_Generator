"""Supported raw-word rejection sampling, before Map selection and rare work."""
from __future__ import annotations

from . import POLICY, TRACE_SCHEMA
from .common import band, length_band, digest, require


class Trace:
    """Shared observations only; context and rows never choose a word or RNG."""
    def __init__(self):
        self.context = {}
        self.gates = []
        self.proposals = []
        self.next_gate_id = 0
        self.next_raw_id = 0
        self.current_gate_id = None
        self.current_request = None
        self.windows = {}
        self.window_start = (0, 0)

    def finish_context(self):
        if self.context.get('generator_pf'):
            key = self.context['event'], self.context['candidate']
            require(key not in self.windows, 'Duplicate PF candidate trace window')
            self.windows[key] = dict(gate_start=self.window_start[0], gate_stop=self.next_gate_id,
                                     raw_start=self.window_start[1], raw_stop=self.next_raw_id)
        self.context = {}
        self.current_gate_id = self.current_request = None

    def set_context(self, context):
        self.finish_context()
        self.context = dict(context)
        self.window_start = self.next_gate_id, self.next_raw_id

    def register_gate(self, row):
        require(self.context.get('generator_pf'), 'Gate query outside PF context')
        self.current_gate_id = self.next_gate_id
        self.next_gate_id += 1
        self.current_request = None
        row.update(query_id=self.current_gate_id, trace_schema=TRACE_SCHEMA)
        self.gates.append(row)

    def bind_request(self, request):
        if not self.context.get('generator_pf'):
            self.current_request = None
            return
        require(self.current_gate_id is not None, 'PF request without a gate query')
        request['pfgen'] = dict(trace_schema=TRACE_SCHEMA, gate_query_id=self.current_gate_id,
                               event=self.context['event'], candidate=self.context['candidate'], raw_calls=[])
        self.current_request = request

    def begin_raw(self):
        request = self.current_request
        require(request is not None and request['pfgen']['gate_query_id'] == self.current_gate_id,
                'Raw PF call without its request/gate')
        call_id = self.next_raw_id
        self.next_raw_id += 1
        return call_id, request


def request_sampler_class(parent_class, trace):
    """Annotate the original request channel; no new instance state or RNG."""
    class PFRequestSampler(parent_class):
        def _start_request(self, st, args, kwargs):
            record = super()._start_request(st, args, kwargs)
            trace.bind_request(record)
            return record
    return PFRequestSampler


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
            call_id, request = trace.begin_raw()
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
            record = dict(trace.context, trace_schema=TRACE_SCHEMA, call_id=call_id,
                                        request_id=request['proposal_id'], gate_query_id=trace.current_gate_id,
                                        role=str(args[2]), paragraph_line=int(args[3]),
                                        row_phase=str(st.row_phase), end=end, line_end_boundary=line_end,
                                        word_index=int(st.word_index), rstart=int(args[6]),
                                        identity=law.identity, law_sha256=digest(law), draws=draws,
                                        chosen_draw=chosen, fallback=fallback,
                                        selected_glyphs=list(result), state_unchanged=True,
                                        rng_entry_sha256=rng_before, rng_exit_sha256=digest(rng.bit_generator.state))
            trace.proposals.append(record)
            request['pfgen']['raw_calls'].append(dict(call_id=call_id, draws=len(draws), row_sha256=digest(record)))
            return result
    return PFEndProposalSampler
