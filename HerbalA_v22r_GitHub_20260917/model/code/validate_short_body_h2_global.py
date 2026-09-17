from __future__ import annotations
import json
from pathlib import Path
import pandas as pd

ROOT=Path(__file__).resolve().parents[1]
V=ROOT/'validation/short_body_h2_global/prejudge'
noop=pd.read_csv(V/'NOOP_HASH_AUDIT.csv')
selftest=pd.read_csv(V/'SELFTEST_20_CASES.csv')
trace=pd.read_csv(V/'SHORT_H2_TRACE_EVENTS.csv')
checks={
    'noop_rows_20_20': bool(noop['rows_match'].all() and len(noop)==20),
    'noop_commits_20_20': bool(noop['commits_match'].all() and len(noop)==20),
    'packing_20_20': bool(selftest['packing'].all() and len(selftest)==20),
    'support_zero': int(selftest['support'].sum())==0,
    'invalid_zero': int(selftest['invalid'].sum())==0,
    'intervention_events_positive': int(selftest['h2_events'].sum())>0,
    'actual_changes_positive': int(selftest['h2_changed'].sum())>0,
    'trace_scope_body': bool((trace['role']=='BODY').all()),
    'trace_lengths_2_4': bool(trace['short_body_h2_length'].between(2,4).all()),
}
out={'status':'PASS' if all(checks.values()) else 'FAIL','checks':checks,
     'events':int(selftest['h2_events'].sum()),'changes':int(selftest['h2_changed'].sum()),
     'changed_bifolia':int(selftest['hash_changed'].sum()),'blind_judge_run':False}
(V/'VALIDATION.json').write_text(json.dumps(out,ensure_ascii=False,indent=2),encoding='utf-8')
print(json.dumps(out,ensure_ascii=False,indent=2))
if out['status']!='PASS': raise SystemExit(1)
