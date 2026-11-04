#!/usr/bin/env python3
from pathlib import Path
import runpy, sys
ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT/'model/code'))
runpy.run_path(str(ROOT/'model/code/run_v22_2.py'), run_name='__main__')
