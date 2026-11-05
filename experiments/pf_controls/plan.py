from __future__ import annotations

import hashlib
from pathlib import Path

from judges.v03.adapter import source_documents
from judges.v03.protocol import digest as jury_digest, extractor_hash, PROTOCOL_HASH
from experiments.pf_generation import MODEL_SET_HASH, EXTRACTOR_HASH, PROTOCOL_HASH as EXPECTED_PROTOCOL
from . import CONTRACT, SEED, BRANCHES, NAMESPACE, FAMILIES
from .common import ROOT, PACKAGE, digest, file_hash, frozen_sources, read, require, runtime_inputs, seal, sources, unseal, write_json
from .proxy import fit_fold
from .replay import Runtime


def structure(rt, bifolia):
    _, corpus, docs, loci, _ = source_documents(PACKAGE)
    events = []
    for bif in bifolia:
        page = str(rt.C.pages[bif][-1])
        for li, (frame, obs, loc) in enumerate(zip(docs[page]['layout']['lines'], docs[page]['observations']['lines'], loci[page])):
            # Read structural eligibility only. Never place true tokens in selector metadata.
            if not(frame['whole_line_usable'] and frame['paragraph_final'] and frame['paragraph_line'] is not None
                   and frame['paragraph_line'] >= 2):
                continue
            for si, (sf, so) in enumerate(zip(frame['segments'], obs['segments'])):
                if sf['end'] == 'LINE_END' and so['mode'] == 'FULL':
                    events.append(dict(bif=bif, page=page, locus=str(loc), segment_id=si, line_index=li,
                                       full=True, space=len(so['tokens']) >= 2))
    return events, jury_digest(corpus), corpus['source_hashes']


def create(output, bifolia, kind='smoke'):
    require(not Path(output).exists(), 'Plan root already exists')
    require(kind in ('smoke', 'controls'), 'Invalid plan kind')
    require(extractor_hash() == EXTRACTOR_HASH and PROTOCOL_HASH == EXPECTED_PROTOCOL, 'Frozen jury changed')
    rt = Runtime()
    if bifolia == ['all']:
        bifolia = sorted(rt.C.bifs)
    require(bifolia and len(set(bifolia)) == len(bifolia) and set(bifolia) <= set(rt.C.bifs), 'Invalid target bifolia')
    require(kind != 'smoke' or len(bifolia) <= 3, 'Smoke is limited to three bifolia')
    require(kind != 'controls' or sorted(bifolia) == sorted(rt.C.bifs), 'Full controls require the fixed twenty bifolia')
    folds = {b: int(rt.active.SEL.reset_index().set_index('bif').loc[b,'fold']) for b in bifolia}
    events, corpus, raw = structure(rt, bifolia)
    p = dict(schema_version=1, kind=kind, seed=SEED, branches=BRANCHES, namespace=NAMESPACE,
             bifolia=bifolia, folds=folds, target_slot=3, contract=read(ROOT/CONTRACT),
             proxies={str(f):fit_fold(rt,f) for f in sorted(set(folds.values()))},
             eligible_events=events, corpus_hash=corpus, source_hashes=raw,
             eligible_cohorts={lane:[b for b in bifolia if any(e['bif']==b and (lane!='space_T_H1' or e['space'])
                                                          for e in events)] for lane in FAMILIES},
             source_files=sources(), frozen_sources=frozen_sources(), runtime_inputs=rt.input_snapshot,
             model_set_hash=MODEL_SET_HASH, extractor_hash=EXTRACTOR_HASH, protocol_hash=EXPECTED_PROTOCOL,
             selection='extreme strict proxy NLL vs BASE; epsilon 1e-12; first branch ID on tie',
             blinding='hash(plan hash, family, direction, bif) bit; independent of words/NLL/CAL',
             manipulation='page target-channel empirical feature counts differ after substitution',
             denominators='all structurally eligible pages; unchanged cases remain planned/comparable ties',
             prediction_gate='all predictions sealed before any key read for scoring', promotion=None)
    p = seal(p)
    require(runtime_inputs() == rt.input_snapshot and sources() == p['source_files'], 'Inputs changed during planning')
    Path(output).mkdir(parents=True, exist_ok=False)
    write_json(Path(output)/'plan.json', p)
    return p


def load(path):
    p = unseal(read(path))
    require(p['schema_version'] == 1 and p['seed'] == SEED and p['branches'] == BRANCHES
            and p['namespace'] == NAMESPACE and p['target_slot'] == 3, 'Unsupported replay plan')
    require(p['kind'] in ('smoke','controls') and len(set(p['bifolia'])) == len(p['bifolia'])
            and (len(p['bifolia']) == 20 if p['kind']=='controls' else 1 <= len(p['bifolia']) <= 3),
            'Invalid fixed control cohort')
    require(p['eligible_cohorts'] == {lane:[b for b in p['bifolia']
            if any(e['bif']==b and (lane!='space_T_H1' or e['space']) for e in p['eligible_events'])]
            for lane in FAMILIES}, 'Eligible cohort was filtered after preregistration')
    require(p['contract'] == read(ROOT/CONTRACT), 'Control contract changed')
    require(p['source_files'] == sources() and p['frozen_sources'] == frozen_sources(), 'Sealed source changed')
    require(p['runtime_inputs'] == runtime_inputs(), 'Expanded input changed')
    require(p['model_set_hash'] == MODEL_SET_HASH and p['extractor_hash'] == extractor_hash()
            and p['protocol_hash'] == PROTOCOL_HASH == EXPECTED_PROTOCOL, 'Model/extractor/protocol mismatch')
    require(set(p['folds']) == set(p['bifolia']) and set(p['proxies']) == {str(f) for f in p['folds'].values()},
            'Incomplete proxy fold coverage')
    for fold, table in p['proxies'].items():
        require(table['fold'] == int(fold) and table['known3_used'] is False
                and len(set(table['training_bifolia'])) == 16 and len(set(table['excluded_bifolia'])) == 4
                and not set(table['training_bifolia']) & set(table['excluded_bifolia'])
                and len(set(table['training_pages'])) == 64
                and table['tables_sha256'] == digest(table['probabilities']), 'Invalid proxy scope/hash')
        require(all(b in table['excluded_bifolia'] for b,f in p['folds'].items() if str(f)==fold),
                'Target leaked into proxy fit')
    return p
