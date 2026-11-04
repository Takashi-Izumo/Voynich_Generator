# W2-B2 実装仕様 — HerbalA-v22r-W2B2

## 親

`HerbalA-v22r`（PARAH1-RUN32までの正式2026-09-17版）。

## 適用範囲

`MIDDLE × W2 × non-END × stable glyph length 3..5` のみ。

## 変更するもの

H2だけを次のtarget lawへ最大結合する。

- H2でもW2位置用CDF (`mo=3, wp=1`) を維持する。
- external H2 residualはOFF。
- target-leaf known-3 H2 residualは `tau=128` に強く縮約する。

## 固定するもの

H1、H3以降、terminal、exact glyph length、stable physical width、H2 glyph width、route/bT semantic state、packing、parent RNG。

介入はpost-commitで可視surfaceのH2だけを書き換える。親モデルのsemantic commit後に行うため、後続語へ連鎖しない。

## RNG

request-local SHA-256 side stream。namespaceは `V22R_W2_H2_B2_MINIMAL_V1`。

## 再現性

今回のマージ再監査で、seed 91701・20/20 bifoliaについて保存済みB2 `generated_rows_sha256` とbitwise一致。130/130適用requestも確率・選択結果まで一致した。

`model/validation/w2_b2/reproduction/` を参照。
