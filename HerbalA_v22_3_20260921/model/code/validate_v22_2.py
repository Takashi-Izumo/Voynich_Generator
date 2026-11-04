from __future__ import annotations

import json
import py_compile
from pathlib import Path
from types import SimpleNamespace

ROOT = Path(__file__).resolve().parents[1]


def check(condition, message):
    if not condition:
        raise AssertionError(message)


def main():
    files = [
        ROOT/'code/f1lf_router_off_sampler.py',
        ROOT/'code/run_v22_2.py',
        ROOT/'code/w2_b2_sampler.py',
    ]
    for p in files:
        py_compile.compile(str(p), doraise=True)

    cfg = json.loads((ROOT/'parameters/V22_2_CONFIG.json').read_text(encoding='utf-8'))
    status = json.loads((ROOT/'MODEL_STATUS_V22_2.json').read_text(encoding='utf-8'))
    check(cfg['model_id'] == 'HerbalA-v22.2', 'model_id mismatch')
    check(cfg['parent_model_id'] == 'HerbalA-v22r-W2B2', 'parent mismatch')
    check(cfg['judge_status'] in {'NOT_RUN','PASS_WITH_RESIDUAL'}, 'unexpected judge status')
    check(status['status'] in {'IMPLEMENTED_PREJUDGE_NOT_JUDGED','PROMOTED_PASS_WITH_RESIDUAL'}, 'status mismatch')

    # Prepare the bundled runtime before importing the sampler. Mirror the
    # production runner's path bootstrap, but do not generate or judge pages.
    import os, sys
    sys.path.insert(0, str(ROOT/'code'))
    from runtime_bootstrap import prepare_runtime
    handoff, parent, stage6 = prepare_runtime()
    os.environ['EHC2_STAGE6_PARENT'] = str(parent)
    sys.path.insert(0, str(stage6/'code'))
    sys.path.insert(0, str(parent/'code'))
    import experiment_env as benv
    sys.path.insert(0, str(benv.EHC/'code'))
    sys.path.insert(0, str(benv.EHC/'parent/HerbalA_RMW1_BTI2_20260909/code'))
    sys.path.insert(0, str(benv.EHC/'parent/HerbalA_RMW1_BTI2_20260909/parent_SEL42/code'))
    from f1lf_router_off_sampler import V222F1LFRouterOffSampler

    class S:
        def __init__(self, row='FIRST', seg=0, pf=False, board='LF'):
            self.row_phase=row
            self.segment_id=seg
            self.par_h1_raw_para_final=pf
            self._board=board
        def board(self, role, end, line_end):
            return self._board

    def args(role='F1', end=True):
        z=[None]*11
        z[2]=role
        z[10]=end
        return tuple(z)

    fn = V222F1LFRouterOffSampler.is_f1lf_router_off_scope
    check(fn(S(), args(), {'line_end_boundary': True}), 'normal F1-LF must be in scope')
    check(not fn(S(seg=1), args(), {'line_end_boundary': True}), 'plant restart must be out')
    check(not fn(S(pf=True), args(), {'line_end_boundary': True}), 'paragraph-final FIRST must be out')
    check(not fn(S(row='MIDDLE'), args(), {'line_end_boundary': True}), 'MIDDLE must be out')
    check(not fn(S(), args(role='BODY'), {'line_end_boundary': True}), 'BODY must be out')
    check(not fn(S(), args(), {'line_end_boundary': False}), 'non-LF must be out')
    check(not fn(S(board='BODY'), args(), {'line_end_boundary': True}), 'non-LF board must be out')

    out = {
        'model_id': 'HerbalA-v22.2',
        'compile': 'PASS',
        'scope_truth_table': 'PASS',
        'parent': 'HerbalA-v22r-W2B2',
        'judge_scores_run': bool(cfg['judge_status'] != 'NOT_RUN'),
        'judge_status': cfg['judge_status'],
        'status': status['status']
    }
    (ROOT/'validation/V22_2_PREFLIGHT.json').write_text(json.dumps(out, ensure_ascii=False, indent=2), encoding='utf-8')
    print(json.dumps(out, ensure_ascii=False, indent=2))


if __name__ == '__main__':
    main()
