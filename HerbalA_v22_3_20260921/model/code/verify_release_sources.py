from pathlib import Path
import csv, hashlib, sys
ROOT=Path(__file__).resolve().parents[1]
manifest=ROOT/'sources/SOURCE_ARCHIVES_SHA256.csv'
ok=True
with manifest.open(encoding='utf-8') as f:
    for r in csv.DictReader(f):
        p=ROOT/'sources'/r['filename']
        if not p.exists():
            print('MISSING',p); ok=False; continue
        h=hashlib.sha256(p.read_bytes()).hexdigest()
        good=h==r['sha256']
        print('PASS' if good else 'FAIL',p.name,h)
        ok &= good
if not ok: sys.exit(1)
