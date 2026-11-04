from __future__ import annotations

from collections import Counter, defaultdict
import hashlib
import json
import math

from .features import Feature, extract
from .registry import ATOMS, CONFIG, NAMES
from .schema import validate_case


def digest(obj) -> str:
    return hashlib.sha256(json.dumps(obj, ensure_ascii=False, sort_keys=True, separators=(',', ':'), allow_nan=False).encode()).hexdigest()


CONFIG_HASH = digest(CONFIG)


def normalize(c: Counter) -> dict:
    total = sum(c.values())
    return {k: v/total for k, v in c.items()} if total else {}


def reference_mix(cs: list[Counter]) -> Counter:
    nonempty = [normalize(c) for c in cs if c]
    result = Counter()
    for c in nonempty:
        for k, v in c.items():
            result[k] += v/len(nonempty)
    return result


def jsd(a: Counter, b: Counter) -> float:
    if not a or not b:
        raise ValueError('JSD requires two nonempty distributions')
    p, q = normalize(a), normalize(b)
    result = 0.0
    for k in p.keys() | q.keys():
        x, y = p.get(k, 0.0), q.get(k, 0.0)
        m = (x+y)/2
        if x:
            result += 0.5*x*math.log2(x/m)
        if y:
            result += 0.5*y*math.log2(y/m)
    return max(0.0, result)


def compare(ref: list[Feature], a: Feature, b: Feature) -> dict:
    coverage = {'reference_events': sum(sum(f.counts.values()) for f in ref), 'A_events': sum(a.counts.values()), 'B_events': sum(b.counts.values())}
    if not any(f.counts for f in ref) or not a.counts or not b.counts:
        return dict(coverage, A=None, B=None, delta=None, status='NA_EMPTY')
    if a.conditional:
        def split(c):
            result = defaultdict(Counter)
            for (ctx, outcome), value in c.items():
                result[ctx][outcome] += value
            return result
        # Mix the per-document JOINT distributions first, then condition.
        # Averaging normalized context rows would overweight rare contexts.
        rr = split(reference_mix([f.counts for f in ref]))
        aa, bb = split(a.counts), split(b.counts)
        masses = Counter({ctx: sum(row.values()) for ctx, row in rr.items()})
        common = set(masses) & aa.keys() & bb.keys()
        mass = sum(masses[k] for k in common)
        coverage.update(contexts=len(common), reference_context_coverage=mass/sum(masses.values()))
        if not mass:
            return dict(coverage, A=None, B=None, delta=None, status='NA_CONTEXT')
        sa = sb = 0.0
        for ctx in common:
            q = rr[ctx]
            w = masses[ctx]/mass
            sa -= w*jsd(q, aa[ctx])
            sb -= w*jsd(q, bb[ctx])
    else:
        q = reference_mix([f.counts for f in ref])
        sa, sb = -jsd(q, a.counts), -jsd(q, b.counts)
    return dict(coverage, A=sa, B=sb, delta=sa-sb, status='OK')


def aggregate(deltas: list[float | None]) -> float | None:
    values = [x for x in deltas if x is not None]
    return sum(values)/len(values) if values else None


def validate_config(config: dict) -> None:
    def finite_number(value):
        if type(value) not in (int, float):
            return False
        try:
            return math.isfinite(value)
        except OverflowError:
            return False

    atoms = config.get('primary_atoms')
    if not isinstance(atoms, list) or not atoms or any(not isinstance(a, str) or a not in ATOMS for a in atoms) or len(set(atoms)) != len(atoms):
        raise ValueError('primary_atoms must be a nonempty unique subset of ATOMS')
    weights = config.get('atom_weights')
    if not isinstance(weights, dict) or set(weights) != set(atoms):
        raise ValueError('atom_weights must match primary_atoms exactly')
    if any(not finite_number(w) or w < 0 for w in weights.values()):
        raise ValueError('atom weights must be finite and nonnegative')
    total = sum(weights.values())
    if not math.isfinite(total) or total <= 0:
        raise ValueError('atom weights must have a finite positive total')
    eps = config.get('tie_epsilon')
    if not finite_number(eps) or eps < 0:
        raise ValueError('tie_epsilon must be finite and nonnegative')
    supported = ('space_T_H1', 'word_pair', 'length_pair')
    if config.get('atom_context_channels') != list(supported):
        raise ValueError('this baseline requires its three declared context channels')
    if config.get('direction') != 'closer_to_known3':
        raise ValueError('unsupported score direction')


