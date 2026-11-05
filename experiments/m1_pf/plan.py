from __future__ import annotations

import json
from pathlib import Path

from . import ARMS, BASE_COMMIT, EXTRACTOR_HASH, PROTOCOL_HASH, MODEL_SET_HASH, HISTORICAL_SEEDS
from .common import PACKAGE, digest, file_hash, frozen_sources, model_dir, overlay_sources, write_json
from .inputs import runtime_inputs


def endpoint_observation_map(doc):
    """Atoms consume word_events (FULL lines); endpoint diagnostics also use END_ONLY."""
    from judges.v03.observations import word_events
    return {(e.line, e.segment): e.atom for e in word_events(doc) if e.boundary in ('L', 'P')}


def scope_ledger(bifolia):
    # The judge's unchanged adapter is used only to map structural eligibility;
    # its genuine tokens/labels are not forwarded to the generator runner.
    runtime_inputs()
    from judges.v03.adapter import source_documents
    from .runtime import Runtime
    C, corpus, docs, page_loci, provenance = source_documents(PACKAGE)
    e = Runtime().engine
    rows = []
    for bif in bifolia:
        page = C.pages[bif][-1]
        schedule = {(str(r.locus), int(r.segment_id)): r for r in C.schedules[page].itertuples(index=False)}
        doc = docs[page]
        atoms = endpoint_observation_map(doc)
        for li, (loc, frame, obs) in enumerate(zip(page_loci[page], doc['layout']['lines'], doc['observations']['lines'])):
            for si, sf in enumerate(frame['segments'] or []):
                sr = schedule.get((loc, si))
                pf = bool(sr is not None and e.is_pf(sr))
                atom = 'PLANT_END' if sf['end'] == 'PLANT' else 'PARA_END' if frame['paragraph_final'] else 'LINE_END'
                mode = obs['segments'][si]['mode']
                rows.append(dict(bif=bif, page=page, locus=loc, segment_id=si, generator_pf=pf,
                                 generator_scheduled=sr is not None, structural_end_atom=atom,
                                 judge_atom=atoms.get((li, si)), observation_mode=mode,
                                 judge_observed=(li, si) in atoms, endpoint_usable=mode != 'NONE', boundary=sf['end'],
                                 paragraph_line=frame['paragraph_line'], paragraph_final=frame['paragraph_final'],
                                 reason='INTERVENTION' if pf else 'NO_GENERATOR_SEGMENT' if sr is None else
                                        'PLANT_END' if sf['end'] == 'PLANT' else
                                        'ONE_LINE_PARAGRAPH' if frame['paragraph_line'] == 1 and frame['paragraph_final'] else 'NOT_PF'))
    from judges.v03.protocol import digest as jury_digest
    return rows, {'corpus_hash': jury_digest(corpus), 'source_hashes': corpus['source_hashes'],
                  'quality_provenance_hash': digest(provenance)}


def create_plan(output, bifolia, runs, blinding_seed=20261104, kind='smoke'):
    from judges.v03.protocol import PROTOCOL_HASH as protocol, extractor_hash
    if protocol != PROTOCOL_HASH or extractor_hash() != EXTRACTOR_HASH:
        raise ValueError('The pinned jury v0.3 extractor/protocol is not available')
    if not bifolia or len(set(bifolia)) != len(bifolia) or not runs or len(set(runs)) != len(runs):
        raise ValueError('Bifolia/seeds must be nonempty and unique')
    if any(type(r) is not int or r < 0 for r in runs):
        raise ValueError('Seeds must be nonnegative integers')
    if bifolia == ['all']:
        import csv
        with (PACKAGE / 'model/parameters/LEAFEX_ALPHA_SELECTED.csv').open() as f:
            bifolia = list(dict.fromkeys(r['bif'] for r in csv.DictReader(f)))
    if kind not in ('smoke', 'development'):
        raise ValueError('Unknown plan kind')
    if kind == 'smoke' and len(bifolia) * len(runs) > 20:
        raise ValueError('Smoke plans are limited to 20 cases per arm; specify development for a larger plan')
    files = frozen_sources()
    ledger, source = scope_ledger(bifolia)
    settings = {'schema_version': 2, 'base_commit': BASE_COMMIT, 'kind': kind,
                'package': PACKAGE.name, 'arms': list(ARMS), 'runs': list(runs), 'bifolia': list(bifolia),
                'blinding_seed': blinding_seed, 'primary': 'J24.CAL',
                'local_primary': 'ATOM.PARA_END.CAL', 'required_model_set_hash': MODEL_SET_HASH,
                'extractor_hash': EXTRACTOR_HASH, 'protocol_hash': PROTOCOL_HASH,
                'frozen_sources': files, 'data': source, 'scope_ledger_hash': digest(ledger),
                'runtime_inputs': runtime_inputs(),
                'overlay_sources': overlay_sources(),
                'proposal_id_contract': 'legacy_shared_all_attempts; used by correction side RNG; not an observation-only counter',
                'arm_contracts': {
                    'BASE': 'original two-candidate argmax plus LEN1 rescue; continue base-argmax RNG',
                    'PF_NO_RESCUE': 'two-candidate argmax, zero rescue; continue argmax RNG',
                    'PF_ANCHOR': 'generate/score both candidates; adopt candidate0; continue candidate0 RNG'},
                'failure_policy': 'stop_on_first_failure; preserve partial artifacts; no seed replacement; rerun only into a new directory with the same plan',
                'inference': 'development_reused_bifolia_not_independent_confirmation',
                'promotion_policy': 'NONE; acceptance margins and multiplicity must be fixed before inferential runs',
                'historical_seeds_for_reference_only': list(HISTORICAL_SEEDS),
                'historical_exclusion_not_a_new_exclusion_rule': 91706}
    settings['plan_hash'] = digest(settings)
    output = Path(output)
    output.mkdir(parents=True, exist_ok=False)
    write_json(output / 'plan.json', settings)
    write_json(output / 'scope_ledger.json', ledger)
    return settings


