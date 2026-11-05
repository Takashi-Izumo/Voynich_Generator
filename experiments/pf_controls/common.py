from __future__ import annotations

import json
from pathlib import Path

from experiments.m1_pf.common import ROOT, PACKAGE, canonical, digest, file_hash, frozen_sources, source_state, state_hash, write_json
from experiments.m1_pf.inputs import runtime_inputs
from experiments.pf_generation.common import implementation_sources, require
from . import CONTRACT


def sources():
    paths = sorted(Path(__file__).parent.glob('*.py'))
    return {**implementation_sources(), CONTRACT: file_hash(ROOT / CONTRACT),
            **{str(p.relative_to(ROOT)): file_hash(p) for p in paths}}


def read(path):
    return json.loads(Path(path).read_text())


def seal(value):
    return dict(value, sha256=digest(value))


def unseal(value):
    require(value.get('sha256') == digest({k: v for k, v in value.items() if k != 'sha256'}), 'Receipt changed')
    return value


def file_inventory(root, exclude=()):
    return {p.relative_to(root).as_posix(): file_hash(p) for p in sorted(Path(root).rglob('*'))
            if p.is_file() and p.relative_to(root).as_posix() not in exclude}


def context(row):
    for k in ('bif', 'page', 'locus'):
        require(type(row.get(k)) is str, 'Invalid context string: ' + k)
    for k in ('run', 'event', 'segment_id'):
        require(type(row.get(k)) is int, 'Invalid context integer: ' + k)
    return tuple(row[k] for k in ('bif', 'run', 'page', 'locus', 'segment_id', 'event'))
