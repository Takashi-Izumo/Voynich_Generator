from __future__ import annotations

from collections import Counter, defaultdict
from dataclasses import dataclass, field
from itertools import combinations

from .schema import Event, RARE, WIDTH, events


@dataclass
class Feature:
    counts: Counter = field(default_factory=Counter)
    conditional: bool = False


def near(a: tuple, b: tuple) -> bool:
    """One glyph substitution, insertion or deletion (not transposition)."""
    if abs(len(a)-len(b)) > 1:
        return False
    if len(a) == len(b):
        return sum(x != y for x, y in zip(a, b)) <= 1
    if len(a) > len(b):
        a, b = b, a
    i = next((i for i, (x, y) in enumerate(zip(a, b)) if x != y), len(a))
    return a[i:] == b[i+1:]


def route_features(es: list[Event], refsets: list[set]) -> dict[str, Feature]:
    """Use exactly two reference pages for every sharing/persistence view.

    Candidates average the three two-page subsets; a reference's LOO view
    has one pair. Normalize each nonempty subset channel before mixing so
    persistence is not implicitly weighted by its number of route hits.
    """
    subsets = []
    for pair in combinations(refsets, 2):
        vocab = set().union(*pair)
        grams = {n: {g[i:i+n] for g in vocab for i in range(len(g)-n+1)} for n in range(3, 7)}
        routes = grams[5] | grams[6]
        channels = defaultdict(Counter)
        state = None
        for e in es:
            if not e.g:
                continue
            g = e.g
            matching = set()
            for n in range(3, 7):
                for i in range(len(g)-n+1):
                    sub = g[i:i+n]
                    channels[f'J17/share{n}'][(i == 0, sub in grams[n])] += 1
                    if sub in routes:
                        matching.add(sub)
            if matching:
                channels['J17/visible_persistence']['same' if state in matching else 'switch' if state else 'start'] += 1
                # A distinct state per reference pair; PLANT does not reset it.
                state = state if state in matching else min(matching)
        subsets.append(channels)
    out = {}
    for name in sorted({name for subset in subsets for name in subset}):
        nonempty = [s[name] for s in subsets if s[name]]
        counts = Counter()
        for c in nonempty:
            total = sum(c.values())
            for key, value in c.items():
                counts[key] += value/total/len(nonempty)
        out[name] = Feature(counts)
    return out


