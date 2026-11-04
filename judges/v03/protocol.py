from __future__ import annotations

import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).parent


def digest(value):
    return hashlib.sha256(json.dumps(value, ensure_ascii=False, sort_keys=True,
        separators=(',', ':'), allow_nan=False).encode()).hexdigest()


def read_json(path):
    def invalid(value):
        raise ValueError('non-finite JSON number: '+value)
    return json.loads(Path(path).read_text(), parse_constant=invalid)


def read_jsonl(path):
    def invalid(value):
        raise ValueError('non-finite JSON number: '+value)
    rows = [json.loads(s, parse_constant=invalid) for s in Path(path).read_text().splitlines() if s.strip()]
    if not rows:
        raise ValueError('empty JSONL')
    return rows


def write_json(path, value):
    Path(path).write_text(json.dumps(value, ensure_ascii=False, sort_keys=True, indent=2, allow_nan=False)+'\n')


def write_jsonl(path, rows):
    Path(path).write_text(''.join(json.dumps(r, ensure_ascii=False, sort_keys=True, allow_nan=False)+'\n' for r in rows))


def file_hash(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def extractor_hash():
    # Include reused legacy primitives and every v03 source/contract, not only root *.py.
    parent = ROOT.parent
    paths = list(ROOT.rglob('*.py')) + list((ROOT/'contracts').glob('*.json'))
    paths += [parent/n for n in ['features.py', 'schema.py', 'scoring.py', 'registry.py']]
    return digest({str(p.relative_to(parent)): file_hash(p) for p in sorted(paths)})


DEFAULT = read_json(ROOT/'contracts/protocol.json')


def load_protocol(path=None):
    value = DEFAULT if path is None else read_json(path)
    # Initial release has one preregistered protocol. Changes require a versioned release.
    if value != DEFAULT:
        raise ValueError('unsupported protocol; v0.3-v1 parameters are fixed')
    return value


PROTOCOL_HASH = digest(DEFAULT)
