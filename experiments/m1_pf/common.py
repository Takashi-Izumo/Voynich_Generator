from __future__ import annotations

import dataclasses
import hashlib
import json
from pathlib import Path
import subprocess

from . import ARMS, BASE_COMMIT

ROOT = Path(__file__).resolve().parents[2]
PACKAGE = ROOT / 'HerbalA_v22_3_20260921'


def canonical(value):
    """Include keys, arrays, sets and payloads omitted by legacy state.digest()."""
    if isinstance(value, dict):
        return {'dict': sorted([[canonical(k), canonical(v)] for k, v in value.items()],
                               key=lambda p: json.dumps(p[0], sort_keys=True))}
    if isinstance(value, (set, frozenset)):
        return {'set': sorted([canonical(v) for v in value], key=lambda v: json.dumps(v, sort_keys=True))}
    if isinstance(value, (list, tuple)):
        return [canonical(v) for v in value]
    if dataclasses.is_dataclass(value):
        return canonical(dataclasses.asdict(value))
    if hasattr(value, 'tolist'):
        return canonical(value.tolist())
    if isinstance(value, Path):
        return str(value)
    if value is None or isinstance(value, (str, int, float, bool)):
        return value
    raise TypeError(f'Unreviewed mutable payload: {type(value).__name__}')


def digest(value):
    return hashlib.sha256(json.dumps(canonical(value), sort_keys=True, ensure_ascii=False,
                                     allow_nan=False, separators=(',', ':')).encode()).hexdigest()


def file_hash(path):
    with Path(path).open('rb') as f:
        return hashlib.file_digest(f, 'sha256').hexdigest()


def write_json(path, value):
    Path(path).write_text(json.dumps(value, ensure_ascii=False, sort_keys=True, indent=2,
                                    allow_nan=False) + '\n', encoding='utf-8')


def model_dir(arm):
    if arm not in ARMS:
        raise ValueError(f'Unknown M1 arm: {arm}')
    return 'HerbalA_v22_3_M1_' + arm


def frozen_sources():
    """Fail closed on generator/judge edits relative to the specified base commit."""
    paths = subprocess.check_output(['git', 'ls-tree', '-r', '--name-only', BASE_COMMIT,
                                     '--', PACKAGE.name, 'judges'], cwd=ROOT, text=True).splitlines()
    differences = subprocess.check_output(['git', 'diff', BASE_COMMIT, '--', PACKAGE.name, 'judges'], cwd=ROOT)
    if differences:
        raise ValueError('Frozen v22.3 or judges differ from the specified base commit')
    if not paths:
        raise ValueError('Base commit is not available')
    return {p: file_hash(ROOT / p) for p in paths}


def overlay_sources():
    return {str(p.relative_to(ROOT)): file_hash(p) for p in sorted(Path(__file__).parent.glob('*.py'))}


def source_state(state):
    motion = state.motion
    payload = {k: v for k, v in vars(state).items() if k != 'motion'}
    if motion is not None:
        # Correction rows are shared read-only probability tables; their content
        # fingerprint is recorded separately in each generation input audit.
        payload['motion'] = {k: v for k, v in vars(motion).items() if k != 'correction'}
        if hasattr(motion, 'correction'):
            payload['correction_content'] = motion.correction.content_fingerprint()
    return payload


def state_hash(state):
    return digest(source_state(state))
