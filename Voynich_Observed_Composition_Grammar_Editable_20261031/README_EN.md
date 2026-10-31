# Voynich Herbal A: Corpus-Induced Composition Grammar

**English standalone LaTeX edition (31 October 2026)**

This is **not a grammar of the former VSL-2.1 program**. All rule inventories and counts in the books are extracted directly from the included **observed Voynich A word tokens and line annotations**. The prior generator's model parameters, random outputs, hidden state names, and full-word selection logic are not inputs to this edition.

The aim is **free manual composition** under an explicit, checkable set of surface grammar rules. It is not a decipherment and carries no assertion of meaning, phonology, or natural-language categories. Grade A composes with attested words in attested positional slots. Grade B allows narrowly constrained analogical new forms. Grade C is a clearly marked exploratory format.


## Reader-editable interpretation columns (new)

The entries in **`Voynich_A_Editable_Lexicon_EN.xlsx`** and **`data/attested_lexicon_editable.csv`** contain two additional fields beside each EVA form:

- **Meaning** — **empty for all 1,971 types on release**. Enter your own translation or semantic guess.
- **Part of Speech** — **empty for all 1,971 types on release**. Enter any grammatical category; no vocabulary or label set is imposed.

In the Excel workbook, **Lexicon!C2:C1972** and **Lexicon!D2:D1972** are the writable input columns, lightly shaded. The other sheets preserve observed frequencies, surface forms, route and positional evidence. The revised standalone LaTeX/PDF concordance adds the two blank right-hand columns on landscape pages for handwriting.

This publication **does not fill either field with a proposed decipherment**. User annotations are personal hypotheses, **not attested evidence**.

`data/attested_lexicon.csv` is the unchanged, corpus-derived source table. `data/attested_lexicon_editable.csv` is a separate editable full copy. To refresh manuscript measurements while **preserving already entered annotations by EVA form** in the editable CSV, run:

```bash
python tools/derive_corpus_evidence.py
python tools/prepare_lexicon_annotations.py
python tools/build_latex_books.py
lualatex Voynich_A_Attested_Lexicon_EN.tex
lualatex Voynich_A_Attested_Lexicon_EN.tex
```

**Do not expect Excel and CSV to auto-sync**: edit either file and keep that version as your working dictionary. The bundled Python preparation script only merges annotations already saved in the editable CSV; it does not read your `.xlsx`. To preserve Excel edits when rebuilding from CSV, export them into the editable CSV first.

## Documents

- `Voynich_A_Induced_Compositional_Grammar_EN.tex` and `.pdf` -- 16-page independent compositional grammar with worked new paragraphs.
- `Voynich_A_Attested_Lexicon_EN.tex` and `.pdf` -- 74-page landscape-annotated 1,971-type word index and 715-route reference.
- Both TeX files include all their table data. Neither has `\\input`/`\\include` dependencies. Compile each twice with LuaLaTeX.

## Reproducible source and tools

- `data/source_pureA85_observed_tokens.csv.gz` -- 6,836 actual word tokens, extracted from the position-annotated supplied project corpus. The file is included for complete independent reproduction.
- `data/attested_lexicon.csv` -- complete word type-frequency and role-count table.
- `data/shared_routes.csv` -- route count table and attested carrier examples.
- `data/word_internal_bigrams.csv`, `data/word_internal_trigrams.csv` -- observed glyph transitions, no word-boundary crossing.
- `data/attested_single_substitutions.csv` -- co-attested word-form analogies.
- `tools/derive_corpus_evidence.py` -- **recomputes** all tables directly from the supplied tokens.
- `tools/recheck_l2_l3.py` -- exploratory 5,000-replicate line-family test.
- `tools/check_composition.py` -- **validator, not generator**.
- `tools/self_test.py` -- 10 checks.
- `examples/` -- human-composed Grade A and Grade B examples.

## Quick start

```bash
python tools/check_composition.py examples/grade_A_original.eva --level A
python tools/check_composition.py examples/grade_B_one_edit_original.eva --level B
python tools/check_composition.py --list-role W2
python tools/self_test.py
```

To write your own text, use space-separated EVA words, one physical line per line of the file, and a blank line between paragraphs. In the conservative core, begin with PHW ... F1_LF, use HEAD W2 BODY* LF on any number of internal lines, and finish with PF_HEAD PF_BODY* PF_LF. Choose each word yourself from the indexed role inventory. Optional graphic 4-6-glyph family continuity is **not a mandatory grammatical constraint**.

## Scientific status

Pure Herbal A, 85 pages, 22 bifolia, 165 paragraphs, 1,090 lines, 6,836 tokens, 1,971 surface types. Core 3+-line role-annotation subset: 164 paragraphs/6,816 tokens. The observed 23-unit segmentation uses ch/sh/cfh/ckh/cph/cth as single glyphs. There are 229 word-internal bigram types and 881 trigram types. Absence from these finite samples does **not** establish absolute historical impossibility. Nothing in the books supplies an attested English translation of a Voynich word.
