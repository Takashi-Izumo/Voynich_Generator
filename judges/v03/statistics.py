from __future__ import annotations

from collections import defaultdict
import csv
import math
from pathlib import Path
import random
from .protocol import DEFAULT, PROTOCOL_HASH, read_json, read_jsonl, write_json, write_jsonl, file_hash
from .schema import finite_tree, validate_prediction


def interval(values, bootstrap):
    if len(values)<2:return None
    rng=random.Random(DEFAULT['statistics']['bootstrap_rng_seed'])
    samples=sorted(math.fsum(rng.choices(values,k=len(values)))/len(values) for _ in range(bootstrap))
    return [samples[int(.025*(bootstrap-1))],samples[int(.975*(bootstrap-1))]]


def aggregate(rows, bootstrap=10000):
    if not rows:raise ValueError('empty measurement rows')
    if type(bootstrap) is not int or bootstrap<100:raise ValueError('bootstrap must be >=100')
    by=defaultdict(list)
    for r in rows:
        if r['status'] not in ['DECIDED','TIE','NA']:raise ValueError('invalid measurement state')
        if r['status']=='DECIDED' and (type(r['correct']) is not int or r['correct'] not in [0,1]):raise ValueError('invalid correctness')
        if r['status']!='DECIDED' and r['correct'] is not None:raise ValueError('TIE/NA are not observed correctness')
        by[r['cluster_id']].append(r)
    macro_d=[];macro_g=[];counts={'DECIDED':0,'TIE':0,'NA':0};correct=0;detail={}
    for cluster,rr in sorted(by.items()):
        ds=[r for r in rr if r['status']=='DECIDED'];nt=sum(r['status']=='TIE' for r in rr)
        z=sum(r['correct'] for r in ds);correct+=z
        pd=z/len(ds) if ds else None
        pg=(z+.5*nt)/(len(ds)+nt) if ds or nt else None
        if pd is not None:macro_d.append(pd)
        if pg is not None:macro_g.append(pg)
        for r in rr:counts[r['status']]+=1
        detail[cluster]={'trials':len(rr),'decided':len(ds),'ties':nt,'NA':len(rr)-len(ds)-nt,
            'correct':z,'decided_accuracy':pd,'expected_game_accuracy':pg}
    n=len(rows);nd=counts['DECIDED'];nc=nd+counts['TIE']
    return {'trials':n,'bifolia':len(by),'decided':nd,'ties':counts['TIE'],'NA':counts['NA'],'correct':correct,
        'decision_coverage':nd/n,'comparable_coverage':nc/n,'NA_fraction':counts['NA']/n,
        'decided_bifolia':len(macro_d),'comparable_bifolia':len(macro_g),
        'macro_decided_accuracy':math.fsum(macro_d)/len(macro_d) if macro_d else None,
        'pooled_decided_accuracy':correct/nd if nd else None,
        'macro_expected_game_accuracy':math.fsum(macro_g)/len(macro_g) if macro_g else None,
        'pooled_expected_game_accuracy':(correct+.5*counts['TIE'])/nc if nc else None,
        'decided_cluster_bootstrap_95':interval(macro_d,bootstrap),
        'expected_game_cluster_bootstrap_95':interval(macro_g,bootstrap),
        'bootstrap_replicates':bootstrap,'interval_scope':'available_bifolia_and_frozen_models_only',
        'by_bifolium':detail}


def write_csv(path, rows):
    if not rows:return
    with Path(path).open('w',newline='') as f:
        w=csv.DictWriter(f,fieldnames=list(rows[0]));w.writeheader();w.writerows(rows)


