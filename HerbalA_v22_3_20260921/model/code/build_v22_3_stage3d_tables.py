from __future__ import annotations

import json, os, sys
from pathlib import Path
import pandas as pd

from runtime_bootstrap import prepare_runtime, ROOT as PACKAGE_ROOT
HANDOFF, PARENT, ST = prepare_runtime()
os.environ['EHC2_STAGE6_PARENT'] = str(PARENT)
sys.path.insert(0, str(ST/'code'))
sys.path.insert(0, str(PACKAGE_ROOT/'code'))
from stage6_env import *
import experiment_env as benv
sys.path.insert(0, str(benv.EHC/'code'))
sys.path.insert(0, str(benv.EHC/'parent/HerbalA_RMW1_BTI2_20260909/code'))
from boundary_events import build_events
from f1lf_length_terminal_law import build_strict_scope_ledger, build_terminal_law, law_invariants


def main():
    out = PACKAGE_ROOT/'parameters'
    lawdir = out/'f1lf_stage3d_laws'
    lawdir.mkdir(parents=True, exist_ok=True)
    C = benv.e.context()
    events, lines = build_events(C)
    C.events = events
    scope = build_strict_scope_ledger(C, events, lines)
    scope.to_csv(out/'F1LF_STRICT_SCOPE_88.csv', index=False)

    rows = []
    for bif in C.bifs:
        law = build_terminal_law(events, C.bifs, bif, tau=20.0)
        inv = law_invariants(law)
        payload = dict(law=law.asdict(), invariants=inv)
        name = str(bif).replace(':','_') + '.json'
        (lawdir/name).write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding='utf-8')
        rows.append(dict(target_bif=bif, **{
            'training_bifs': len(law.training_bifs),
            'f1_long_n': law.f1_long_n,
            'normal_lf_short_n': law.normal_lf_short_n,
            'normal_lf_long_n': law.normal_lf_long_n,
            'shared_body_short_n': law.shared_body_short_n,
            'shared_body_long_n': law.shared_body_long_n,
            **inv,
        }))
    pd.DataFrame(rows).to_csv(out/'F1LF_STAGE3D_LAW_AUDIT.csv', index=False)
    summary = {
        'model_id': 'HerbalA-v22.3-STAGE3D-CANDIDATE',
        'parent_model_id': 'HerbalA-v22.2',
        'strict_events': int(len(scope)),
        'strict_bifolia': int(scope.bif.nunique()),
        'complete_bifolia': list(map(str,C.bifs)),
        'laws': int(len(rows)),
        'tau': 20.0,
        'status': 'TABLES_BUILT',
    }
    (out/'F1LF_STAGE3D_TABLE_SUMMARY.json').write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding='utf-8')
    print(json.dumps(summary, ensure_ascii=False, indent=2))

if __name__ == '__main__':
    main()
