# HerbalA-v22.3 Stage3D-r1 candidate

Stage3Gで検出した1件のroute-state leakageを修正した自己完結候補。

## 修正

- `commit_word`: v22.2のcommit pathをそのまま通し、route/MapStateには `v22_2_child_seq` をcommit
- `commit_surface`: Stage3D final childだけをvisible surfaceと`prev_terminal`へcommit
- `commit_surface`ではroute `current` 不変をassert

## 再監査

- Stage3D static/logical: PASS 21/21
- Stage3E-r1 runtime: PASS 910/910
- Stage3F-r1 canonical paired: 410,379 comparisons / failures 0; route/RNG 20/20 exact
- Stage3G-r1: 10 valid seeds × 20 bifolia = 200 paired runs; 4,120,232 mechanical comparisons / failures 0
- route trace exact: 200/200
- route final state exact: 200/200
- BH-significant global regression: 0

正式 `HerbalA-v22.3` 昇格はまだ行わない。旧Stage1/2 component artifactとのsource-law provenance照合が未解決のため、stable parentは `HerbalA-v22.2` のまま。
