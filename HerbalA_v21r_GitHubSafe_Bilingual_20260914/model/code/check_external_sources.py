from __future__ import annotations

import json
import sys

from runtime_bootstrap import source_status


def main() -> None:
    status = source_status()
    ok = all(v['found'] and v['sha256_match'] for v in status.values())
    print(json.dumps({'status': 'PASS' if ok else 'MISSING', 'archives': status}, ensure_ascii=False, indent=2))
    raise SystemExit(0 if ok else 2)


if __name__ == '__main__':
    main()
