from __future__ import annotations

import argparse
import json


def main():
    cli=argparse.ArgumentParser(description='Isolated supported PF capability controls (no production-law changes)')
    sub=cli.add_subparsers(dest='command',required=True)
    p=sub.add_parser('plan');p.add_argument('--output',required=True)
    p.add_argument('--bifolia',nargs='+',default=['A:2','A:3','G:1']);p.add_argument('--kind',choices=['smoke','controls'],default='smoke')
    for name in ('generate','audit','export','verify-export','evaluate'):
        p=sub.add_parser(name);p.add_argument('--plan',required=True)
        if name!='generate':p.add_argument('--generated',required=True)
        if name!='verify-export':p.add_argument('--output',required=True)
        if name in ('verify-export','evaluate'):p.add_argument('--exported',required=True)
        if name=='evaluate':p.add_argument('--models',required=True);p.add_argument('--jobs',type=int,default=1)
    args=vars(cli.parse_args());command=args.pop('command')
    if command=='plan':
        from .plan import create
        result=create(**args);print(json.dumps(dict(plan_sha256=result['sha256'],eligible_cohorts=result['eligible_cohorts'])))
    else:
        from . import pipeline
        if command=='evaluate':
            from .evaluation import evaluate
            result=evaluate(**args)
        else:
            result=getattr(pipeline,command.replace('-','_'))(**args)
        print(json.dumps(dict(command=command,status='COMPLETE')))


if __name__=='__main__':
    main()