def load_plan(path):
    path = Path(path)
    p = json.loads(path.read_text())
    h = p.pop('plan_hash')
    if digest(p) != h:
        raise ValueError('Plan was changed after being sealed')
    p['plan_hash'] = h
    if p.get('schema_version') != 2:
        raise ValueError('Old M1 plan lacks runtime-input binding; create a schema-v2 plan')
    if p['base_commit'] != BASE_COMMIT or p['arms'] != list(ARMS) or p['primary'] != 'J24.CAL':
        raise ValueError('Unsupported M1 plan/primary')
    if frozen_sources() != p['frozen_sources']:
        raise ValueError('Frozen source hash mismatch')
    if overlay_sources() != p['overlay_sources']:
        raise ValueError('Overlay code changed after the plan was sealed; create a new plan')
    if runtime_inputs() != p['runtime_inputs']:
        raise ValueError('Sealed runtime inputs changed')
    ledger = json.loads((path.parent / 'scope_ledger.json').read_text())
    if digest(ledger) != p['scope_ledger_hash']:
        raise ValueError('Structural scope ledger changed')
    return p


def generate(plan_path, output, reference=False, arm_order=None):
    from .runtime import Runtime
    plan = load_plan(plan_path)
    arms = tuple(arm_order or ARMS)
    if set(arms) != set(ARMS) or len(arms) != 3:
        raise ValueError('All three M1 arms must be generated exactly once')
    output = Path(output)
    output.mkdir(parents=True, exist_ok=False)
    write_json(output / 'plan.json', plan)
    write_json(output / 'STATUS.json', {'status': 'RUNNING', 'plan_hash': plan['plan_hash']})
    records = []
    try:
        rt = Runtime()
        if rt.input_snapshot != plan['runtime_inputs']:
            raise ValueError('Runtime inputs differ from the sealed plan')
        for arm in arms + (('REFERENCE',) if reference else ()):
            directory = model_dir(arm) if arm != 'REFERENCE' else 'HerbalA_v22_3_M1_REFERENCE'
            for bif in plan['bifolia']:
                for run in plan['runs']:
                    dest = output / arm / f'run{run}' / directory / bif.replace(':', '_')
                    md = rt.generate(bif, run, arm, dest)
                    records.append(dict(arm=arm, bif=bif, run=run, path=str(dest.relative_to(output)),
                                        files={str(p.relative_to(dest)): file_hash(p) for p in sorted(dest.iterdir()) if p.is_file()}))
                    print(f'GEN {arm} {bif} {run} {md["generated_rows_sha256"][:12]}', flush=True)
    except Exception as exc:
        write_json(output / 'STATUS.json', {'status': 'FAILED', 'error': str(exc), 'completed_cases': len(records),
                                            'plan_hash': plan['plan_hash']})
        raise
    write_json(output / 'manifest.json', {'plan_hash': plan['plan_hash'], 'records': records})
    write_json(output / 'STATUS.json', {'status': 'GENERATED_NOT_AUDITED', 'completed_cases': len(records),
                                        'plan_hash': plan['plan_hash']})
    return records
