from __future__ import annotations
import json
from pathlib import Path
import pandas as pd

ROOT=Path(__file__).resolve().parents[1]
SELF=ROOT/'validation/paragraph_h1_running/VALIDATION.json'
J=ROOT/'validation/v22r_fresh200_judge'
checks={}
s=json.loads(SELF.read_text(encoding='utf-8'))
checks['prejudge_selftest_pass']=s.get('status')=='PASS'
d=json.loads((J/'DECISION.json').read_text(encoding='utf-8'))
checks['fresh_judge_pass_with_residual']=d.get('status')=='PASS_WITH_RESIDUAL'
checks['all_minimum_promotion_conditions']=bool(d.get('promotion_conditions',{}).get('all_minimum_conditions'))
mech=d.get('mechanical',{})
checks['fresh200_packing']=bool(mech.get('packing_pass'))
checks['fresh200_support_zero']=int(mech.get('support_violations',-1))==0
checks['fresh200_invalid_zero']=int(mech.get('invalid_rows',-1))==0
checks['fresh200_h1_only']=bool(mech.get('h1_only_all'))
checks['fresh200_route_frozen']=bool(mech.get('route_state_equal_all'))
checks['fresh200_parent_rng_frozen']=bool(mech.get('parent_rng_untouched_all'))
checks['combined_chance_inside']=bool(d.get('promotion_conditions',{}).get('combined_chance_inside'))
checks['h1h2_improved']=bool(d.get('promotion_conditions',{}).get('h1h2_improved_signed_margin'))
checks['bigram_residual_shrunk']=bool(d.get('promotion_conditions',{}).get('bigram_residual_shrunk_signed_margin'))
checks['trigram_not_worse']=bool(d.get('promotion_conditions',{}).get('trigram_not_worse_signed_margin'))
sp=pd.read_csv(J/'SPECIALIZED_PARENT_CHILD.csv')
term=sp.loc[sp.judge.eq('terminal')].iloc[0]
checks['terminal_unchanged_from_parent']=float(term.mean_leaf_delta)==0.0
out={'model_id':'HerbalA-v22r','status':'PASS' if all(checks.values()) else 'FAIL','checks':checks,'judge_status':d.get('status'),'fresh_seeds':d.get('fresh_seeds')}
print(json.dumps(out,ensure_ascii=False,indent=2))
if out['status']!='PASS': raise SystemExit(1)
