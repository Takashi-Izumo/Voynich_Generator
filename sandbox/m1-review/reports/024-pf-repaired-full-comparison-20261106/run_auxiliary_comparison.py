"""Registered supplemental comparison using separate independent audit authority.

No product module or official AUDIT seal is modified. Isolated copies of the
unchanged diagnostic/export code substitute only their release guard. Scoring,
calibration, inputs, masks, contrasts and statistical code are unchanged.
"""
from pathlib import Path
import csv
import hashlib
import json
import sys
import time

from independent_canonical_audit import ROOT,OUT,PLAN,authorized
import run_postprocessing as original_post

REG=ROOT/'sandbox/m1-review/reports/024-pf-repaired-full-comparison-20261106'

def read(p):return json.loads(p.read_text())
def write(p,v):p.write_text(json.dumps(v,ensure_ascii=False,indent=2,allow_nan=False)+'\n')
def table(p,rows):
    with p.open('w',newline='') as f:
        w=csv.DictWriter(f,fieldnames=list(rows[0]),lineterminator='\n');w.writeheader();w.writerows(rows)

def frozen_adapter(name,plan):
    """Compile an isolated exact copy; override only its audited() release guard."""
    source=ROOT/('experiments/pf_generation/'+name+'.py')
    digest=hashlib.sha256(source.read_bytes()).hexdigest()
    assert digest==plan['implementation_sources'][source.relative_to(ROOT).as_posix()]
    ns={'__name__':'experiments.pf_generation._independent_authority_'+name,'__package__':'experiments.pf_generation'}
    exec(compile(source.read_text(),'<isolated frozen '+name+' with independent release authority>','exec'),ns)
    def independent_release(plan_path,generated):
        assert Path(plan_path).resolve()==PLAN.resolve() and Path(generated).resolve()==(OUT/'generated').resolve()
        p,review=authorized()
        return p
    ns['audited']=independent_release
    return ns,digest

