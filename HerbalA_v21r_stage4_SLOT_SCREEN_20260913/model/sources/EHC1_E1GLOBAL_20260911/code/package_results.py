"""Package results and a standalone full copy; verify archive CRCs."""
from pathlib import Path
import zipfile,json,hashlib
ROOT=Path(__file__).resolve().parents[1]

def sha(p):
    h=hashlib.sha256()
    with p.open('rb') as f:
        for b in iter(lambda:f.read(2**20),b''):h.update(b)
    return h.hexdigest()

def main():
    arcs={}
    for name in ['RMW1_BTI2_EHC1_20260911.zip','RMW1_BTI2_EHC1_JUDGE_20260911.zip','BTI2_EHC1_SPACE_DIAG1_RESULTS_20260911.zip']:
        p=ROOT.parent/name
        if p.exists():arcs[name]={'sha256':sha(p),'bytes':p.stat().st_size}
    (ROOT/'SOURCE_ARCHIVES.json').write_text(json.dumps(arcs,indent=2))
    fs=[p for p in ROOT.rglob('*') if p.is_file() and not any(x in str(p) for x in ['__pycache__','numba_cache'])]
    manifest={str(p.relative_to(ROOT)):sha(p) for p in fs if p.name not in ['PACKAGE_FILE_SHA256.json','PACKAGE_SUMMARY.json']}
    (ROOT/'PACKAGE_FILE_SHA256.json').write_text(json.dumps(manifest,indent=2,sort_keys=True))
    fs.append(ROOT/'PACKAGE_FILE_SHA256.json')
    results=[]
    for mode in ['RESULTS','FULL']:
        dest=ROOT.parent/f'EHC1_E1GLOBAL_{mode}_20260911.zip'
        selected=[p for p in fs if mode=='FULL' or not str(p.relative_to(ROOT)).startswith('inputs/')]
        with zipfile.ZipFile(dest,'w',zipfile.ZIP_DEFLATED,compresslevel=6) as z:
            for p in sorted(set(selected)):z.write(p,str(Path(ROOT.name)/p.relative_to(ROOT)))
        with zipfile.ZipFile(dest) as z:
            bad=z.testzip();assert bad is None,bad
            count=len(z.namelist())
            assert not any(n.lower().endswith(('.ttf','.otf','.woff','.woff2')) for n in z.namelist())
        s=sha(dest);dest.with_suffix('.zip.sha256').write_text(f'{s}  {dest.name}\n')
        results.append(dict(file=dest.name,sha256=s,bytes=dest.stat().st_size,files=count,crc_pass=True))
        print(mode,count,round(dest.stat().st_size/1e6,2),s,flush=True)
    (ROOT/'PACKAGE_SUMMARY.json').write_text(json.dumps(results,indent=2))
if __name__=='__main__':main()
