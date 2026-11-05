"""Verify the expanded runtime's immutable inputs, not just the source ZIPs."""
from __future__ import annotations

import csv
import hashlib
from pathlib import Path, PurePosixPath
import zipfile

from .common import PACKAGE, digest, file_hash

_INVENTORIES = {}


def included(name):
    # Compiler caches are execution outputs, never generator settings/data.
    return '__pycache__' not in PurePosixPath(name).parts and not name.endswith(('.pyc', '.pyo', '.nbc', '.nbi'))


def verify_tree(root, expected):
    root = Path(root)
    actual = {p.relative_to(root).as_posix(): p for p in root.rglob('*') if p.is_file()
              and included(p.relative_to(root).as_posix())}
    if set(actual) != set(expected):
        raise ValueError('Extracted runtime input set changed (missing or additional files)')
    for name, row in expected.items():
        path = actual[name]
        if path.stat().st_size != row['bytes'] or file_hash(path) != row['sha256']:
            raise ValueError('Extracted runtime input changed: ' + name)
    return {'files': len(expected), 'tree_sha256': digest(expected)}


def runtime_inputs(package=PACKAGE):
    package = Path(package)
    model = package / 'model'
    root = model / 'runtime'
    with (model / 'sources/SOURCE_ARCHIVES_SHA256.csv').open(newline='') as f:
        sources = list(csv.DictReader(f))
    inventories, archives = {}, {}
    for row in sources:
        name = row['filename']
        if Path(name).name != name:
            raise ValueError('Invalid source archive name')
        path = model / 'sources' / name
        if path.stat().st_size != int(row['bytes']) or file_hash(path) != row['sha256']:
            raise ValueError('Parent archive mismatch: ' + name)
        archives[name] = row['sha256']
        if row['sha256'] not in _INVENTORIES:
            with zipfile.ZipFile(path) as z:
                entries = {}
                for info in z.infolist():
                    if info.is_dir() or not included(info.filename):
                        continue
                    p = PurePosixPath(info.filename)
                    if p.is_absolute() or '..' in p.parts or (info.external_attr >> 16) & 0o170000 == 0o120000:
                        raise ValueError('Unsafe parent archive entry')
                    with z.open(info) as stream:
                        entries[info.filename] = {'bytes': info.file_size,
                                                'sha256': hashlib.file_digest(stream, 'sha256').hexdigest()}
                _INVENTORIES[row['sha256']] = entries
        entries = _INVENTORIES[row['sha256']]
        if inventories.keys() & entries.keys():
            raise ValueError('Overlapping parent archive entries')
        inventories.update(entries)
    # Only initialize a genuinely absent runtime. Never repair or overwrite an
    # existing modified/incomplete tree while checking a sealed plan.
    if not root.exists():
        root.mkdir(parents=True)
        for row in sources:
            with zipfile.ZipFile(model / 'sources' / row['filename']) as z:
                for name in _INVENTORIES[row['sha256']]:
                    z.extract(name, root)
    return {'archives': archives, **verify_tree(root, inventories)}
