from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
import sys
import tempfile
from pathlib import Path

import pandas as pd

from runtime_bootstrap import resolve_source_archive, source_status

ROOT = Path(__file__).resolve().parents[1]


def sha(path: Path) -> str:
    h = hashlib.sha256()
    with path.open('rb') as f:
        for chunk in iter(lambda: f.read(1 << 20), b''):
            h.update(chunk)
    return h.hexdigest()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--smoke', action='store_true')
    ap.add_argument(
        '--no-source-check',
        action='store_true',
        help='compile/config audit only; do not require external release assets',
    )
    args = ap.parse_args()

    cfg = json.loads((ROOT / 'parameters/MODEL_CONFIG.json').read_text())
    assert cfg['w2_h2_splice']['exact_glyph_length'] == 4
    assert cfg['w2_h2_splice']['sibling_k'] == 16
    assert cfg['w2_h2_splice']['known3_residual'] is False

    expected = {
        'RMW1_BTI2_EHC2_DECOMP1_PUV_HANDOFF_COMPACT_20260912.zip':
            '0a3ea22dbe826ca56100de3e185460e6a3b5e804c5b1166069abfc8dd6c04f29',
        'EHC1_E1GLOBAL_FULL_20260911.zip':
            'cf8ec127ab584a8460c3c02aa4f3a5b2a7f01a328a9b3568f58d6ce0c53c025f',
    }
    resolved = {}
    if not args.no_source_check:
        for name, digest in expected.items():
            p = resolve_source_archive(name, verify=True)
            assert sha(p) == digest
            resolved[name] = str(p)

    subprocess.run(
        [
            sys.executable,
            '-m',
            'py_compile',
            str(ROOT / 'code/runtime_bootstrap.py'),
            str(ROOT / 'code/w2_sibling_generator.py'),
            str(ROOT / 'code/integrated_sampler.py'),
            str(ROOT / 'code/run_model.py'),
            str(ROOT / 'code/integrated_sampler_v21.py'),
            str(ROOT / 'code/run_model_v21.py'),
        ],
        check=True,
    )

    out = {
        'static': 'PASS',
        'model_id': cfg['model_id'],
        'external_source_policy': 'verified release assets or local model/sources',
        'resolved_sources': resolved,
    }
    if args.no_source_check:
        out['source_check'] = 'SKIPPED'
        out['source_status'] = source_status()

    if args.smoke:
        if args.no_source_check:
            raise SystemExit('--smoke requires source archives; remove --no-source-check')
        with tempfile.TemporaryDirectory(prefix='w2l4int_') as td:
            subprocess.run(
                [
                    sys.executable,
                    str(ROOT / 'code/run_model.py'),
                    '--fold', '0',
                    '--bif', 'A:2',
                    '--run', '91321',
                    '--output-root', td,
                ],
                check=True,
            )
            mech = list(Path(td).glob('run91321/*/A_2/MECHANICAL.json'))
            assert len(mech) == 1
            data = json.loads(mech[0].read_text())
            ref = pd.read_csv(ROOT / 'validation/REFERENCE_HASHES_5SEED.csv')
            row = ref[(ref.bif == 'A:2') & (ref.run == 91321)].iloc[0]
            for key in (
                'generated_rows_sha256',
                'surface_commits_sha256',
                'generation_input_sha256',
            ):
                assert data[key] == row[key], (key, data[key], row[key])
            out['smoke_hash_identity'] = 'PASS'
            out['smoke_case'] = 'fold0 A:2 run91321'
            out['generated_rows_sha256'] = data['generated_rows_sha256']

    print(json.dumps(out, ensure_ascii=False, indent=2))


if __name__ == '__main__':
    main()