def extract(doc: dict, reference: list[dict], profile: str) -> dict[str, Feature]:
    out: dict[str, Feature] = {}

    def add(name, value, weight=1.0):
        out.setdefault(name, Feature()).counts[value] += weight

    def cond(name, context, value):
        out.setdefault(name, Feature(conditional=True)).counts[(context, value)] += 1

    def bundle(name: str, e: Event):
        g = e.g
        add(name+'/word', g)
        add(name+'/length_width', (len(g), sum(WIDTH[c] for c in g)))
        add(name+'/head', g[:2])
        add(name+'/terminal', g[-1])
        for n in (2, 3):
            for i in range(len(g)-n+1):
                add(name+f'/ng{n}', g[i:i+n])

    es = events(doc)
    valid = [e for e in es if e.g]
    refsets = [{e.g for e in events(r) if e.g} for r in reference]
    out.update(route_features(es, refsets))
    reference_pairs = list(combinations(refsets, 2))
    capacity_by_seg = {}
    for e in es:
        key = (e.line, e.segment)
        if key not in capacity_by_seg:
            sg = [x for x in es if (x.line, x.segment) == key]
            capacity_by_seg[key] = None if any(not x.g for x in sg) else sum(sum(WIDTH[c] for c in x.g) for x in sg) + len(sg)-1
    previous_head = None
    history = Counter()
    pending = Counter()
    last_line = None
    last_para = None
    last_word = {}
    for e in es:
        if e.para != last_para:
            history.clear()
            pending.clear()
            previous_head = None
        elif e.line != last_line:
            history.update(pending)
            pending.clear()
        last_line, last_para = e.line, e.para
        if not e.g:
            continue
        g = e.g
        bundle('ATOM:'+e.atom, e)
        for name, selected in (
            ('J01', e.first and e.ordinal == 0), ('J02', e.first),
            ('J03', not e.first and e.ordinal == 0),
            ('J04', not e.first and e.ordinal == 1), ('J05', e.ordinal >= 2),
            ('J06', e.boundary == 'L'), ('J07', e.final),
        ):
            if selected:
                bundle(name, e)
        if e.first and e.boundary == 'L':
            # Broad observable FIRST-LF; this is NOT the generator's strict ledger.
            add('J08/'+('short' if len(g) <= 3 else 'long'), g[-1])
        if e.role == 'HEAD':
            if len(g) >= 2:
                cond('J09/H2', (g[0],), g[1])
            if len(g) >= 3:
                cond('J09/H3', g[:2], g[2])
        if e.ordinal == 0:
            if previous_head and previous_head[0] == e.line-1 and previous_head[1] == e.para:
                cond('J10/vertical', (min(e.pline, 5), previous_head[2]), g[0])
            previous_head = (e.line, e.para, g[0])
        if e.role == 'W2' and e.boundary == 'I' and not e.first and not e.final and 3 <= len(g) <= 5:
            cond(f'J11/L{len(g)}', (g[0],), g[1])
        if e.role == 'BODY' and e.boundary == 'I':
            if 2 <= len(g) <= 4:
                cond('J12/H2', (len(g), g[0]), g[1])
            if len(g) >= 2 and not e.first and not e.final:
                if history:
                    dom = min(history, key=lambda c: (-history[c], c))
                    cond('J13/visible_history', (dom,), g[0])
                pending[g[0]] += 1
            if len(g) >= 2 and e.remaining is not None:
                seg = doc['lines'][e.line]['segments'][e.segment]
                capacity = capacity_by_seg[(e.line, e.segment)]
                if capacity is not None and capacity > 0:
                    band = min(4, int(5*e.remaining/capacity))
                    family = 'NMY' if g[-1] in ('n', 'm', 'y') else 'LR' if g[-1] in ('l', 'r') else 'OTHER'
                    cond('J14/relative_remaining', (seg['end'], band), family)
        if e.prev:
            # Assign each transition to its destination atom once. Diagnostic
            # J15/J25 are NOT added again as votes in the final aggregate.
            cond('ATOM:'+e.atom+'/space_T_H1', (e.prev[-1],), g[0])
            add('ATOM:'+e.atom+'/word_pair', (e.prev, g))
            add('ATOM:'+e.atom+'/length_pair', (len(e.prev), len(g)))
            cond('J15/T_H1', (e.prev[-1],), g[0])
            if len(e.prev) >= 2:
                cond('J15/bT_H1', e.prev[-2:], g[0])
        if len(g) >= 2:
            add('J16/'+e.boundary, g[-2:])
        for d in range(len(g)+1):
            add('J18/depth', (min(d, 9), g[d-2] if d >= 2 else 'START', g[d-1] if d else 'START', g[d] if d < len(g) else 'END'))
        add('J18/length_width_joint', (len(g), sum(WIDTH[c] for c in g)))
        # Compare to two reference pages in both candidates and reference LOO views.
        for subset in reference_pairs:
            v = set().union(*subset)
            relation = 'exact' if g in v else 'near' if any(near(g, w) for w in v) else 'novel'
            add('J19/relation_to_two', relation, 1/len(reference_pairs))
        if g in last_word:
            add('J20/repeat_distance', min(10, e.line-last_word[g]))
        last_word[g] = e.line
        if e.boundary == 'P':
            bundle('J22/plant_end', e)
        if e.segment > 0 and e.position == 0:
            bundle('J22/restart', e)
        bundle('J23/global', e)
        for n in (4, 5, 6):
            for i in range(len(g)-n+1):
                add(f'J23/ng{n}', g[i:i+n])
        if e.prev:
            add('J25/word_pair', (e.prev, g))
            add('J25/length_pair', (len(e.prev), len(g)))

    counts = Counter(e.g for e in valid)
    n = len(valid)
    if n:
        for label, value in (
            ('types', len(counts)), ('hapax', sum(v == 1 for v in counts.values())),
            ('F2', sum(v == 2 for v in counts.values())),
            ('F3_5', sum(3 <= v <= 5 for v in counts.values())),
            ('F6_10', sum(6 <= v <= 10 for v in counts.values())),
            ('F11+', sum(v >= 11 for v in counts.values())),
        ):
            add('J20/frequency', (label, round(20*value/n)))
    if profile == 'raw':
        for e in es:
            if e.text is not None:
                rare = [c for c in e.text if c in RARE]
                add('J21/rare_presence', bool(rare))
                for c in rare:
                    add('J21/rare_kind', (e.boundary, c))
    return out
