from __future__ import annotations

from collections import defaultdict
import hashlib
import json
from pathlib import Path
import random

from .registry import CONFIG, NAMES
from .schema import read_jsonl, validate_case
from .scoring import CONFIG_HASH, digest, predict


def write_json(path: Path, obj):
    path.write_text(json.dumps(obj, ensure_ascii=False, indent=2, sort_keys=True, allow_nan=False)+'\n', encoding='utf-8')


def write_jsonl(path: Path, rows):
    path.write_text(''.join(json.dumps(x, ensure_ascii=False, sort_keys=True, allow_nan=False)+'\n' for x in rows), encoding='utf-8')


def unique(rows):
    ids = [r['set_id'] for r in rows]
    if len(set(ids)) != len(ids):
        raise ValueError('duplicate set_id')


def unique_trials(rows):
    trials = [(r['cluster_id'], r['seed']) for r in rows]
    if len(set(trials)) != len(trials):
        raise ValueError('duplicate cluster_id/seed trial')


def code_hash():
    root = Path(__file__).parent
    return digest({p.name: hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted(root.glob('*.py'))})


def run_predict(input_path: Path, output: Path):
    cases = read_jsonl(input_path)
    unique(cases)
    for c in cases:
        validate_case(c)
    unique_trials(cases)
    predictions = [predict(c) for c in cases]
    # No answer-key path is accepted or read in this operation.
    output.mkdir(parents=True, exist_ok=False)
    write_jsonl(output/'predictions.jsonl', predictions)
    write_json(output/'manifest.json', {
        'status': 'predictions_sealed', 'config': CONFIG, 'config_hash': CONFIG_HASH,
        'code_hash': code_hash(), 'input_file_sha256': hashlib.sha256(input_path.read_bytes()).hexdigest(),
        'predictions_sha256': hashlib.sha256((output/'predictions.jsonl').read_bytes()).hexdigest(),
        'sets': len(predictions), 'answer_key_read': False,
    })
    return predictions


def summarize(predictions: list[dict], keys: list[dict], bootstrap: int = 5000) -> dict:
    if not predictions or not keys:
        raise ValueError('empty predictions or answer key')
    if bootstrap < 100:
        raise ValueError('bootstrap must be at least 100')
    unique(predictions)
    unique_trials(predictions)
    unique(keys)
    truth = {k['set_id']: k['truth'] for k in keys}
    if set(truth) != {p['set_id'] for p in predictions} or any(t not in ('A', 'B') for t in truth.values()):
        raise ValueError('answer key must match predictions exactly and contain A/B truths')
    clusters = defaultdict(list)
    seeds = defaultdict(list)
    for p in predictions:
        if p['config_hash'] != CONFIG_HASH or p['prediction'] not in ('A', 'B'):
            raise ValueError('unsupported config or prediction')
        correct = int(p['prediction'] == truth[p['set_id']])
        clusters[p['cluster_id']].append(correct)
        seeds[p['seed']].append(correct)
    means = [sum(v)/len(v) for _, v in sorted(clusters.items())]
    by_view = {}
    for name in NAMES:
        available = [p for p in predictions if name in p.get('views', {})]
        if not available:
            continue
        decided = [p for p in available if p['views'][name]['pick'] in ('A', 'B')]
        correct = [int(p['views'][name]['pick'] == truth[p['set_id']]) for p in decided]
        by_view[name] = {
            'decided_cases': len(decided), 'decision_coverage': len(decided)/len(predictions),
            'NA_cases': sum(p['views'][name]['delta'] is None for p in available),
            'tied_cases': sum(p['views'][name]['delta'] is not None and abs(p['views'][name]['delta']) <= CONFIG['tie_epsilon'] for p in available),
            'covered_clusters': len({p['cluster_id'] for p in decided}),
            'accuracy_on_decided_cases_only': sum(correct)/len(correct) if correct else None,
        }
    ci = None
    if len(means) >= 2:
        rng = random.Random(20261104)
        samples = sorted(sum(rng.choices(means, k=len(means)))/len(means) for _ in range(bootstrap))
        ci = [samples[int(.025*(bootstrap-1))], samples[int(.975*(bootstrap-1))]]
    return {
        'status': 'descriptive_benchmark_only', 'sets': len(predictions), 'clusters': len(clusters),
        'cluster_equal_weight_accuracy': sum(means)/len(means),
        'raw_accuracy': sum(sum(v) for v in clusters.values())/len(predictions),
        'cluster_bootstrap_percentile_95': ci, 'bootstrap_replicates': bootstrap if ci else 0,
        'by_cluster': {k: {'sets': len(v), 'accuracy': sum(v)/len(v)} for k, v in sorted(clusters.items())},
        'by_seed': {str(k): {'sets': len(v), 'accuracy': sum(v)/len(v)} for k, v in sorted(seeds.items())},
        'final_ties': sum(p['final_tie'] for p in predictions),
        'diagnostic_views': by_view,
        'promotion_verdict': None, 'config_hash': CONFIG_HASH,
    }


def run_score(prediction_dir: Path, key_path: Path, output: Path, bootstrap: int):
    manifest = json.loads((prediction_dir/'manifest.json').read_text())
    pp = prediction_dir/'predictions.jsonl'
    if hashlib.sha256(pp.read_bytes()).hexdigest() != manifest['predictions_sha256']:
        raise ValueError('sealed prediction file hash mismatch')
    if manifest['config_hash'] != CONFIG_HASH:
        raise ValueError('manifest config mismatch')
    result = summarize(read_jsonl(pp), read_jsonl(key_path), bootstrap)
    result['predictions_sha256'] = manifest['predictions_sha256']
    result['answer_key_sha256'] = hashlib.sha256(key_path.read_bytes()).hexdigest()
    output.mkdir(parents=True, exist_ok=False)
    write_json(output/'summary.json', result)
    return result
