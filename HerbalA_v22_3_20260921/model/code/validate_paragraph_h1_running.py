from __future__ import annotations
import json
from pathlib import Path
import pandas as pd

ROOT=Path(__file__).resolve().parents[1]
V=ROOT/'validation/paragraph_h1_running'
A=pd.read_csv(V/'SELFTEST_20_CASES.csv')
D=pd.read_csv(V/'H1_CHANGED_ROWS.csv')
checks={
    'cases_20': len(A)==20,
    'noop_rows_20_20': bool(A['parent_noop_rows'].all()),
    'noop_commits_20_20': bool(A['parent_noop_commits'].all()),
    'packing_20_20': bool(A['packing'].all()),
    'support_zero': int(A['support'].sum())==0,
    'invalid_zero': int(A['invalid'].sum())==0,
    'structure_frozen_20_20': bool(A['structure_same'].all()),
    'route_state_frozen_20_20': bool(A['route_state_same'].all()),
    'h1_only_all_changes': bool(A['h1_only'].all()),
    'h2plus_frozen_all_changes': bool(A['h2plus_frozen'].all()),
    'exact_length_all_changes': bool(A['exact_length'].all()),
    'exact_width_all_changes': bool(A['exact_width'].all()),
    'parent_rng_untouched': bool(A['parent_rng_untouched'].all()),
    'precommit_semantics_untouched': bool(A['semantic_precommit_untouched'].all()),
    'intervention_applied_positive': int(A['applied'].sum())>0,
    'actual_h1_changes_positive': len(D)>0,
    'audit_change_count_matches_rows': int(A['audit_changed'].sum())==len(D),
}
out={
    'status':'PASS' if all(checks.values()) else 'FAIL',
    'checks':checks,
    'seed':91601,
    'cases':len(A),
    'eligible_commits':int(A['committed_eligible'].sum()),
    'applied':int(A['applied'].sum()),
    'changed_rows':len(D),
    'changed_bifolia':int((A['changed_rows']>0).sum()),
    'blind_judge_run':False,
}
(V/'VALIDATION.json').write_text(json.dumps(out,ensure_ascii=False,indent=2),encoding='utf-8')
print(json.dumps(out,ensure_ascii=False,indent=2))
if out['status']!='PASS': raise SystemExit(1)
