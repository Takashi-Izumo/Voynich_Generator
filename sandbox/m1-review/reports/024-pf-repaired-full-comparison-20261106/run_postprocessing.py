"""Audit all800 new pages, seal all600 predictions, then score frozen CAL."""
from pathlib import Path
from collections import defaultdict
import csv
import json
import math
import random
import subprocess
import sys
import time

ROOT=Path('/workspace/voynich-results/m1-v2-independent-20261105/checkout')
OUT=Path('/workspace/voynich-results/pf-repaired-full-comparison-20261106')
PLAN=ROOT/'sandbox/m1-review/reports/024-pf-repaired-full-comparison-20261106/full-plan/plan.json'
MODELS=Path('/workspace/voynich-results/m1-review-received-20261105/cal-models')
ARMS=['BASE','PF_GATE','PF_GATE_LENGTH']
PRIMARY=['J24.CAL','ATOM.PARA_END.CAL']
sys.path.insert(0,str(ROOT))

def read(p):return json.loads(Path(p).read_text())
def write(p,v):Path(p).write_text(json.dumps(v,ensure_ascii=False,indent=2,allow_nan=False)+'\n')
def table(path,rows):
    with path.open('w',newline='') as f:
        w=csv.DictWriter(f,fieldnames=list(rows[0]),lineterminator='\n');w.writeheader();w.writerows(rows)
def run(name,args):
    t=time.monotonic()
    with (OUT/(name+'.log')).open('w') as f:r=subprocess.run([sys.executable,*map(str,args)],cwd=ROOT,stdout=f,stderr=subprocess.STDOUT)
    v=dict(name=name,command=[sys.executable,*map(str,args)],returncode=r.returncode,wall_seconds=time.monotonic()-t)
    write(OUT/(name+'.result.json'),v);print(json.dumps(v),flush=True);assert r.returncode==0,name

def historical_base():
    from experiments.pf_generation.audit import semantic_case
    from experiments.pf_generation.common import file_hash,digest
    old=Path('/workspace/voynich-results/m1-full-comparison-20261105/generated')
    prior=read(old/'manifest.json')['records'];lookup={(r['arm'],r['bif'],r['run']):r for r in prior}
    current=read(OUT/'generated/manifest.json')['records'];baseline=[r for r in current if r['arm']=='BASE']
    assert len(baseline)==200
    for i,r in enumerate(baseline):
        p=lookup[r['arm'],r['bif'],r['run']]
        assert semantic_case(OUT/'generated'/r['path'])==semantic_case(old/p['path']),(r['bif'],r['run'])
        if (i+1)%25==0:print('HISTORICAL BASE',i+1,'/200',flush=True)
    write(OUT/'historical-base-check.json',dict(status='PASS',cases=200,semantic_state_actual_rng_exact=True,
        base_records_sha256=digest(sorted(baseline,key=lambda r:(r['bif'],r['run']))),prior_manifest_sha256=file_hash(old/'manifest.json')))

