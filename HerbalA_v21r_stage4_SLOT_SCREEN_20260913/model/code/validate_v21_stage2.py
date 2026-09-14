from __future__ import annotations
import argparse,json,subprocess,sys,tempfile
from pathlib import Path
import pandas as pd
ROOT=Path(__file__).resolve().parents[1]
VAL=ROOT/'validation/stage2'

def main():
    ap=argparse.ArgumentParser(description='v21r Stage-2 SAFE_LEFT validator')
    ap.add_argument('--smoke',action='store_true')
    a=ap.parse_args()
    for f in ['integrated_sampler_v21.py','run_model_v21.py','run_all_folds_v21.py']:
        subprocess.run([sys.executable,'-m','py_compile',str(ROOT/'code'/f)],check=True)
    rep=pd.read_csv(VAL/'historical_reproduction.csv')
    mech=pd.read_csv(VAL/'mechanical_summary.csv').iloc[0]
    href=pd.read_csv(VAL/'SAFE_LEFT_REFERENCE_HASHES_5SEED.csv')
    out={
      'stage':2,'mode':'SAFE_LEFT','static':'PASS',
      'historical_checks':int(len(rep)),'historical_matches':int(rep['match'].sum()),
      'hash_reference_cases':int(len(href)),
      'events':int(mech.events),'changed':int(mech.changed),'fallback':int(mech.fallback),
      'eligible':int(mech.eligible),'right_off_events':int(mech.right_off_events),
      'support':int(mech.support),'invalid':int(mech.invalid),'packing':bool(mech.packing),
    }
    assert out['historical_checks']==out['historical_matches']==23
    assert out['hash_reference_cases']==100
    assert out['events']==out['right_off_events']==542
    assert out['changed']==162 and out['fallback']==5 and out['eligible']==7069
    assert out['support']==0 and out['invalid']==0 and out['packing']
    if a.smoke:
        with tempfile.TemporaryDirectory(prefix='v21s2_',dir='/mnt/data') as td:
            subprocess.run([sys.executable,str(ROOT/'code/run_model_v21.py'),'--fold','0','--bif','A:2','--run','91321','--mode','SAFE_LEFT','--output-root',td],check=True)
            mechp=next(Path(td).glob('run91321/*/A_2/MECHANICAL.json'));d=json.loads(mechp.read_text());r=href[(href.run==91321)&(href.bif=='A:2')].iloc[0]
            for k in ['generated_rows_sha256','surface_commits_sha256','generation_input_sha256']: assert str(d[k])==str(r[k]),(k,d[k],r[k])
            out['smoke']='PASS';out['smoke_case']='fold0 A:2 run91321'
    print(json.dumps(out,ensure_ascii=False,indent=2))
if __name__=='__main__': main()
