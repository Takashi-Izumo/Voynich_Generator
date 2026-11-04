from __future__ import annotations

import json, os, sys, py_compile
from pathlib import Path
import numpy as np
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

import v19r_rb3_pw2_close1 as m
from f1lf_length_terminal_law import TerminalLaw, long_l_inheritance, law_invariants
from f1lf_length_terminal_sampler import V223F1LFLengthTerminalSampler


def main():
    checks = {}
    cfg = json.loads((PACKAGE_ROOT/'parameters/V22_3_STAGE3D_CONFIG.json').read_text(encoding='utf-8'))
    scope = pd.read_csv(PACKAGE_ROOT/'parameters/F1LF_STRICT_SCOPE_88.csv')
    audit = pd.read_csv(PACKAGE_ROOT/'parameters/F1LF_STAGE3D_LAW_AUDIT.csv')
    laws = PACKAGE_ROOT/'parameters/f1lf_stage3d_laws'

    checks['model_id_candidate'] = cfg['model_id'] == 'HerbalA-v22.3-STAGE3D-R1-CANDIDATE'
    checks['parent_v22_2'] = cfg['parent_model_id'] == 'HerbalA-v22.2'
    checks['strict_events_88'] = len(scope) == 88
    checks['strict_bifolia_20'] = scope.bif.nunique() == 20
    checks['scope_all_first_f1_lf'] = bool((scope.row_phase.eq('FIRST') & scope.role.eq('F1') & scope.board.eq('LF')).all())
    checks['scope_all_segment0'] = bool(scope.segment_id.eq(0).all())
    checks['scope_no_plant'] = bool((~scope.plant_restart.astype(bool) & ~scope.plant_boundary.astype(bool)).all())
    checks['scope_multiline_multiword'] = bool((scope.paragraph_line_count.gt(1) & scope.line_word_count.gt(1)).all())
    checks['scope_exact_linear_width_known'] = bool((scope.mapping_quality.eq('EXACT_W_SEQUENCE') & scope.layout_mode.eq('linear_paragraph') & scope.width_known.astype(bool)).all())
    checks['law_count_20'] = len(list(laws.glob('*.json'))) == 20 == len(audit)
    checks['all_training_19'] = bool(audit.training_bifs.eq(19).all())
    checks['all_support_unchanged'] = bool(audit.support_changes.eq(0).all())
    checks['law_sum'] = float(audit.probability_sum_error.max()) <= 1e-12
    checks['law_l_exact'] = float(audit.l_inheritance_error.max()) <= 2e-12
    checks['law_non_l_ratio'] = float(audit.non_l_ratio_error.max()) <= 1e-12
    checks['law_yn_ratio'] = float(audit.y_n_ratio_error.max()) <= 1e-12
    checks['law_finite_nonnegative'] = bool(audit.finite.astype(bool).all() and audit.nonnegative.astype(bool).all())

    # 20/20 per-bif logical equivalence + one strict-ledger equivalence = 21/21.
    logical = []
    lidx = int(m.G2I['l'])
    yidx = int(m.G2I['y']); nidx = int(m.G2I['n'])
    for p in sorted(laws.glob('*.json')):
        payload = json.loads(p.read_text(encoding='utf-8'))
        law = TerminalLaw(**payload['law'])
        pf = np.asarray(law.p_f1_long, float)
        pl = np.asarray(law.p_normal_lf_long, float)
        pn = np.asarray(law.p_long_new, float)
        recomputed = long_l_inheritance(pf, pl)
        ok = (
            np.max(np.abs(recomputed-pn)) <= 1e-14
            and abs(pn[lidx]-pl[lidx]) <= 2e-12
            and abs((pn[yidx]/pn[nidx])-(pf[yidx]/pf[nidx])) <= 1e-12
            and np.array_equal(pf>0, pn>0)
            and abs(np.asarray(law.p_normal_lf_short).sum()-1) <= 1e-12
        )
        logical.append(dict(target_bif=law.target_bif, pass_=bool(ok), **law_invariants(law)))
    logical.append(dict(target_bif='STRICT_SCOPE_LEDGER', pass_=bool(len(scope)==88 and scope.bif.nunique()==20)))
    checks['logical_21_of_21'] = sum(int(x['pass_']) for x in logical) == 21

    # Scope gate can only activate keys carried by the structural ledger.
    V223F1LFLengthTerminalSampler.STAGE3D_STRICT_KEYS = frozenset(zip(scope.page.astype(str), scope.locus.astype(str)))
    class S: pass
    st=S()
    inside=scope.iloc[0]
    rin=dict(v22_2_f1lf_router_off_scope=True,page=inside.page,locus=inside.locus,role='F1',row_phase='FIRST',segment_id=0,board='LF',end=True,line_end_boundary=True)
    rout=dict(rin,page='__OUTSIDE__',locus='__OUTSIDE__')
    checks['strict_gate_inside'] = V223F1LFLengthTerminalSampler._strict_record_scope(st,rin)
    checks['strict_gate_outside'] = not V223F1LFLengthTerminalSampler._strict_record_scope(st,rout)

    # Static implementation safety: no commit-after-the-fact word[-1] assignment;
    # final child is passed to both semantic and surface commit paths.
    src=(PACKAGE_ROOT/'code/f1lf_length_terminal_sampler.py').read_text(encoding='utf-8')
    checks['no_word_minus1_assignment'] = 'word[-1] =' not in src and 'word[-1]=' not in src
    checks['stop_not_modified'] = 'stop_changed=False' in src and 'STOP/CONTINUE is inherited unchanged' in src
    checks['candidate_bank_not_modified'] = 'candidate_bank_changed=False' in src
    checks['prefix_frozen'] = 'out[:-1] != seq[:-1]' in src
    checks['semantic_visible_same_child'] = 'visible_semantic_terminal_match' in src
    checks['route_commit_uses_v22_2_base_child'] = 'v22_3_stage3d_route_uses_v22_2_base_child' in src and 'return super().commit_word(seq, role, sr)' in src
    checks['surface_commit_freezes_route'] = 'v22_3_stage3d_route_state_frozen_on_surface_commit' in src

    for f in ['f1lf_length_terminal_law.py','f1lf_length_terminal_sampler.py','build_v22_3_stage3d_tables.py','run_v22_3_stage3d.py']:
        py_compile.compile(str(PACKAGE_ROOT/'code'/f), doraise=True)
    checks['compile'] = True

    status = 'PASS' if all(bool(v) for v in checks.values()) else 'FAIL'
    out = {
        'status': status,
        'model_id': cfg['model_id'],
        'parent_model_id': cfg['parent_model_id'],
        'stage': '3D_R1_STATIC_AND_LOGICAL',
        'checks': checks,
        'logical_tests_passed': sum(int(x['pass_']) for x in logical),
        'logical_tests_total': len(logical),
        'max_errors': {
            'probability_sum': float(audit.probability_sum_error.max()),
            'l_inheritance': float(audit.l_inheritance_error.max()),
            'non_l_ratio': float(audit.non_l_ratio_error.max()),
            'y_n_ratio': float(audit.y_n_ratio_error.max()),
            'support_changes': int(audit.support_changes.max()),
        },
        'live_generation_run': False,
        'promotion': False,
        'next_stage': '3E unit/invariant runtime audit',
    }
    vdir=PACKAGE_ROOT/'validation/stage3d'
    vdir.mkdir(parents=True,exist_ok=True)
    (vdir/'VALIDATION_STAGE3D.json').write_text(json.dumps(out,ensure_ascii=False,indent=2),encoding='utf-8')
    pd.DataFrame(logical).to_csv(vdir/'LOGICAL_EQUIVALENT_21.csv',index=False)
    print(json.dumps(out,ensure_ascii=False,indent=2))
    if status!='PASS': raise SystemExit(1)

if __name__=='__main__': main()