def main():
    assert not (OUT/'evaluation').exists() and not (OUT/'anonymous').exists()
    assert read(OUT/'STUDY_STATUS.json')['status']=='FAILED'
    assert not (OUT/'generated/AUDIT.json').exists()
    amendment=read(REG/'AUXILIARY_EXECUTION.json')
    assert amendment['status']=='REGISTERED_INDEPENDENT_AUDIT_AUXILIARY_COMPARISON'
    assert amendment['comparison_plan_hash']==read(PLAN)['plan_hash']
    for item in read(REG/'AUXILIARY_REGISTRATION_MANIFEST.json')['files']:
        b=(REG/item['path']).read_bytes();assert len(b)==item['bytes'] and hashlib.sha256(b).hexdigest()==item['sha256']
    assert amendment['auxiliary_driver_sha256']==hashlib.sha256(Path(__file__).read_bytes()).hexdigest()
    plan,review=authorized();assert amendment['independent_audit_review_sha256']==hashlib.sha256((OUT/'independent-audit-review.json').read_bytes()).hexdigest()
    write(OUT/'AUXILIARY_STATUS.json',dict(status='RUNNING',official_audit='FAIL_PRESERVED',generated_pages=800,planned_predictions=600))
    original_post.historical_base()
    counts={a:0 for a in [*original_post.ARMS,'REFERENCE']};cases=[]
    for entry in read(OUT/'generated/manifest.json')['records']:
        n=read(OUT/'generated'/entry['path']/'PF_GENERATION_FINAL.json')['terminal_precommits']
        counts[entry['arm']]+=n
        if n:cases.append(dict(arm=entry['arm'],bif=entry['bif'],run=entry['run'],terminal_precommits=n))
    assert counts['BASE']==counts['REFERENCE']==0
    write(OUT/'terminal-repair-summary.json',dict(status='PASS',counts_include_discarded_attempts=True,by_arm=counts,cases=cases))
    adapters={}
    for module,command,target in [('diagnostics','summarize','diagnostics'),('evaluation','export','anonymous')]:
        ns,digest=frozen_adapter(module,plan);t=time.monotonic()
        ns[command](PLAN,OUT/'generated',OUT/target)
        adapters[module]=dict(frozen_source_sha256=digest,only_private_release_guard_substituted=True,
            product_module_modified=False,wall_seconds=time.monotonic()-t)
        print('AUXILIARY',command,'COMPLETE',flush=True)
    write(OUT/'auxiliary-authority-adapters.json',dict(status='PASS',adapters=adapters,
        release_authority_sha256=hashlib.sha256((OUT/'independent-audit-review.json').read_bytes()).hexdigest()))
    authorized()
    from experiments.pf_generation.evaluation import evaluate
    import judges.v03.artifacts as artifacts
    import judges.v03.statistics as stats
    predict0,score0=artifacts.predict_file,stats.score;events=[]
    def predict(*a,**kw):
        result=predict0(*a,**kw);n=len((Path(a[1])/'predictions.jsonl').read_text().splitlines());assert n==200
        events.append(dict(action='predictions_sealed',arm=Path(a[1]).name,count=n))
        print('AUXILIARY PREDICTIONS',sum(e['count'] for e in events if e['action']=='predictions_sealed'),'/600',flush=True)
        return result
    def score(*a,**kw):
        n=sum(e['count'] for e in events if e['action']=='predictions_sealed');assert n==600
        events.append(dict(action='score_key_read',arm=Path(a[2]).name,sealed_predictions=n));return score0(*a,**kw)
    artifacts.predict_file,stats.score=predict,score
    try:comparisons=evaluate(PLAN,OUT/'anonymous',original_post.MODELS,OUT/'evaluation',jobs=4,bootstrap=10000)
    finally:artifacts.predict_file,stats.score=predict0,score0
    write(OUT/'prediction-order.json',dict(status='PASS',events=events,all_600_predictions_before_scoring=True))
    summaries={a:read(OUT/'evaluation/scores'/a/'summary.json') for a in original_post.ARMS}
    original_post.independently_recompute(summaries,comparisons)
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
                distance_change_lower95=ci[0],distance_change_upper95=ci[1],paired_cases=r['paired_cases'],paired_bifolia=r['paired_bifolia'],direction_reversal=r.get('direction_reversal')))
    table(OUT/'summary/all-paired.csv',paired)
    selected=[*original_post.PRIMARY,'J24.PROTO','ATOM.W2.CAL','ATOM.BODY.CAL','ATOM.LINE_END.CAL','ATOM.PLANT_END.CAL','J19.CAL','J20.CAL','J25.CAL']
    short={a:{v:s['views'][v] for v in selected if v in s['views']} for a,s in summaries.items()}
    authorized()
    result=dict(status='COMPLETED_DESCRIPTIVE_COMPARISON_VIA_INDEPENDENT_NATIVE_SCOPE_REVIEW',plan_hash=plan['plan_hash'],
        source_head='43a6895',generated_pages=800,comparison_pages=600,reference_pages=200,independent_bifolia=20,
        primary='J24.CAL',local_primary='ATOM.PARA_END.CAL',arms=short,comparisons=comparisons,
        official_audit_status='FAIL_SCOPE_ASSUMPTION_PRESERVED',official_AUDIT_seal_created=False,
        independent_audit_status=review['status'],independent_audit_review_sha256=hashlib.sha256((OUT/'independent-audit-review.json').read_bytes()).hexdigest(),
        capability_status='CAPABILITY_NOT_VERIFIED_UNCHANGED',new_measurement_design='UNIMPLEMENTED',
        inference='descriptive_development_reused_bifolia_frozen_models_auxiliary_release',promotion=None,equivalence_claim=False)
    write(OUT/'summary/RESULTS.json',result)
    write(OUT/'AUXILIARY_STATUS.json',dict(status=result['status'],generated_pages=800,predicted_cases=600,
        official_audit_status=result['official_audit_status'],independent_audit_status=review['status'],promotion=None))
    print('AUXILIARY COMPARISON COMPLETE; OFFICIAL AUDIT FAIL PRESERVED',flush=True)
    print(json.dumps({a:{v:s[v]['macro_expected_game_accuracy'] for v in original_post.PRIMARY} for a,s in short.items()}),flush=True)

if __name__=='__main__':main()
