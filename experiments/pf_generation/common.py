from __future__ import annotations

import json
from pathlib import Path

from experiments.m1_pf.common import ROOT, PACKAGE, digest, file_hash, frozen_sources, state_hash, write_json
from experiments.m1_pf.inputs import runtime_inputs
from . import ARMS, DESIGN


def require(condition, reason):
    if not condition:
        raise ValueError(reason)


def model_dir(arm):
    require(arm in (*ARMS, 'REFERENCE'), 'Unknown PF generation arm')
    return 'HerbalA_v22_3_PFGEN_' + arm


def implementation_sources():
    manifest = json.loads((ROOT / 'sandbox/m1-review/implementation_manifest.json').read_text())
    require(manifest['payload_snapshot_sha256'] == '294a7afdc86949e4f774166c449a5415de9573c1e4e57ab6bb94032df57c1504',
            'Pinned M1 snapshot changed')
    for path, expected in manifest['files'].items():
        require(file_hash(ROOT / path) == expected, 'Pinned M1 file changed: ' + path)
    paths = [*Path(__file__).parent.glob('*.py'), ROOT / DESIGN]
    return {**manifest['files'], **{str(p.relative_to(ROOT)): file_hash(p) for p in sorted(paths)}}


def band(value):
    return 0 if value <= 3 else 1 if value <= 6 else 2 if value <= 9 else 3


def length_band(value):
    return 0 if value <= 3 else 1 if value <= 6 else 2
