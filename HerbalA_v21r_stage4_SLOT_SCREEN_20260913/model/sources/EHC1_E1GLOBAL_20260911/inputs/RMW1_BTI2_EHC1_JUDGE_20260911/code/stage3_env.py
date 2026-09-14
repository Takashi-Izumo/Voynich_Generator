"""Isolated evaluation paths; frozen generator code is never edited."""
import os,sys,zipfile,hashlib
from pathlib import Path
for k in ('OPENBLAS_NUM_THREADS','OMP_NUM_THREADS','MKL_NUM_THREADS','NUMBA_NUM_THREADS'):os.environ[k]='1'
ROOT=Path(__file__).resolve().parents[1]
EHC=Path(os.environ.get('EHC1_ROOT',str(ROOT/'work/RMW1_BTI2_EHC1_20260911')))
EXPECTED='016075e63e7c8a85516d80354ac787908a5c4888fcbc3118da1fb6c0bdd21f3a'
if not (EHC/'code/run_bti2_ehc1.py').exists():
    p=ROOT/'input/RMW1_BTI2_EHC1_20260911.zip'
    if not p.exists():raise FileNotFoundError('Set EHC1_ROOT to the unmodified Stage-2 extraction, or place the Stage-2 ZIP in input/.')
    if hashlib.sha256(p.read_bytes()).hexdigest()!=EXPECTED:raise ValueError('Stage-2 archive hash mismatch')
    EHC=ROOT/'work/RMW1_BTI2_EHC1_20260911'
    with zipfile.ZipFile(p) as z:z.extractall(ROOT/'work')
sys.path.insert(0,str(EHC/'code'))
import ehc_paths
