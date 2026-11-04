from __future__ import annotations
import json
from pathlib import Path
import pandas as pd

ROOT=Path(__file__).resolve().parents[1]
PKG=ROOT.parent
checks={}

version=json.loads((PKG/'VERSION.json').read_text(encoding='utf-8'))
cfg=json.loads((ROOT/'parameters/W2_B2_CONFIG.json').read_text(encoding='utf-8'))
status=json.loads((ROOT/'MODEL_STATUS_W2_B2.json').read_text(encoding='utf-8'))
rep=json.loads((ROOT/'validation/w2_b2/reproduction/REPRODUCTION_SUMMARY.json').read_text(encoding='utf-8'))
mech=json.loads((ROOT/'validation/w2_b2/mechanical/MECHANICAL_SUMMARY.json').read_text(encoding='utf-8'))
blind=json.loads((ROOT/'validation/w2_b2/fresh200/DECISION.json').read_text(encoding='utf-8'))
verdicts=pd.read_csv(ROOT/'validation/w2_b2/multijudge/09_JUDGE_VERDICTS.csv')

checks['model_id']=version.get('model_id')=='HerbalA-v22r-W2B2'
checks['status_model_id']=status.get('model_id')=='HerbalA-v22r-W2B2'
checks['cfg_enabled']=bool(cfg.get('enabled'))
checks['scope_middle_w2']=cfg['scope']['row_phase']=='MIDDLE' and cfg['scope']['role']=='W2' and cfg['scope']['board']=='W2'
checks['scope_len3_5']=int(cfg['scope']['min_glyph_length'])==3 and int(cfg['scope']['max_glyph_length'])==5
checks['known_tau128']=float(cfg['target_h2_law']['known3_tau'])==128.0
checks['namespace']=cfg['selection']['namespace']=='V22R_W2_H2_B2_MINIMAL_V1'
checks['reproduction_hash_20_20']=bool(rep.get('hash_all_exact')) and int(rep.get('leaves',0))==20
checks['reproduction_requests_130_130']=bool(rep.get('request_all_exact')) and int(rep.get('requests',0))==130
checks['mechanical_pass']=all(bool(mech.get(k)) for k in ['token_count_equal','tokenwise_length_equal','tokenwise_width_equal','packing_trace_equal','packing_exact','scope_ok','h1_frozen','h3plus_frozen','terminal_frozen','width_frozen','parent_rng_untouched','semantic_precommit_untouched'])
checks['mechanical_support_zero']=int(mech.get('support_violations',-1))==0 and int(mech.get('invalid_rows',-1))==0
checks['blind_pass']=blind.get('status')=='PASS_WITH_RESIDUAL' and bool(blind.get('judgment',{}).get('promote_as_w2_fix'))
checks['blind_target_improved']=int(blind['targeted_w2']['positive_leaves'])==17 and float(blind['targeted_w2']['paired_wilcoxon_greater_p'])<0.001
checks['global_not_claimed_closed']=not bool(blind.get('judgment',{}).get('global_bigram_closed'))
# Remote positional families must remain exact invariants in the saved multijudge.
remote=verdicts[verdicts['family'].isin(['FIRST_LINE','LINE_HEAD','BODY','LINE_END'])]
checks['remote_position_no_regression']=bool((remote['verdict']=='EXACT_INVARIANT').all())

out={'model_id':'HerbalA-v22r-W2B2','status':'PASS' if all(checks.values()) else 'FAIL','checks':checks}
print(json.dumps(out,ensure_ascii=False,indent=2))
if out['status']!='PASS':
    raise SystemExit(1)