def independently_recompute(summaries,comparisons):
    from judges.v03.protocol import read_jsonl
    all_groups={};checked=0;ci_count=0;pair_count=0
    def interval(values):
        if len(values)<2:return None
        rng=random.Random(20261104)
        draws=sorted(math.fsum(rng.choices(values,k=len(values)))/len(values) for _ in range(10000))
        return [draws[int(.025*9999)],draws[int(.975*9999)]] if len(values)>1 else None
    for arm in ARMS:
        groups=defaultdict(list)
        for row in read_jsonl(OUT/'evaluation/scores'/arm/'measurements.jsonl'):groups[row['view']].append(row)
        all_groups[arm]=groups
        assert set(groups)==set(summaries[arm]['views'])
        for view,rows in groups.items():
            by=defaultdict(list);na=ties=correct=decided=0
            for row in rows:
                if row['status']=='NA':na+=1;continue
                if row['status']=='TIE':value=.5;ties+=1
                else:value=row['correct'];correct+=value;decided+=1
                by[row['cluster_id']].append(value)
            means=[math.fsum(v)/len(v) for _,v in sorted(by.items())]
            accuracy=math.fsum(means)/len(means) if means else None
            metrics=summaries[arm]['views'][view]
            assert accuracy==metrics['macro_expected_game_accuracy'] and len(rows)==metrics['trials']==200
            assert (na,ties,correct,decided,len(by))==(metrics['NA'],metrics['ties'],metrics['correct'],metrics['decided'],metrics['comparable_bifolia'])
            if view in PRIMARY:
                assert interval(means)==metrics['expected_game_cluster_bootstrap_95'];ci_count+=1
            checked+=1
    for left,right in [('BASE','PF_GATE'),('PF_GATE','PF_GATE_LENGTH')]:
        label=left+'__'+right
        for view in PRIMARY:
            a={r['set_id']:r for r in all_groups[left][view]};b={r['set_id']:r for r in all_groups[right][view]}
            assert set(a)==set(b)
            by=defaultdict(list)
            for key in a:
                x,y=a[key],b[key]
                if x['status']=='NA' or y['status']=='NA':continue
                val=lambda r:.5 if r['status']=='TIE' else r['correct']
                by[x['cluster_id']].append((val(x),val(y)))
            pairs=[(math.fsum(x for x,y in v)/len(v),math.fsum(y for x,y in v)/len(v)) for _,v in sorted(by.items())]
            av=math.fsum(x for x,y in pairs)/len(pairs);bv=math.fsum(y for x,y in pairs)/len(pairs)
            result=comparisons[label][view]
            assert (av,bv)==(result['left_rate'],result['right_rate'])
            assert result['distance_change']==abs(bv-.5)-abs(av-.5)
            assert result['paired_cases']==sum(len(v) for v in by.values())
            rng=random.Random(20261104);draws=[]
            for _ in range(10000):
                sample=rng.choices(pairs,k=len(pairs))
                x=math.fsum(x for x,y in sample)/len(sample);y=math.fsum(y for x,y in sample)/len(sample)
                draws.append(abs(y-.5)-abs(x-.5))
            draws.sort();assert result['cluster_bootstrap_95']==[draws[int(.025*9999)],draws[int(.975*9999)]]
            pair_count+=1
    write(OUT/'independent-statistics.json',dict(status='PASS',all_view_arm_rates_checked=checked,
        primary_rate_intervals_checked=ci_count,primary_paired_distance_intervals_checked=pair_count,
        bootstrap_replicates=10000,seed=20261104,NA_not_replaced_by_tie=True))

