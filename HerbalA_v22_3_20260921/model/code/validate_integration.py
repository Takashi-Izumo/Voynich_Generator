from __future__ import annotations
import argparse,hashlib,json,subprocess,sys,tempfile
from pathlib import Path
import pandas as pd
ROOT=Path(__file__).resolve().parents[1]

def sha(p):
    h=hashlib.sha256()
    with open(p,'rb') as f:
        for b in iter(lambda:f.read(1<<20),b''):h.update(b)
    return h.hexdigest()

def main():
    ap=argparse.ArgumentParser();ap.add_argument('--smoke',action='store_true');a=ap.parse_args()
    cfg=json.loads((ROOT/'parameters/MODEL_CONFIG.json').read_text())
    assert cfg['w2_h2_splice']['exact_glyph_length']==4 and cfg['w2_h2_splice']['sibling_k']==16
    assert cfg['w2_h2_splice']['known3_residual'] is False
    assert sha(ROOT/'sources/RMW1_BTI2_EHC2_DECOMP1_PUV_HANDOFF_COMPACT_20260912.zip')=='0a3ea22dbe826ca56100de3e185460e6a3b5e804c5b1166069abfc8dd6c04f29'
    assert sha(ROOT/'sources/EHC1_E1GLOBAL_FULL_20260911.zip')=='cf8ec127ab584a8460c3c02aa4f3a5b2a7f01a328a9b3568f58d6ce0c53c025f'
    subprocess.run([sys.executable,'-m','py_compile',str(ROOT/'code/runtime_bootstrap.py'),str(ROOT/'code/w2_sibling_generator.py'),str(ROOT/'code/integrated_sampler.py'),str(ROOT/'code/run_model.py')],check=True)
    out={'static':'PASS','model_id':cfg['model_id']}
    if a.smoke:
        with tempfile.TemporaryDirectory(prefix='w2l4int_',dir='/mnt/data') as td:
            subprocess.run([sys.executable,str(ROOT/'code/run_model.py'),'--fold','0','--bif','A:2','--run','91321','--output-root',td],check=True)
            mech=list(Path(td).glob('run91321/*/A_2/MECHANICAL.json'));assert len(mech)==1
            d=json.loads(mech[0].read_text());ref=pd.read_csv(ROOT/'validation/REFERENCE_HASHES_5SEED.csv');r=ref[(ref.bif=='A:2')&(ref.run==91321)].iloc[0]
            for k in ('generated_rows_sha256','surface_commits_sha256','generation_input_sha256'):assert d[k]==r[k],(k,d[k],r[k])
            out['smoke_hash_identity']='PASS';out['smoke_case']='fold0 A:2 run91321';out['generated_rows_sha256']=d['generated_rows_sha256']
    print(json.dumps(out,ensure_ascii=False,indent=2))
if __name__=='__main__':main()
