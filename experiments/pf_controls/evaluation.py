"""Fixed CAL prediction followed by separately keyed, per-channel capability gates."""
from __future__ import annotations

from pathlib import Path
import math

from judges.v03.protocol import digest as jury_digest, read_jsonl
from judges.v03.statistics import aggregate
from . import FAMILIES, DIRECTIONS
from .common import file_hash, read, require, seal, write_json
from .pipeline import verify_export


def channel_measurement(prediction, truth, channel):
    a,b=prediction['A'],prediction['B']
    delta=a-b if a is not None and b is not None else None
    state='NA' if delta is None else 'TIE' if abs(delta)<=1e-12 else 'DECIDED'
    return dict(view=channel,status=state,correct=None if state!='DECIDED' else int(('A' if delta>0 else 'B')==truth))


def gate(measurements, realized, cohort, config):
    require(len(measurements)==len(realized)==cohort and cohort>0,'Capability cohort coverage mismatch')
    stats=aggregate(measurements,config['cluster_bootstrap_replicates'])
    manipulation=sum(realized)/cohort
    interval=stats['expected_game_cluster_bootstrap_95']
    valid=(stats['comparable_bifolia']>=config['minimum_contributing_bifolia']
           and stats['comparable_coverage']>=config['minimum_comparable_page_fraction']
           and stats['macro_expected_game_accuracy'] is not None
           and stats['macro_expected_game_accuracy']>=config['minimum_macro_expected_accuracy']
           and interval is not None and interval[0]>config['cluster_bootstrap_95_lower_strictly_above'])
    status=('MANIPULATION_NOT_REALIZED' if manipulation<config['minimum_realized_target_manipulation_fraction']
            else 'PASS' if valid else 'INSUFFICIENT_CAPABILITY')
    return dict(status=status,planned_eligible_pages=cohort,realized_target_manipulation_fraction=manipulation,
                expected_accuracy_ties_half=True,**stats)


def evaluate(plan,generated,exported,models,output,jobs=1):
    from judges.v03.calibration import load_models
    from judges.v03.artifacts import predict_file
    from judges.v03.statistics import score
    p,m,exports=verify_export(plan,generated,exported)
    payload,_=load_models(models)
    require(jury_digest(payload)==p['model_set_hash'],'Frozen CAL model set mismatch; no refit/fallback')
    require(p['kind']=='controls','Capability evaluation requires the preregistered twenty-leaf control plan')
    output=Path(output);output.mkdir(parents=True,exist_ok=False)
    predictions={}
    # Every prediction is sealed before scoring opens any answer key.
    for label,data in exports.items():
        if not data['inputs']:
            continue
        opaque=jury_digest(['blind-prediction',m['sha256'],label])[:24]
        target=output/'predictions'/opaque
        predict_file(Path(exported)/label/'inputs.jsonl',target,models,primary='J24.CAL',jobs=jobs)
        predictions[label]=str(target)
    sealed={label:dict(path=path,manifest_sha256=file_hash(Path(path)/'manifest.json')) for label,path in predictions.items()}
    write_json(output/'PREDICTIONS.json',seal(dict(export_sha256=m['sha256'],model_set_hash=p['model_set_hash'],all_predictions_complete=True,
                                               predictions=sealed,keys_used_to_score=False)))
    results={}
    for label,data in exports.items():
        if label not in predictions:
            continue
        target=Path(predictions[label])
        require(file_hash(target/'manifest.json')==sealed[label]['manifest_sha256'],
                'Prediction changed after all-predictions seal')
        pm=read(target/'manifest.json')
        require(pm['model_set_hash']==p['model_set_hash'] and pm['extractor_hash']==p['extractor_hash']
                and pm['protocol_hash']==p['protocol_hash'] and pm['input_file_sha256']==file_hash(Path(exported)/label/'inputs.jsonl')
                and pm['channels_sha256']==file_hash(target/'channels.jsonl')
                and pm['predictions_sha256']==file_hash(target/'predictions.jsonl')
                and pm['answer_key_read'] is False,'Prediction seal mismatch')
        # Standard reports keep every other atom/panel and PROTO, without gating on them.
        score(target,Path(exported)/label/'answer_key.jsonl',output/'scores'/label,10000)
        rows=read_jsonl(target/'predictions.jsonl');details=read_jsonl(target/'channels.jsonl')
        keys={r['set_id']:r['truth'] for r in read_jsonl(Path(exported)/label/'answer_key.jsonl')}
        channels={r['set_id']:r['channels']['CAL'] for r in details}
        require(len(keys)==len(rows)==len(channels) and set(keys)=={r['set_id'] for r in rows}==set(channels),
                'Prediction/key/channel coverage mismatch')
        lane,direction=label.split('__');channel='ATOM.PARA_END/'+lane
        measurements=[]
        for row in rows:
            measurements.append(dict(set_id=row['set_id'],cluster_id=row['cluster_id'],seed=row['seed'],target_slot=3,
                                **channel_measurement(channels[row['set_id']][channel],keys[row['set_id']],channel)))
        results[label]=gate(measurements,[d['target_feature_realized'] for d in data['diagnostics']],
                            len(p['eligible_cohorts'][lane]),p['contract']['gate'])
        results[label]['used_for_gate']=direction=='far'
        results[label]['all_channel_facts']=str(target/'channels.jsonl')
    channel_results={}
    for lane in FAMILIES:
        channel_results['ATOM.PARA_END/'+lane]=results.get(lane+'__far',dict(status='INSUFFICIENT_CAPABILITY'))
    passed=all(r['status']=='PASS' for r in channel_results.values())
    review=seal(dict(schema_version=1,status='PASS' if passed else 'NOT_PASSED',
                     comparison_plan_hash=p['contract']['comparison_plan_hash'],model_set_hash=p['model_set_hash'],
                     control_plan_hash=p['sha256'],export_hash=m['sha256'],
                     channel_results=channel_results,diagnostics=results,
                     all_predictions_before_scoring=True,full_comparison_started=False,promotion=None,
                     independent_review_required=True))
    write_json(output/'CAPABILITY_RESULTS.json',review)
    # This is results, not an independent CAPABILITY_REVIEW approval for the orchestrator.
    return review
