"""Seal trained laws together with sources, expanded inputs and scope."""
from __future__ import annotations

import json
from pathlib import Path

from experiments.m1_pf.plan import scope_ledger
from experiments.m1_pf.runtime import Runtime as SourceRuntime
from . import ARMS, BASE_COMMIT, CONTRASTS, DESIGN, CAPABILITY_ERRATUM, EXTRACTOR_HASH, MODEL_SET_HASH, POLICY, PROTOCOL_HASH, TRACE_SCHEMA
from .common import ROOT, PACKAGE, digest, file_hash, frozen_sources, implementation_sources, model_dir, require, runtime_inputs, write_json
from .laws import Law, fit_fold
from . import SURFACE_COMMIT_POLICY


def create_plan(output, bifolia, runs, kind='smoke', identity=False, blinding_seed=20261105):
    from judges.v03.protocol import extractor_hash, PROTOCOL_HASH as protocol
    require(not Path(output).exists(), 'Plan output already exists')
    require(protocol == PROTOCOL_HASH and extractor_hash() == EXTRACTOR_HASH, 'Frozen jury differs')
    require(kind in ('smoke', 'development'), 'Unknown plan kind')
    rt = SourceRuntime()
    if bifolia == ['all']:
        bifolia = sorted(rt.C.bifs)
    require(bifolia and len(set(bifolia)) == len(bifolia) and set(bifolia) <= set(rt.C.bifs), 'Invalid bifolia')
    require(runs and len(set(runs)) == len(runs) and all(type(s) is int and s >= 0 for s in runs), 'Invalid seeds')
    require(kind != 'smoke' or len(bifolia) * len(runs) <= 20, 'Smoke limited to 20 cases per arm')
    sources = implementation_sources()
    folds = {b: int(rt.active.SEL.reset_index().set_index('bif').loc[b, 'fold']) for b in bifolia}
    laws = {str(f): fit_fold(rt, f, identity) for f in sorted(set(folds.values()))}
    ledger, data = scope_ledger(bifolia)
    plan = dict(schema_version=2, trace_schema=TRACE_SCHEMA, experiment='PF_GENERATION_DESIGN_007_STUDY_1', base_commit=BASE_COMMIT,
                package=PACKAGE.name, arms=list(ARMS), contrasts=[list(c) for c in CONTRASTS], kind=kind,
                bifolia=bifolia, runs=runs, folds=folds, laws=laws, policy=dict(POLICY),surface_commit_policy=dict(SURFACE_COMMIT_POLICY),
                identity_override=bool(identity), blinding_seed=blinding_seed,
                required_model_set_hash=MODEL_SET_HASH, extractor_hash=EXTRACTOR_HASH, protocol_hash=PROTOCOL_HASH,
                primary='J24.CAL', local_primary='ATOM.PARA_END.CAL', data=data,
                scope_ledger_hash=digest(ledger), frozen_sources=frozen_sources(),
                implementation_sources=sources, design_sha256=file_hash(ROOT / DESIGN),
                capability_design_erratum_sha256=file_hash(ROOT / CAPABILITY_ERRATUM),
                runtime_inputs=rt.input_snapshot, inference='descriptive_development_reused_bifolia',
                proposal_id_contract='legacy_shared_all_attempts_including_discarded_branches',
                main_rng_continuation='initial_two_candidate_argmax_in_each_arm',
                failure_policy='stop_first_failure_no_new_seed_exclusion_or_replacement', promotion=None)
    require(implementation_sources() == sources and runtime_inputs() == rt.input_snapshot, 'Inputs changed while fitting')
    plan['plan_hash'] = digest(plan)
    output = Path(output)
    output.mkdir(parents=True, exist_ok=False)
    write_json(output / 'plan.json', plan)
    write_json(output / 'scope_ledger.json', ledger)
    return plan


