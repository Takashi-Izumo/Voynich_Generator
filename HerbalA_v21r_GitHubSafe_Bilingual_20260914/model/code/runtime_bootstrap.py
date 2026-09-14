from __future__ import annotations

from pathlib import Path
import hashlib
import json
import os
import zipfile

ROOT = Path(__file__).resolve().parents[1]
REPO_ROOT = ROOT.parent
SOURCE_MANIFEST = ROOT / 'SOURCE_ARCHIVES.json'

HANDOFF_NAME = 'RMW1_BTI2_EHC2_DECOMP1_PUV_HANDOFF_COMPACT_20260912.zip'
PARENT_NAME = 'EHC1_E1GLOBAL_FULL_20260911.zip'


def _runtime_root() -> Path:
    raw = os.environ.get('VOYNICH_V21R_RUNTIME_DIR')
    if raw:
        return Path(raw).expanduser().resolve()
    return ROOT / 'runtime'


RUNTIME = _runtime_root()
HANDOFF_ROOT = RUNTIME / 'RMW1_BTI2_EHC2_DECOMP1_PUV_HANDOFF_COMPACT_20260912'
PARENT_ROOT = RUNTIME / 'EHC1_E1GLOBAL_20260911'
STAGE6 = HANDOFF_ROOT / 'current_model/RMW1_BTI2_EHC2_DECOMP1_STAGE6_20260911'


def _load_source_manifest() -> dict:
    return json.loads(SOURCE_MANIFEST.read_text(encoding='utf-8'))


def _sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open('rb') as f:
        for chunk in iter(lambda: f.read(1 << 20), b''):
            h.update(chunk)
    return h.hexdigest()


def source_search_dirs() -> list[Path]:
    """Return deterministic source-archive search locations.

    Search order is intentionally narrow so that the model never silently picks
    an unrelated archive from an arbitrary directory.
    """
    dirs: list[Path] = []
    env_dir = os.environ.get('VOYNICH_V21R_SOURCE_DIR')
    if env_dir:
        dirs.append(Path(env_dir).expanduser().resolve())
    dirs.extend([
        ROOT / 'sources',
        REPO_ROOT / 'release_assets',
        REPO_ROOT / 'external_sources',
    ])
    out: list[Path] = []
    seen: set[str] = set()
    for d in dirs:
        key = str(d)
        if key not in seen:
            out.append(d)
            seen.add(key)
    return out


def resolve_source_archive(name: str, verify: bool = True) -> Path:
    manifest = _load_source_manifest()
    if name not in manifest:
        raise KeyError(f'archive not declared in {SOURCE_MANIFEST}: {name}')
    expected = str(manifest[name]['sha256'])
    checked: list[str] = []
    for directory in source_search_dirs():
        candidate = directory / name
        checked.append(str(candidate))
        if not candidate.is_file():
            continue
        if verify:
            actual = _sha256(candidate)
            if actual != expected:
                raise RuntimeError(
                    f'SHA-256 mismatch for {candidate}\n'
                    f'expected: {expected}\nactual:   {actual}'
                )
        return candidate
    joined = '\n  - '.join(checked)
    raise FileNotFoundError(
        f'Required v21r source archive not found: {name}\n'
        f'Searched:\n  - {joined}\n\n'
        'Download the release assets, then either place both ZIP files in '
        'model/sources/, place them in repository-level release_assets/, or set '
        'VOYNICH_V21R_SOURCE_DIR to the directory containing them.'
    )


def source_status() -> dict:
    manifest = _load_source_manifest()
    status = {}
    for name, meta in manifest.items():
        record = {
            'expected_sha256': str(meta['sha256']),
            'role': meta.get('role'),
            'found': False,
            'path': None,
            'sha256_match': None,
        }
        try:
            p = resolve_source_archive(name, verify=True)
            record.update(found=True, path=str(p), sha256_match=True)
        except FileNotFoundError:
            pass
        status[name] = record
    return status


def _extract_once(archive_name: str, marker: Path) -> None:
    if marker.exists():
        return
    archive = resolve_source_archive(archive_name, verify=True)
    RUNTIME.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(archive) as zf:
        zf.extractall(RUNTIME)
    if not marker.exists():
        raise FileNotFoundError(
            f'Archive extracted but expected runtime marker is missing: {marker}'
        )


def prepare_runtime():
    _extract_once(HANDOFF_NAME, HANDOFF_ROOT / 'README_START_HERE_JA.md')
    _extract_once(PARENT_NAME, PARENT_ROOT / 'README_JA.md')
    return HANDOFF_ROOT, PARENT_ROOT, STAGE6
