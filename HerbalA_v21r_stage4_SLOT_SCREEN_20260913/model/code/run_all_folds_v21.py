from __future__ import annotations
import argparse,subprocess,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
def main():
    ap=argparse.ArgumentParser();ap.add_argument('--runs',default='91321,91322,91323,91324,91325');ap.add_argument('--mode',choices=['V20_COMPAT','SAFE_LEFT'],default='SAFE_LEFT');ap.add_argument('--output-root',default=str(ROOT/'outputs/stage2'));a=ap.parse_args()
    for fold in range(5):subprocess.run([sys.executable,str(ROOT/'code/run_model_v21.py'),'--fold',str(fold),'--runs',a.runs,'--mode',a.mode,'--output-root',a.output_root,'--skip-existing'],check=True)
if __name__=='__main__':main()
