import gzip,json
from pathlib import Path
import pandas as pd, numpy as np
RUNS=[92001,92002,92003,92004,92005,92006,92007,92008,92009,92011]
P=Path('/mnt/data/v22_2_judge_parent');C=Path('/mnt/data/v22_2_judge_child')
PM='HerbalA_v22r_W2B2';CM='HerbalA_v22_2'
# bifs from dirs
rows=[]
for run in RUNS:
  pd0=P/f'run{run}'/PM; cd0=C/f'run{run}'/CM
  for bdir in sorted(pd0.iterdir()):
    bif=bdir.name.replace('_',':')
    qdir=cd0/bdir.name
    def load(fp):
      with gzip.open(fp,'rt') as f:return [json.loads(x) for x in f]
    a=load(bdir/'requests.jsonl.gz'); b=load(qdir/'requests.jsonl.gz')
    same_n=len(a)==len(b)
    n=min(len(a),len(b)); keyeq=bankeq=draw_eq=outcome_eq=prob_eq=0; after_changed_bankdiff=0; after_changed_probdiff=0; scope=0; changed=0
    first_changed_idx=None
    for i in range(n):
      x,y=a[i],b[i]
      keys=('page','locus','segment_id','word_index','proposal_id')
      ke=all(x.get(k)==y.get(k) for k in keys); keyeq+=ke
      be=x.get('candidates')==y.get('candidates'); bankeq+=be
      de=x.get('proposal_draws')==y.get('proposal_draws'); draw_eq+=de
      oe=x.get('outcome')==y.get('outcome'); outcome_eq+=oe
      px=np.array(x.get('probabilities') or [],float); py=np.array(y.get('probabilities') or [],float)
      pe=(len(px)==len(py) and (len(px)==0 or np.allclose(px,py,rtol=0,atol=1e-15))); prob_eq+=pe
      if y.get('v22_2_f1lf_router_off_scope'):scope+=1
      if y.get('v22_2_changed'):
        changed+=1
        if first_changed_idx is None:first_changed_idx=i
      if first_changed_idx is not None and i>first_changed_idx:
        after_changed_bankdiff += int(not be)
        after_changed_probdiff += int(not pe)
    rows.append(dict(run=run,bif=bif,parent_requests=len(a),child_requests=len(b),same_n=same_n,key_equal=keyeq,bank_equal=bankeq,draw_equal=draw_eq,outcome_equal=outcome_eq,prob_equal=prob_eq,scope_requests=scope,changed_scope=changed,after_changed_bankdiff=after_changed_bankdiff,after_changed_probdiff=after_changed_probdiff))
D=pd.DataFrame(rows);D.to_csv('/mnt/data/v22_2_judge_results/16_request_clock_audit.csv',index=False)
print(D[['same_n']].all())
print('cases',len(D),'all same n',D.same_n.all())
print('total req',D.parent_requests.sum(),D.child_requests.sum())
print('key eq',D.key_equal.sum(),'of',D.parent_requests.sum())
print('bank eq',D.bank_equal.sum(),'draw eq',D.draw_equal.sum(),'outcome eq',D.outcome_equal.sum(),'prob eq',D.prob_equal.sum())
print('scope',D.scope_requests.sum(),'changed',D.changed_scope.sum())
print('after change bankdiff',D.after_changed_bankdiff.sum(),'probdiff',D.after_changed_probdiff.sum())
print('cases probdiff', (D.prob_equal<D.parent_requests).sum(),'bankdiff',(D.bank_equal<D.parent_requests).sum())