def main():
    status=read(OUT/'generated/STATUS.json');assert status['status']=='GENERATED_NOT_AUDITED' and status['completed_cases']==800
    run('audit',['-m','experiments.pf_generation','audit','--plan',PLAN,'--generated',OUT/'generated','--output',OUT/'audit'])
    report=read(OUT/'audit/report.json')
    assert report['status']=='PASS' and report['cases']==600 and report['base_reference_checked'] and report['base_reference_main_rng_checked'] and report['trace_coverage_checked']
    repair_counts={a:0 for a in [*ARMS,'REFERENCE']};repair_cases=[]
    for entry in read(OUT/'generated/manifest.json')['records']:
        n=read(OUT/'generated'/entry['path']/'PF_GENERATION_FINAL.json')['terminal_precommits']
        repair_counts[entry['arm']]+=n
        if n:repair_cases.append(dict(arm=entry['arm'],bif=entry['bif'],run=entry['run'],terminal_precommits=n))
    assert repair_counts['BASE']==repair_counts['REFERENCE']==0
    write(OUT/'terminal-repair-summary.json',dict(status='PASS',counts_include_discarded_attempts=True,by_arm=repair_counts,cases=repair_cases))
    historical_base()
    for command,target in [('summarize','diagnostics'),('export','anonymous')]:
        run(target,['-m','experiments.pf_generation',command,'--plan',PLAN,'--generated',OUT/'generated','--output',OUT/target])
    from experiments.pf_generation.evaluation import evaluate
    import judges.v03.artifacts as artifacts
    import judges.v03.statistics as stats
    original_predict,original_score=artifacts.predict_file,stats.score;events=[]
    def predict(*a,**kw):
        result=original_predict(*a,**kw);count=len((Path(a[1])/'predictions.jsonl').read_text().splitlines());assert count==200
        events.append(dict(action='predictions_sealed',arm=Path(a[1]).name,count=count))
        print('PREDICTIONS',sum(e['count'] for e in events if e['action']=='predictions_sealed'),'/600',flush=True)
        return result
    def score(*a,**kw):
        count=sum(e['count'] for e in events if e['action']=='predictions_sealed');assert count==600
        events.append(dict(action='score_key_read',arm=Path(a[2]).name,sealed_predictions=count));return original_score(*a,**kw)
    artifacts.predict_file,stats.score=predict,score
    try:comparisons=evaluate(PLAN,OUT/'anonymous',MODELS,OUT/'evaluation',jobs=4,bootstrap=10000)
    finally:artifacts.predict_file,stats.score=original_predict,original_score
    write(OUT/'prediction-order.json',dict(status='PASS',events=events,all_600_predictions_before_scoring=True))
    summaries={a:read(OUT/'evaluation/scores'/a/'summary.json') for a in ARMS}
    independently_recompute(summaries,comparisons)
    rows=[]
    for view in sorted(set.intersection(*(set(s['views']) for s in summaries.values()))):
        for arm,s in summaries.items():
            r=s['views'][view];ci=r['expected_game_cluster_bootstrap_95'] or [None,None]
            rows.append(dict(view=view,arm=arm,rate=r['macro_expected_game_accuracy'],lower95=ci[0],upper95=ci[1],
                comparable_bifolia=r['comparable_bifolia'],trials=r['trials'],NA=r['NA'],ties=r['ties'],comparable_fraction=r['comparable_coverage']))
    (OUT/'summary').mkdir();table(OUT/'summary/all-views.csv',rows)
    paired=[]
    for label,views in comparisons.items():
        scored=read(OUT/'evaluation/paired'/label/'comparison.json')['views']
        for view,r in views.items():
            ci=r.get('cluster_bootstrap_95') or [None,None]
            signed_ci=scored[view]['paired_expected_game'].get('cluster_bootstrap_95') or [None,None]
            paired.append(dict(contrast=label,view=view,left_rate=r.get('left_rate'),right_rate=r.get('right_rate'),
                signed_rate_change=r.get('signed_rate_change'),rate_change_lower95=signed_ci[0],rate_change_upper95=signed_ci[1],
                left_distance=r.get('left_distance'),right_distance=r.get('right_distance'),distance_change=r.get('distance_change'),
                distance_change_lower95=ci[0],distance_change_upper95=ci[1],paired_cases=r['paired_cases'],
                paired_bifolia=r['paired_bifolia'],direction_reversal=r.get('direction_reversal')))
    table(OUT/'summary/all-paired.csv',paired)
    selected=[*PRIMARY,'J24.PROTO','ATOM.W2.CAL','ATOM.BODY.CAL','ATOM.LINE_END.CAL','ATOM.PLANT_END.CAL','J19.CAL','J20.CAL','J25.CAL']
    short={a:{v:s['views'][v] for v in selected if v in s['views']} for a,s in summaries.items()}
    write(OUT/'summary/RESULTS.json',dict(status='COMPLETED_DESCRIPTIVE_MAIN',plan_hash=status['plan_hash'],
        source_head='43a6895',generated_pages=800,comparison_pages=600,reference_pages=200,independent_bifolia=20,
        primary='J24.CAL',local_primary='ATOM.PARA_END.CAL',arms=short,comparisons=comparisons,
        capability_status='CAPABILITY_NOT_VERIFIED_UNCHANGED',new_measurement_design='UNIMPLEMENTED',
        inference='development_reused_bifolia_frozen_models',promotion=None,equivalence_claim=False))
    print('COMPLETE:800 new pages,600 blind predictions,200 exact references,independent statistical recomputation PASS',flush=True)
    print(json.dumps({a:{v:s[v]['macro_expected_game_accuracy'] for v in PRIMARY} for a,s in short.items()}),flush=True)

if __name__=='__main__':main()
