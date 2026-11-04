# 正式統合仕様

## モデルID

`RMW1-BTI2-EHC2-DECOMP1-PUV-R4LEX-W2H2L4-K16`

## 親

- PUV U/V decomposition
- BODY non-prefix R4 coefficient: `0.85`
- bT leaf-excess: leaf-wise adaptive alpha from `{64,128,256}` using the frozen target-blind selection table

## 新規正式成分

W2 の **exact 4-glyph word** に限り、親 selector が選んだ anchor の H2 だけを再選択する。

1. 親モデルで通常どおり W2 anchor を確定する。
2. request-local SHA-256 side-stream RNG で sibling proposal を収集する。
3. sibling は anchor と `H1 / exact length / stable physical width` が同一でなければ棄却する。
4. K=16、最大 4096 draw。multiplicity は proposal probability として保持し、deduplicate しない。
5. H2 候補はさらに anchor H2 と glyph width が同一で、親 proposal support 上 `H1-H2-H3` および `H2-H3-H4` が正であることを要求する。
6. eligible sibling multiplicity 上で一様選択する。
7. 最終語は anchor の **H2だけ**を置換する。H1、H3以降、terminal、exact length、physical width は anchor と完全一致する。
8. eligible candidate が0なら anchorへfallbackする。

known3 residual table、W2 full-word replacement、W3 terminal bridgeは使用しない。

## RNG

sibling pool と H2 selection は親 RNG を消費しない dedicated SHA-256 side-stream を使用する。したがって後続差は乱数位置ずれではなく、最終語形差に由来する。

## 不採用

- W2 known3 residual reweighting
- full-word sibling replacement
- L3 H2 splice
- L5 H2 splice
- L6+ H2 splice
- K32/K64
- W3 terminal bridge/terminal weakening
