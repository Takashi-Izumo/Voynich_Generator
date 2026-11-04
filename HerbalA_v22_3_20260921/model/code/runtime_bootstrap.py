from __future__ import annotations
from pathlib import Path
import zipfile
ROOT=Path(__file__).resolve().parents[1]
RUNTIME=ROOT/'runtime'
HANDOFF_ZIP=ROOT/'sources/RMW1_BTI2_EHC2_DECOMP1_PUV_HANDOFF_COMPACT_20260912.zip'
PARENT_ZIP=ROOT/'sources/EHC1_E1GLOBAL_FULL_20260911.zip'
HANDOFF_ROOT=RUNTIME/'RMW1_BTI2_EHC2_DECOMP1_PUV_HANDOFF_COMPACT_20260912'
PARENT_ROOT=RUNTIME/'EHC1_E1GLOBAL_20260911'
STAGE6=HANDOFF_ROOT/'current_model/RMW1_BTI2_EHC2_DECOMP1_STAGE6_20260911'

def _extract_once(z:Path, marker:Path):
    if marker.exists(): return
    if not z.exists(): raise FileNotFoundError(z)
    RUNTIME.mkdir(parents=True,exist_ok=True)
    with zipfile.ZipFile(z) as f: f.extractall(RUNTIME)
    if not marker.exists(): raise FileNotFoundError(marker)

def prepare_runtime():
    _extract_once(HANDOFF_ZIP,HANDOFF_ROOT/'README_START_HERE_JA.md')
    _extract_once(PARENT_ZIP,PARENT_ROOT/'README_JA.md')
    return HANDOFF_ROOT,PARENT_ROOT,STAGE6
