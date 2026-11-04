from __future__ import annotations
import argparse, json, subprocess, sys, tempfile
from pathlib import Path
import pandas as pd
ROOT = Path(__file__).resolve().parents[1]

HASH_KEYS = ('generated_rows_sha256','surface_commits_sha256','generation_input_sha256')

def check_outputs(out_root: Path):
    ref = pd.read_csv(ROOT/'validation/REFERENCE_HASHES_5SEED.csv')
    rows=[]
    for _,r in ref.iterrows():
        run=int(r.run); bif=str(r.bif)
        ms=list(out_root.glob(f'run{run}/*/{bif.replace(":","_")}/MECHANICAL.json'))
        if len(ms)!=1:
            raise RuntimeError(f'{run} {bif}: expected 1 MECHANICAL.json, got {len(ms)}')
        d=json.loads(ms[0].read_text())
        rec={'run':run,'bif':bif}
        for k in HASH_KEYS: rec[k+'_match']=(str(d[k])==str(r[k]))
        rec['all_match']=all(rec[k+'_match'] for k in HASH_KEYS)
        rows.append(rec)
    df=pd.DataFrame(rows)
    return df

def main():
    ap=argparse.ArgumentParser(description='v21r Stage-1 V20_COMPAT validator')
    ap.add_argument('--smoke',action='store_true')
    ap.add_argument('--audit-root',type=Path)
    ap.add_argument('--full-generate',action='store_true',help='generate the official 5-seed x 20-bif = 100 cases before auditing')
    a=ap.parse_args()
    subprocess.run([sys.executable,'-m','py_compile',
                    str(ROOT/'code/integrated_sampler_v21.py'),
                    str(ROOT/'code/run_model_v21.py'),
                    str(ROOT/'code/run_all_folds_v21.py')],check=True)
    out={'static':'PASS','stage':'v21r Stage 1','mode':'V20_COMPAT'}
    if a.smoke:
        with tempfile.TemporaryDirectory(prefix='v21s1_',dir='/mnt/data') as td:
            subprocess.run([sys.executable,str(ROOT/'code/run_model_v21.py'),'--fold','0','--bif','A:2','--run','91321','--mode','V20_COMPAT','--output-root',td],check=True)
            d=check_outputs(Path(td)) if False else None
            mech=next(Path(td).glob('run91321/*/A_2/MECHANICAL.json'))
            md=json.loads(mech.read_text())
            ref=pd.read_csv(ROOT/'validation/REFERENCE_HASHES_5SEED.csv')
            r=ref[(ref.bif=='A:2')&(ref.run==91321)].iloc[0]
            for k in HASH_KEYS:
                assert str(md[k])==str(r[k]),(k,md[k],r[k])
            out['smoke']='PASS'
            out['smoke_case']='fold0 A:2 run91321'
    audit_root=a.audit_root
    if a.full_generate:
        if audit_root is None:
            audit_root=ROOT/'outputs/v21_stage1_hash100'
        for fold in range(5):
            subprocess.run([sys.executable,str(ROOT/'code/run_model_v21.py'),'--fold',str(fold),'--runs','91321,91322,91323,91324,91325','--mode','V20_COMPAT','--output-root',str(audit_root),'--skip-existing'],check=True)
    if audit_root is not None:
        df=check_outputs(audit_root)
        out['cases']=len(df); out['matched_cases']=int(df.all_match.sum())
        out['matched_hash_fields']=int(sum(int(df[k+'_match'].sum()) for k in HASH_KEYS))
        out['hash_fields']=len(df)*len(HASH_KEYS)
        out['hash_audit']='PASS' if bool(df.all_match.all()) else 'FAIL'
        if not bool(df.all_match.all()):
            raise SystemExit(df[~df.all_match].to_string(index=False))
    print(json.dumps(out,ensure_ascii=False,indent=2))
if __name__=='__main__': main()