def aggregate_atoms(views: dict, config: dict) -> tuple[float, list[str]]:
    validate_config(config)
    active = [a for a in config['primary_atoms'] if config['atom_weights'][a] > 0 and views['ATOM:'+a]['delta'] is not None]
    if not active:
        raise ValueError('no comparable positive-weight primary atoms; contest is unscorable')
    weights = config['atom_weights']
    # Rescale positive weights before multiplication for numerical stability.
    scale = max(weights[a] for a in active)
    total = math.fsum(weights[a]/scale for a in active)
    delta = math.fsum((weights[a]/scale)*views['ATOM:'+a]['delta'] for a in active)/total
    return delta, active


def pick(delta: float | None, set_id: str, config: dict | None = None) -> tuple[str, bool]:
    config = CONFIG if config is None else config
    if delta is not None and abs(delta) > config['tie_epsilon']:
        return ('A' if delta > 0 else 'B'), False
    # Only the FINAL tie receives a side. Feature ties never become random votes.
    coin = hashlib.sha256((digest(config)+'|'+set_id+'|final-tie-v1').encode()).digest()[0] & 1
    return ('A' if coin == 0 else 'B'), True


def predict(case: dict, *, config: dict | None = None) -> dict:
    validate_case(case)
    config = CONFIG if config is None else config
    validate_config(config)
    known = case['known']
    # Each reference view uses the other two pages, preventing self-overlap in J19.
    refs = [extract(d, [x for j, x in enumerate(known) if i != j], case['text_profile']) for i, d in enumerate(known)]
    sides = {k: extract(v, known, case['text_profile']) for k, v in case['candidates'].items()}
    keys = sorted(set().union(*(r.keys() for r in refs), sides['A'].keys(), sides['B'].keys()))
    channels = {}
    for key in keys:
        exemplar = next((x[key] for x in refs + list(sides.values()) if key in x), Feature())
        empty = lambda: Feature(conditional=exemplar.conditional)
        channels[key] = compare([r.get(key, empty()) for r in refs], sides['A'].get(key, empty()), sides['B'].get(key, empty()))
    views = {}
    for name in list(NAMES) + ['ATOM:'+a for a in ATOMS]:
        parts = [v for k, v in channels.items() if k.startswith(name+'/')]
        delta = aggregate([v['delta'] for v in parts])
        views[name] = {'name': NAMES.get(name, name), 'delta': delta, 'channels_used': sum(v['delta'] is not None for v in parts), 'status': 'OK' if delta is not None else 'NA', 'pick': None if delta is None or abs(delta) <= config['tie_epsilon'] else 'A' if delta > 0 else 'B'}
    delta, active = aggregate_atoms(views, config)
    choice, tie = pick(delta, case['set_id'], config)
    views['J24'].update(delta=delta, status='FINAL_TIE' if tie else 'OK', pick=choice,
                         channels_used=sum(views['ATOM:'+a]['channels_used'] for a in active))
    return {
        'schema_version': 1, 'set_id': case['set_id'], 'cluster_id': case['cluster_id'], 'seed': case['seed'],
        'input_hash': digest(case), 'config_hash': digest(config),
        'prediction': choice, 'final_tie': tie, 'delta': delta,
        'active_atoms': active,
        'views': views, 'channels': channels,
    }
