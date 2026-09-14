"""Resolve bundled frozen input modules, without editing them."""
from pathlib import Path
import os, sys
ROOT = Path(__file__).resolve().parents[1]
EHC = ROOT/'inputs/RMW1_BTI2_EHC1_20260911'
JUDGE = ROOT/'inputs/RMW1_BTI2_EHC1_JUDGE_20260911'
DIAG = ROOT/'inputs/BTI2_EHC1_SPACE_DIAG1_20260911'
sys.dont_write_bytecode=True
os.environ['EHC1_ROOT']=str(EHC)
os.environ['NUMBA_CACHE_DIR']=str(ROOT/'outputs/numba_cache')
for k in ('OPENBLAS_NUM_THREADS','OMP_NUM_THREADS','MKL_NUM_THREADS','NUMBA_NUM_THREADS'): os.environ[k]='1'
sys.path.insert(0,str(JUDGE/'code'))
import evaluation_common as e
import numpy as np, pandas as pd
