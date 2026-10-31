#!/usr/bin/env python3
"""Prepare/update editable Voynich lexicon fields without discarding user annotations.

The original attested_lexicon.csv is corpus-derived and stays unchanged. The
editable CSV is NOT overwritten blindly: existing Meaning / Part of Speech
values are merged by complete EVA form, while fresh manuscript counts are
updated from the corpus-derived base table.
Only Python standard library is required.
"""
from __future__ import annotations
import csv
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BASE = ROOT / "data" / "attested_lexicon.csv"
EDIT = ROOT / "data" / "attested_lexicon_editable.csv"
EDITABLE = ("Meaning", "Part of Speech")

def read_rows(path):
    if not path.exists(): return [], []
    with path.open(encoding="utf-8-sig", newline="") as fp:
        reader = csv.DictReader(fp)
        return list(reader), list(reader.fieldnames or [])

def main():
    base, columns = read_rows(BASE)
    if not base: raise RuntimeError(f"No base lexicon at {BASE}")
    previous, _ = read_rows(EDIT)
    by_form = {row["form"]: row for row in previous}
    fields = columns[:2] + list(EDITABLE) + columns[2:]
    with EDIT.open("w", encoding="utf-8", newline="") as fp:
        out = csv.DictWriter(fp, fieldnames=fields, extrasaction="ignore")
        out.writeheader()
        for row in base:
            old = by_form.get(row["form"], {})
            newrow = {**row, **{key: old.get(key, "") for key in EDITABLE}}
            out.writerow(newrow)
    after, _ = read_rows(EDIT)
    assert len(after) == len(base)
    assert all("Meaning" in x and "Part of Speech" in x for x in after)
    print(f"Prepared {len(after):,} entries; preserved existing annotations by form.")

if __name__ == "__main__": main()
