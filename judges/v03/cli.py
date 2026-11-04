from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys
from .protocol import load_protocol, read_json, read_jsonl


def main(argv=None):
    ap=argparse.ArgumentParser(description='Voynich judges v0.3: measurement and genuine-only calibration')
    sub=ap.add_subparsers(dest='command',required=True)
    p=sub.add_parser('export');p.add_argument('--plan',type=Path,required=True);p.add_argument('--profile',default='structure-endpoints-v2');p.add_argument('--output',type=Path,required=True)
    p=sub.add_parser('validate');p.add_argument('--input',type=Path,required=True);p.add_argument('--protocol',type=Path)
    p=sub.add_parser('fit');p.add_argument('--corpus',type=Path,required=True);p.add_argument('--fold-plan',type=Path);p.add_argument('--protocol',type=Path);p.add_argument('--output',type=Path,required=True)
    p=sub.add_parser('predict');p.add_argument('--input',type=Path,required=True);p.add_argument('--protocol',type=Path);p.add_argument('--models',type=Path);p.add_argument('--primary',choices=['J24.PROTO','J24.CAL'],default='J24.PROTO');p.add_argument('--jobs',type=int,default=1);p.add_argument('--output',type=Path,required=True)
    p=sub.add_parser('score');p.add_argument('--predictions',type=Path,required=True);p.add_argument('--key',type=Path,required=True);p.add_argument('--output',type=Path,required=True);p.add_argument('--bootstrap',type=int,default=10000)
    p=sub.add_parser('compare');p.add_argument('--scores-v21',type=Path,required=True);p.add_argument('--scores-v223',type=Path,required=True);p.add_argument('--output',type=Path,required=True);p.add_argument('--bootstrap',type=int,default=10000)
    p=sub.add_parser('controls');p.add_argument('--corpus',type=Path,required=True);p.add_argument('--fold-plan',type=Path);p.add_argument('--protocol',type=Path);p.add_argument('--output',type=Path,required=True)
    p=sub.add_parser('capability');p.add_argument('--predictions',type=Path,required=True);p.add_argument('--controls',type=Path,required=True);p.add_argument('--output',type=Path,required=True);p.add_argument('--bootstrap',type=int,default=10000)
    p=sub.add_parser('audit-b2');p.add_argument('--export-manifest',type=Path,required=True);p.add_argument('--generator-results',type=Path,required=True);p.add_argument('--output',type=Path,required=True)
    a=ap.parse_args(argv)
    try:
        load_protocol(getattr(a,'protocol',None))
        if a.command=='export':
            if a.profile!='structure-endpoints-v2':raise ValueError('unsupported input profile')
            from .adapter import export
            result={'exported':export(read_json(a.plan),a.output)}
        elif a.command=='validate':
            from .schema import unique_cases
            rows=read_jsonl(a.input);unique_cases(rows);result={'valid':True,'sets':len(rows)}
        elif a.command=='fit':
            from .calibration import fit
            r=fit(read_json(a.corpus),a.output,read_json(a.fold_plan) if a.fold_plan else None)
            result={'fitted_outer_models':len(r['models']),'output':str(a.output)}
        elif a.command=='predict':
            from .artifacts import predict_file
            rows=predict_file(a.input,a.output,a.models,a.primary,a.jobs);result={'sealed':True,'sets':len(rows),'primary':a.primary}
        elif a.command=='score':
            from .statistics import score
            r=score(a.predictions,a.key,a.output,a.bootstrap);result={'primary':r['primary'],'summary':r['primary_summary']|{'by_bifolium':'see summary.json'},'promotion_verdict':None}
        elif a.command=='compare':
            from .statistics import compare_scores
            r=compare_scores(a.scores_v21,a.scores_v223,a.output,a.bootstrap);result={'primary':r['primary'],'paired':r['views'][r['primary']]['paired_expected_game']}
        elif a.command=='controls':
            from .controls import create_controls
            result=create_controls(read_json(a.corpus),a.output,read_json(a.fold_plan) if a.fold_plan else None)
        elif a.command=='capability':
            from .controls import capability
            result=capability(a.predictions,a.controls,a.output,a.bootstrap)
        else:
            from .mechanism import audit
            result=audit(a.export_manifest,a.generator_results,a.output)
        print(json.dumps(result,ensure_ascii=False,allow_nan=False));return 0
    except (ValueError,OSError,KeyError,TypeError) as exc:
        print('judges v03: '+str(exc),file=sys.stderr);return 2


if __name__=='__main__':raise SystemExit(main())