def score(prediction_dir, key_path, output, bootstrap=10000):
    prediction_dir=Path(prediction_dir);output=Path(output)
    m=read_json(prediction_dir/'manifest.json')
    if m['protocol_hash']!=PROTOCOL_HASH or m['predictions_sha256']!=file_hash(prediction_dir/'predictions.jsonl'):
        raise ValueError('sealed prediction/protocol mismatch')
    if m['channels_sha256']!=file_hash(prediction_dir/'channels.jsonl'):
        raise ValueError('sealed channel facts were changed')
    ps=read_jsonl(prediction_dir/'predictions.jsonl');kk=read_jsonl(key_path)
    if any(set(k)!={'set_id','truth'} or k['truth'] not in ['A','B'] for k in kk):raise ValueError('invalid key fields/truth')
    keys={k['set_id']:k['truth'] for k in kk}
    if len(keys)!=len(kk) or set(keys)!={p['set_id'] for p in ps}:raise ValueError('key must match sealed cases exactly')
    if len({p['set_id'] for p in ps})!=len(ps) or len({(p['cluster_id'],p['target_slot'],p['seed']) for p in ps})!=len(ps):raise ValueError('duplicate sealed case/trial')
    records=[];trials=[]
    for p in ps:
        validate_prediction(p)
        if p['protocol_hash']!=PROTOCOL_HASH:raise ValueError('prediction config mismatch')
        truth=keys[p['set_id']]
        for name,v in p['views'].items():
            if v['status']=='DECIDED' and v['pick'] not in ['A','B']:raise ValueError('invalid decided prediction')
            if v['status']!='DECIDED' and v['pick'] is not None:raise ValueError('TIE/NA cannot hide a decision')
            correct=int(v['pick']==truth) if v['status']=='DECIDED' else None
            records.append({'set_id':p['set_id'],'cluster_id':p['cluster_id'],'seed':p['seed'],'target_slot':p['target_slot'],
                'view':name,'status':v['status'],'correct':correct,'reason':v['reason']})
        trials.append({'set_id':p['set_id'],'cluster_id':p['cluster_id'],'seed':p['seed'],'target_slot':p['target_slot'],
            'template_hash':p['template_hash'],'model_hash':p['model_hash'],'primary':p['primary'],
            'genuine_hash':m['candidate_hashes'][p['set_id']][truth]})
    names=sorted({r['view'] for r in records});views={}
    for name in names:views[name]=aggregate([r for r in records if r['view']==name],bootstrap)
    primaries={p['primary'] for p in ps}
    if len(primaries)!=1:raise ValueError('mixed primary classifiers')
    primary=next(iter(primaries))
    result={'status':'development_reused_not_fresh_confirmation','protocol_hash':PROTOCOL_HASH,
        'primary':primary,'primary_summary':views[primary],'views':views,'promotion_verdict':None,
        'predictions_sha256':m['predictions_sha256'],'answer_key_sha256':file_hash(key_path),
        'input_profile':m['input_profile'],'extractor_hash':m['extractor_hash'],'model_set_hash':m['model_set_hash']}
    output.mkdir(parents=True,exist_ok=False)
    write_json(output/'summary.json',result);write_jsonl(output/'measurements.jsonl',records);write_jsonl(output/'trials.jsonl',trials)
    flat=[{'view':name,**{k:v for k,v in s.items() if k not in ['by_bifolium','decided_cluster_bootstrap_95','expected_game_cluster_bootstrap_95']}} for name,s in views.items()]
    write_csv(output/'by_scope.csv',flat)
    write_csv(output/'by_bifolium.csv',[{'view':name,'cluster_id':b,**v} for name,s in views.items() for b,v in s['by_bifolium'].items()])
    write_csv(output/'coverage.csv',[{k:r[k] for k in ['view','trials','bifolia','decided','ties','NA','decision_coverage','comparable_coverage','decided_bifolia','comparable_bifolia']} for r in flat])
    write_json(output/'manifest.json',{'summary_sha256':file_hash(output/'summary.json'),'measurements_sha256':file_hash(output/'measurements.jsonl'),'trials_sha256':file_hash(output/'trials.jsonl')})
    return result


def compare_scores(left,right,output,bootstrap=10000):
    paths=[Path(left),Path(right)]; summaries=[];trial_maps=[];data=[]
    for path in paths:
        m=read_json(path/'manifest.json')
        for filename,key in [('summary.json','summary_sha256'),('measurements.jsonl','measurements_sha256'),('trials.jsonl','trials_sha256')]:
            if file_hash(path/filename)!=m[key]:raise ValueError('score artifacts were changed')
        summaries.append(read_json(path/'summary.json'))
        trial_maps.append({r['set_id']:r for r in read_jsonl(path/'trials.jsonl')})
        data.append({(r['set_id'],r['view']):r for r in read_jsonl(path/'measurements.jsonl')})
    if set(trial_maps[0])!=set(trial_maps[1]):raise ValueError('paired trials differ')
    for k,a in trial_maps[0].items():
        if a!=trial_maps[1][k]:raise ValueError('paired template, genuine face, primary or model differs: '+k)
    for k in ['protocol_hash','input_profile','extractor_hash','primary','model_set_hash']:
        if summaries[0][k]!=summaries[1][k]:raise ValueError('comparison protocols/models differ: '+k)
    result={}
    for view in sorted(set(summaries[0]['views'])&set(summaries[1]['views'])):
        pairs=[(data[0][k,view],data[1][k,view]) for k in trial_maps[0]]
        entry={'left':summaries[0]['views'][view],'right':summaries[1]['views'][view]}
        for label,allowed in [('expected_game',['DECIDED','TIE']),('decided',['DECIDED'])]:
            groups=defaultdict(list)
            for a,b in pairs:
                if a['status'] in allowed and b['status'] in allowed:
                    value=lambda r:.5 if r['status']=='TIE' else r['correct']
                    groups[a['cluster_id']].append(value(b)-value(a))
            means=[math.fsum(v)/len(v) for _,v in sorted(groups.items())]
            entry['paired_'+label]={'cases':sum(map(len,groups.values())),'bifolia':len(groups),
                'right_minus_left':math.fsum(means)/len(means) if means else None,'cluster_bootstrap_95':interval(means,bootstrap)}
        entry['availability_transitions']={f'{sa}/{sb}':sum(a['status']==sa and b['status']==sb for a,b in pairs) for sa in ['DECIDED','TIE','NA'] for sb in ['DECIDED','TIE','NA']}
        result[view]=entry
    output=Path(output);output.mkdir(parents=True,exist_ok=False)
    payload={'protocol_hash':PROTOCOL_HASH,'primary':summaries[0]['primary'],'views':result,'promotion_verdict':None}
    write_json(output/'comparison.json',payload)
    return payload
