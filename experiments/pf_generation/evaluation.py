"""Adapters around the unchanged v0.3 panel; CAL never falls back to PROTO."""
from __future__ import annotations

from collections import defaultdict
import json
import math
from pathlib import Path
import random

from . import ARMS, CONTRASTS
from experiments.m1_pf.evaluation import distance_summary
from .audit import generation_binding, require
from .common import PACKAGE, file_hash, model_dir, write_json
from .plan import load_plan


def audited(plan_path, generated):
    plan = load_plan(plan_path)
    binding = generation_binding(plan, generated)
    seal = json.loads((Path(generated) / 'AUDIT.json').read_text())
    require(seal.get('schema_version') == 1 and seal['plan_hash'] == plan['plan_hash']
            and seal['generation_binding'] == binding and file_hash(seal['report']) == seal['report_sha256'],
            'Missing/changed mechanical audit seal')
    report = json.loads(Path(seal['report']).read_text())
    require(report.get('schema_version') == 1 and report['plan_hash'] == plan['plan_hash']
            and report['generation_binding'] == binding and report['status'] == 'PASS'
            and report['base_reference_checked'] and report['base_reference_main_rng_checked'],
            'Evaluation requires a passing mechanical audit and exact BASE reference')
    if report['repeat_checked']:
        require(generation_binding(plan, report['repeat_root']) == report['repeat_binding'],
                'Audited repeat artifacts changed')
    return plan


def export(plan_path, generated, output):
    from judges.v03.adapter import export as frozen_export
    plan = audited(plan_path, generated)
    output = Path(output)
    output.mkdir(parents=True, exist_ok=False)
    corpus_hash = None
    seals = {}
    for arm in ARMS:
        adapter_plan = dict(package=str(PACKAGE), generated_root=str((Path(generated) / arm).resolve()),
                            model_dir=model_dir(arm), runs=plan['runs'], bifolia=plan['bifolia'],
                            blinding_seed=plan['blinding_seed'])
        frozen_export(adapter_plan, output / arm)
        manifest = json.loads((output / arm / 'export_manifest.json').read_text())
        require(manifest['corpus_hash'] == plan['data']['corpus_hash'], 'Genuine corpus changed since planning')
        corpus = json.loads((output / arm / 'corpus.json').read_text())
        require(corpus['source_hashes'] == plan['data']['source_hashes'], 'Raw source/quality ledger changed')
        if corpus_hash is None:
            corpus_hash = manifest['corpus_hash']
        require(corpus_hash == manifest['corpus_hash'], 'Genuine corpus/masks changed across arms')
        seals[arm] = {name: file_hash(output / arm / name)
                      for name in ('inputs.jsonl', 'answer_key.jsonl', 'corpus.json', 'export_manifest.json')}
    write_json(output / 'PFGEN_EXPORT.json', dict(plan_hash=plan['plan_hash'], corpus_hash=corpus_hash,
                                              primary='J24.CAL', arms=list(ARMS), files=seals))
    return plan


def evaluate(plan_path, inputs, models, output, jobs=1, bootstrap=10000):
    from judges.v03.calibration import load_models
    from judges.v03.protocol import digest, extractor_hash, PROTOCOL_HASH, read_jsonl
    from judges.v03.artifacts import predict_file
    from judges.v03.statistics import score, compare_scores
    plan = load_plan(plan_path)
    model_set, _ = load_models(models)
    require(digest(model_set) == plan['required_model_set_hash'], 'Frozen CAL model set differs from the specification')
    require(extractor_hash() == plan['extractor_hash'] and PROTOCOL_HASH == plan['protocol_hash'], 'Jury configuration changed')
    manifest = json.loads((Path(inputs) / 'PFGEN_EXPORT.json').read_text())
    require(manifest['plan_hash'] == plan['plan_hash'] and manifest['primary'] == 'J24.CAL'
            and manifest['arms'] == list(ARMS), 'Export plan differs')
    for arm in ARMS:
        for name, expected in manifest['files'][arm].items():
            require(Path(name).name == name and file_hash(Path(inputs) / arm / name) == expected,
                    'Sealed input/key/corpus changed')
    output = Path(output)
    output.mkdir(parents=True, exist_ok=False)
    # Seal all predictions before any answer key is read by the scorer.
    for arm in ARMS:
        predict_file(Path(inputs) / arm / 'inputs.jsonl', output / 'predictions' / arm,
                     models, primary='J24.CAL', jobs=jobs)
    for arm in ARMS:
        score(output / 'predictions' / arm, Path(inputs) / arm / 'answer_key.jsonl',
              output / 'scores' / arm, bootstrap)
    comparisons = {}
    for left, right in CONTRASTS:
        label = left + '__' + right
        compare_scores(output / 'scores' / left, output / 'scores' / right,
                       output / 'paired' / label, bootstrap)
        rows = [read_jsonl(output / 'scores' / a / 'measurements.jsonl') for a in (left, right)]
        views = sorted({r['view'] for r in rows[0]} & {r['view'] for r in rows[1]})
        comparisons[label] = {v: distance_summary([r for r in rows[0] if r['view'] == v],
                                                 [r for r in rows[1] if r['view'] == v], bootstrap) for v in views}
    write_json(output / 'PFGEN_COMPARISONS.json', dict(plan_hash=plan['plan_hash'], primary='J24.CAL',
                                                  local_primary='ATOM.PARA_END.CAL', comparisons=comparisons,
                                                  promotion=None, acceptance_margins=None,
                                                  multiplicity='descriptive_only_no_inferential_selection'))
    return comparisons