def validate_laws(plan):
    require(set(plan['folds']) == set(plan['bifolia']), 'Incomplete fold assignment')
    require(set(plan['laws']) == {str(f) for f in plan['folds'].values()}, 'Missing/unexpected laws')
    for key, payload in plan['laws'].items():
        Law.load(payload)
        require(payload['fold'] == int(key) and not payload['known3_used']
                and len(set(payload['training_bifolia'])) == 16
                and len(set(payload['excluded_bifolia'])) == 4
                and not set(payload['training_bifolia']) & set(payload['excluded_bifolia']), 'Invalid law training scope')
        require(payload['runtime_inputs'] == plan['runtime_inputs'], 'Law runtime provenance mismatch')
        require(payload['identity_override'] == plan['identity_override'], 'Law identity policy mismatch')
        for bif, fold in plan['folds'].items():
            if str(fold) == key:
                require(bif in payload['excluded_bifolia'], 'Target bifolium in training law')


def load_plan(path):
    path = Path(path)
    plan = json.loads(path.read_text())
    require(digest({k: v for k, v in plan.items() if k != 'plan_hash'}) == plan['plan_hash'], 'Sealed PF plan changed')
    require(plan['schema_version'] == 2 and plan.get('trace_schema') == TRACE_SCHEMA
            and plan['experiment'] == 'PF_GENERATION_DESIGN_007_STUDY_1'
            and plan['base_commit'] == BASE_COMMIT and plan['arms'] == list(ARMS)
            and plan['contrasts'] == [list(c) for c in CONTRASTS] and plan['policy'] == POLICY
            and plan.get('surface_commit_policy') == SURFACE_COMMIT_POLICY
            and plan['required_model_set_hash'] == MODEL_SET_HASH and plan['extractor_hash'] == EXTRACTOR_HASH
            and plan['protocol_hash'] == PROTOCOL_HASH and plan['primary'] == 'J24.CAL'
            and plan['local_primary'] == 'ATOM.PARA_END.CAL', 'Unsupported PF contract')
    require(frozen_sources() == plan['frozen_sources'], 'Frozen generator/judge changed')
    require(implementation_sources() == plan['implementation_sources'], 'PF implementation changed after sealing')
    require(file_hash(ROOT / DESIGN) == plan['design_sha256'], 'Design contract changed')
    require(file_hash(ROOT / CAPABILITY_ERRATUM) == plan['capability_design_erratum_sha256'], 'Capability design erratum changed')
    require(runtime_inputs() == plan['runtime_inputs'], 'Expanded runtime inputs changed')
    require(digest(json.loads((path.parent / 'scope_ledger.json').read_text())) == plan['scope_ledger_hash'],
            'Scope ledger changed')
    validate_laws(plan)
    return plan


def generate(plan_path, output, reverse=False):
    from .runtime import Runtime
    plan = load_plan(plan_path)
    output = Path(output)
    output.mkdir(parents=True, exist_ok=False)
    write_json(output / 'plan.json', plan)
    write_json(output / 'STATUS.json', dict(status='RUNNING', plan_hash=plan['plan_hash']))
    records = []
    try:
        rt = Runtime(plan)
        order = (*ARMS, 'REFERENCE')
        for arm in (tuple(reversed(order)) if reverse else order):
            for bif in plan['bifolia']:
                for run in plan['runs']:
                    dest = output / arm / f'run{run}' / model_dir(arm) / bif.replace(':', '_')
                    md = rt.generate(bif, run, arm, dest)
                    records.append(dict(arm=arm, bif=bif, run=run, path=str(dest.relative_to(output)),
                                        files={p.name: file_hash(p) for p in sorted(dest.iterdir()) if p.is_file()}))
                    print(f'GEN {arm} {bif} {run} {md["generated_rows_sha256"][:12]}', flush=True)
    except Exception as exc:
        write_json(output / 'STATUS.json', dict(status='FAILED', error=str(exc), completed_cases=len(records),
                                               plan_hash=plan['plan_hash']))
        raise
    write_json(output / 'manifest.json', dict(plan_hash=plan['plan_hash'], records=records))
    write_json(output / 'STATUS.json', dict(status='GENERATED_NOT_AUDITED', completed_cases=len(records),
                                           plan_hash=plan['plan_hash']))
    return records
