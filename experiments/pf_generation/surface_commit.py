"""Materialize an already-selected terminal edit before semantic surface commit.

The frozen parent still commits its anchor to route memory and performs m/rare
and packing first. Only a post-m H1/H2 which has become the actual last glyph
needs this boundary adapter. All other paths delegate literally to the parent.
"""
from __future__ import annotations

import numpy as np

from judges.schema import RARE, glyphs
from .common import require


def staged_terminal(record, role, visible):
    if record is None:
        return None
    if role == 'W2' and record.get('b2_h2_changed'):
        writer, rank, field = 'W2_H2', 1, 'b2_h2_selected_h2'
    elif role == 'BODY' and record.get('paragraph_h1_changed'):
        writer, rank, field = 'BODY_H1', 0, 'paragraph_h1_selected_h1'
    else:
        return None
    if len(visible) != rank + 1:
        return None
    selected = record[field]
    require(type(selected) is int and 0 <= selected < 22, 'Invalid staged terminal glyph')
    return (writer, rank, selected) if visible[-1] != selected else None


def sampler_class(parent, m):
    class SurfaceCommitSampler(parent):
        def commit_surface(self, rseq, stable_seq, role, sr, row):
            positions = [i for i,g in enumerate(rseq) if isinstance(g,(int,np.integer)) and 0 <= int(g) < 22]
            visible = tuple(int(rseq[i]) for i in positions)
            edit = staged_terminal(self.last_request, role, visible)
            # A rare suffix is the physical terminal; the stable H1/H2 is not.
            if edit is None or positions[-1] != len(rseq)-1:
                return super().commit_surface(rseq,stable_seq,role,sr,row)
            writer, rank, selected = edit
            pos = positions[rank]
            require(int(m.WIDTH[int(rseq[pos])]) == int(m.WIDTH[selected]), 'Terminal edit changed physical width')
            final = list(rseq)
            final[pos] = selected
            record, state = self.last_request, self.state
            route_before = state.current
            row['surface'] = m.word_str(tuple(final))
            # Keep stable_seq and request.selected as the original anchor. The
            # native H1/H2 methods still write their stable child and pending H1
            # statistics. Their visible write becomes idempotent. No second draw.
            result = super().commit_surface(tuple(final),stable_seq,role,sr,row)
            require(state.current == route_before, 'Terminal surface edit changed anchor route')
            require(state.prev_terminal == selected and state.surface_commits[-1]['prev_terminal_after'] == selected
                    and record['commit_terminal_name'] == m.I2G[selected], 'Final visible terminal was not committed')
            record['pfgen_terminal_precommit'] = dict(schema_version=1,writer=writer,rank=rank,
                previous_terminal=int(rseq[pos]),selected_terminal=selected,physical_position=pos,
                before_semantic_surface_commit=True,anchor_route_preserved=True)
            return result
    return SurfaceCommitSampler


def audit_requests(requests, commits, arm):
    """Require repair receipts from post-m anchors, including discarded attempts."""
    count = 0
    byid = {c['proposal_id']:c for c in commits}
    from judges.schema import GLYPHS
    byrequest = {r['proposal_id']:r for r in requests}
    last_key, previous = None, None
    for commit in commits:
        key = commit['page'],commit['locus'],commit['segment_id']
        if key != last_key:
            previous = None
        require(type(commit['prev_terminal_before']) is type(previous)
                and commit['prev_terminal_before']==previous,'Surface terminal chain crossed segment or disagrees')
        request=byrequest[commit['proposal_id']]
        require(type(request['prev_terminal']) is type(previous) and request['prev_terminal']==previous,
                'Next request did not observe the committed visible terminal')
        surface=commit['surface']
        names=glyphs(surface)
        require(bool(names),'Invalid committed visible surface')
        actual=None if surface[-1] in RARE else GLYPHS.index(names[-1])
        require(type(commit['prev_terminal_after']) is type(actual) and commit['prev_terminal_after']==actual,
                'Semantic terminal differs from actual committed surface')
        previous,last_key=actual,key
    for request in requests:
        raw = request.get('after_rare','')
        names = glyphs(raw) if raw else None
        visible = tuple(GLYPHS.index(g) for g in names) if names else ()
        edit = staged_terminal(request,request['role'],visible) if request.get('outcome') == 'LOCAL_COMMIT' else None
        expected = arm != 'BASE' and edit is not None and raw[-1:] not in RARE
        receipt = request.get('pfgen_terminal_precommit')
        require((receipt is not None) == expected, 'Missing/out-of-scope terminal precommit receipt')
        if not expected:
            continue
        writer,rank,selected = edit
        require(type(receipt.get('schema_version')) is int and receipt['schema_version']==1
                and receipt['writer']==writer and type(receipt['rank']) is int and receipt['rank']==rank
                and type(receipt['previous_terminal']) is int and receipt['previous_terminal']==visible[-1]
                and type(receipt['selected_terminal']) is int and receipt['selected_terminal']==selected
                and type(receipt['physical_position']) is int
                and receipt['physical_position']==rank+sum(c in RARE for c in raw)
                and receipt['before_semantic_surface_commit'] is True and receipt['anchor_route_preserved'] is True,
                'Terminal precommit receipt differs from staged edit')
        require(request['commit_terminal_name']==GLYPHS[selected]
                and glyphs(request['final_surface'])[-1]==GLYPHS[selected], 'Terminal edit/request mismatch')
        if request['proposal_id'] in byid:
            c=byid[request['proposal_id']]
            require(c['surface']==request['final_surface'] and c['prev_terminal_after']==selected,
                    'Terminal edit/final state commit mismatch')
        count += 1
    return count
