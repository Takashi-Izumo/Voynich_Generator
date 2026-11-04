# v21r Stage 2 実装・再現監査

## 判定

**PASS** — `SAFE_LEFT` を Stage 1 の互換基盤へ実装し、既存の W2 exact-L4 LEFT-only 5-seed 検定を完全再現した。

## 唯一の挙動変更

v20r の W2 exact-L4 H2 splice では、候補 H2 に対して次の両 bridge support を要求していた。

- LEFT: `H1-H2-H3 > 0`
- RIGHT: `H2-H3-H4 > 0`

Stage 2 `SAFE_LEFT` は **RIGHT 条件だけを削除**する。

維持するもの:

- W2 only / exact glyph length 4
- K=16, max draws=4096
- H1固定
- exact glyph length固定
- stable physical width固定
- H2 glyph width固定
- H3以降・terminalをanchor固定
- sibling multiplicity保持
- eligible multiplicityから一様選択
- fallbackはeligible 0ならanchor
- `W2H2SPLICE_POOL_V1` / `W2H2SPLICE_SELECT_V1` のRNG namespace
- W2-L4 bTを含む親側挙動

## 再現検証

5 seed (`91321..91325`) × 20 complete bifolia = 100 casesを再生成。

以前のLEFT-only検定との照合:

- 9 judges × BOTH/LEFT absolute margin = 18項目
- LEFT mechanical totals = 5項目
- 合計 **23/23 完全一致**

Stage 2 LEFT mechanical totals:

- splice events: 542
- changed: 162
- changed rate: 0.2988929889
- zero fallback: 5
- sibling pool multiplicity: 8640
- eligible multiplicity: 7069
- eligible/event: 13.0424354
- RIGHT-off audit events: 542/542
- support violations: 0
- invalid rows: 0
- packing: 100% PASS

## BOTH vs LEFT（同一5 seeds）

低いabsolute marginが良い。LEFT−BOTHの改善量:

- H2_RAW: -0.0000455, p=.594
- bigram: +0.0005050, p=.0858
- ng: +0.0003110, p=.1386
- trigram: +0.0003044, p=.2604

RIGHTを追加する利益は再現されず、平均はn-gram 3指標すべてLEFT側。

## Stage 1互換性

`V20_COMPAT` は別クラスとして残し、Stage 2実装後も smoke case `A:2 / run91321` で公式v20r参照hashと一致した。

## 結論

Stage 2は **SAFE_LEFT固定対照として使用可能**。Stage 3では、このコードを変更せずにW2 SLOT table builderを追加する。
