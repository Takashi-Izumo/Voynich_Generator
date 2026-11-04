"""Optional adapter; loaded only by export-v223, never by the blind predictor."""
from __future__ import annotations

from collections import defaultdict
import csv
import gzip
import hashlib
from pathlib import Path
import random
import re
import runpy
import sys

from .contest import write_json, write_jsonl
from .schema import glyphs, validate_case


def export(package: Path, generated: Path, model_dir: str, runs: list[int], bifs: list[str] | None, output: Path, blind_seed: int):
    package = package.resolve()
    sys.path.insert(0, str(package/'model/code'))
    try:
        g = runpy.run_path(str(package/'model/code/run_v22_3_stage3d.py'), run_name='judges_export_adapter')
        C = g['benv'].e.context()
    except (ImportError, FileNotFoundError) as exc:
        raise ValueError('v22.3 adapter requires the documented Python environment and verified parent ZIPs: '+str(exc)) from exc
    builder = sys.modules['build_full_schedule']
    raw = {}
    raw_path = g['rb'].ep.DATA/'ZL3b-n.txt'
    for line in raw_path.read_text().splitlines():
        m = re.match(r'^<([^>]+)>\s*(.*)$', line)
        if m and '.' in m[1]:
            raw[m[1].split(',')[0]] = m[2]
    plans, docs, coverage = {}, {}, {}
    for page in C.seqs:
        plan, lines, omitted = [], [], []
        for locus, group in C.T[C.T.page.eq(page)].sort_values('global_order').groupby('locus', sort=False):
            items = builder.raw_items(raw.get(str(locus), ''))
            # Preserve the generator's documented f28v.7 layout exception.
            if str(locus) == 'f28v.7':
                items = [x for x in items if x[0] != 'B']
            exact = bool(items) and all(k != 'X' for k, _ in items) and [v for k, v in items if k == 'W'] == group.surface.astype(str).tolist()
            segs = [{'end': 'LINE_END', 'tokens': []}]
            for kind, value in items:
                if kind == 'B':
                    segs[-1]['end'] = 'PLANT'
                    segs.append({'end': 'LINE_END', 'tokens': []})
                elif kind == 'W':
                    segs[-1]['tokens'].append(value)
            exact = exact and all(s['tokens'] for s in segs)
            para = int(group.iloc[0].para)
            lines.append({'paragraph': para, 'segments': segs if exact else [], **({} if exact else {'excluded': True})})
            plan.append((str(locus), exact, para, len(segs)))
            if not exact:
                omitted.append(str(locus))
        docs[str(page)] = {'lines': lines}
        plans[str(page)] = plan
        coverage[str(page)] = {'lines': len(lines), 'excluded_lines': omitted}

    selected = sorted(C.bifs if bifs is None else bifs)
    if len(set(selected)) != len(selected) or not set(selected) <= set(C.bifs) or len(set(runs)) != len(runs):
        raise ValueError('invalid/duplicate bifolia or runs')
    if not selected or not runs:
        raise ValueError('empty selection')
    cases, keys, provenance = [], [], []
    count = len(selected)*len(runs)
    rng = random.Random(blind_seed)
    flags = [True]*(count//2) + [False]*(count//2)
    if count % 2:
        flags.append(bool(rng.getrandbits(1)))
    rng.shuffle(flags)
    for bif in selected:
        page = str(C.pages[bif][-1])
        known_pages = [str(p) for p in C.pages[bif] if str(p) != page]
        for run in runs:
            path = generated/f'run{run}'/model_dir/bif.replace(':', '_')/'tokens.csv.gz'
            by_line = defaultdict(lambda: defaultdict(list))
            with gzip.open(path, 'rt') as f:
                rows = list(csv.DictReader(f))
            if not rows or {r['page'] for r in rows} != {page} or {int(r['run']) for r in rows} != {run}:
                raise ValueError(f'wrong/empty generated target: {path}')
            for r in rows:
                by_line[r['locus']][int(r['segment_id'])].append(r)
            if set(by_line) != {x[0] for x in plans[page]}:
                raise ValueError(f'generated loci differ from shared layout: {path}')
            lines = []
            for locus, exact, para, nseg in plans[page]:
                if not exact:
                    lines.append({'paragraph': para, 'segments': [], 'excluded': True})
                    continue
                src = by_line[locus]
                if set(src) != set(range(nseg)):
                    raise ValueError(f'generated segment layout mismatch: {locus}')
                segs = []
                for si in range(nseg):
                    rr = sorted(src[si], key=lambda r: int(r['segment_wordnum']))
                    end = 'LINE_END' if si == nseg-1 else 'PLANT'
                    if {r['boundary_type'] for r in rr} != {end}:
                        raise ValueError(f'boundary mismatch: {locus}')
                    if [int(r['segment_wordnum']) for r in rr] != list(range(1,len(rr)+1)):
                        raise ValueError(f'noncontiguous/duplicate segment words: {locus}')
                    if [int(r['draw_segment_end']) for r in rr] != [0]*(len(rr)-1)+[1]:
                        raise ValueError(f'invalid segment closure: {locus}')
                    # Visible surface, not hidden pre-rare stable anchor: m remains visible.
                    tokens = [''.join(gl) if (gl := glyphs(r['surface'])) else None for r in rr]
                    segs.append({'end': end, 'tokens': tokens})
                lines.append({'paragraph': para, 'segments': segs})
            fake = {'lines': lines}
            i = len(cases)
            real_side = 'A' if flags[i] else 'B'
            opaque = hashlib.sha256(f'v223/{bif}/{run}'.encode()).hexdigest()[:24]
            case = {
                'schema_version': 1, 'set_id': opaque,
                'cluster_id': hashlib.sha256(('cluster/'+bif).encode()).hexdigest()[:16],
                'seed': run, 'text_profile': 'stable22',
                'known': [docs[p] for p in known_pages],
                'candidates': {real_side: docs[page], 'B' if real_side == 'A' else 'A': fake},
            }
            validate_case(case)
            cases.append(case)
            keys.append({'set_id': opaque, 'truth': real_side})
            provenance.append({'set_id': opaque, 'bif': bif, 'target': page, 'known': known_pages, 'generated_file': str(path), 'generated_sha256': hashlib.sha256(path.read_bytes()).hexdigest()})
    output.mkdir(parents=True, exist_ok=False)
    write_jsonl(output/'inputs.jsonl', cases)
    write_jsonl(output/'answer_key.jsonl', keys)
    write_json(output/'export_manifest.json', {
        'profile': 'v223-shared-clean-lines-stable22-v1',
        'blinding_seed': blind_seed,
        'selection': {'bifolia': selected, 'runs': runs}, 'sets': len(cases),
        'coverage': {p: coverage[p] for p in {r['target'] for r in provenance} | {p for r in provenance for p in r['known']}},
        'provenance': provenance, 'raw_sha256': hashlib.sha256(raw_path.read_bytes()).hexdigest(),
        'conditions': ['original target segment layout supplied to both candidates', 'shared whole-line mask; excluded lines retain paragraph/line positions', 'known pages independently use same clean-line rule', 'rare characters removed symmetrically; J21 unavailable', 'not the legacy 200-contest preprocessing'],
        'layout_exception': 'f28v.7 ignores PLANT markers, matching the frozen generator',
    })
    return len(cases)
