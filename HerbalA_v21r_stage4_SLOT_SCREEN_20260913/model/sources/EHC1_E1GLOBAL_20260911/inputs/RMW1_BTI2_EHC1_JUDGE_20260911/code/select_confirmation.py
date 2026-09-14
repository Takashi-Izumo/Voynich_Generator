#!/usr/bin/env python3
"""Select one unchanged finalist; warnings forbid automatic promotion."""
import evaluation_common as e
from stage3_env import ROOT
import pandas as pd,json

def main():
 s=pd.read_csv(ROOT/'outputs/multirun/judged/paired_vs_parent.csv');sel=json.loads((ROOT/'SELECTION_FROZEN.json').read_text());r=[]
 for a,g in s.groupby('arm'):
  score=float((1+g[g.judge.isin(e.PRIMARY+e.HEAD)].change_pct/100).mean())
  warnings=g[g.judge.isin(e.REGRESSION)&g.change_pct.gt(10)].judge.tolist()
  r.append(dict(arm=a,five_channel_ratio=score,regression_warnings=warnings))
 best=min(r,key=lambda d:(d['five_channel_ratio'],d['arm']))
 plan=dict(selected_arms=[best['arm']],confirmation_seeds=sel['confirmation_seeds'],ranking=r,selection_basis='balanced five-channel fixed diagnostic score, same unchanged candidates; warnings retained',settings_changed=False,performance_status_before_confirmation='NOT_PROMOTABLE_REGRESSION_WARNINGS',three_seed_result_sha256=e.file_hash(ROOT/'outputs/multirun/judged/paired_vs_parent.csv'))
 e.write(ROOT/'CONFIRMATION_FROZEN.json',plan);print(plan)
if __name__=='__main__':main()
