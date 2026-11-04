# short BODY H2 global化 — 審判前監査

## 1. no-op同一性

`known3_strength=1.0` の監査armを seed 91601 / 20 bifolia で生成し、親 `PRETERM_QMAP9` の保存hashと比較した。

- generated rows hash: 20/20 完全一致
- surface commits hash: 20/20 完全一致

したがって介入係数を親値へ戻した場合、追加コード自体は挙動を変えない。

## 2. 修正版の1-seed機械監査

seed 91601 / 20 bifolia:

- short BODY H2 intervention opportunities: 354
- actual H2 changes: 24
- output hash changed: 15/20 bifolia
- packing exact: 20/20
- support violations: 0
- invalid rows: 0

変更はH2のみ。コードassertにより、H1 / H3+ / exact length / H2 glyph width / physical word widthを固定している。

## 3. 変更例

- `dal -> dol`
- `shy -> sho`
- `chey -> choy`
- `chlor -> cheor`

いずれもH2だけが変わる。

## 4. 審判状態

**blind judgeは未実行。**

本版は「実装・再現・機械監査完了、審判待ち」で停止する。
