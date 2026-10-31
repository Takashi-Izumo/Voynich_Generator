# Freely writing in the observable Voynich-A surface grammar

You do not need to follow any fixed sample text. You choose every attested word yourself.

## A core composition outline (three or more lines)

```text
[PHW] [any number of F1_BODY words] [F1_LF]
[HEAD] [W2] [any number of BODY words] [LF]
[HEAD] [W2] [any number of BODY words] [LF]  <-- optional and repeatable
[PF_HEAD] [any number of PF_BODY words] [PF_LF]
```

Use the `attested_lexicon.csv` table or run `python tools/check_composition.py --list-role HEAD` (or other role codes) to choose an actual word from that category. There is no subject-verb-object requirement: the meanings of these words are unknown.

## Expressive choices

- Choose a short or long paragraph: the number of ordinary middle lines is freely expandable.
- Use high-frequency words for familiar-looking passages or less common attested words for diversity.
- Use pairs such as `chol/chor` or `qokchy/qotchy` for graphical contrast.
- Optionally choose a path from `shared_routes.csv` and place different carriers on lines 2 and 3.
- You can drop or switch the path later; this is not a compulsory anaphora rule.
- Use grade B if and only if you want a clearly labelled, one-edit new graphic form; its meaning is not known.
- Place a blank line between separate paragraphs.

## Check a new passage

```bash
python tools/check_composition.py my_passage.eva --level A
```

A PASS means that the formal, corpus-based *surface composition standard* is satisfied. It does **not** mean authentic historical grammaticality or a verifiable translation.
