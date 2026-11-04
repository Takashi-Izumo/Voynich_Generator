# Paragraph H1 continuous running residual 実装記録

## 親モデル

完全固定した親は：

`v21r + PRETERM_QMAP9 + SHORTBODY-H2-GLOBAL`

です。今回、H2 page-local補正、H3補正、LF/bT/PRETERM/width/packing/route5/6/RNG構造は変更していません。

## 採用した状態モデル

外部保留対決では、有限離散stateはbaselineを悪化させ、continuous running residual と decay memory が改善しました。decayの追加利得はcontinuousに対して有意でなかったため、最小モデルとして：

- continuous running residual
- decayなし
- shrinkage lambda = 32
- paragraph境界でneutral reset

を採用しました。

## 因果順序

状態更新は完成頁を参照しません。

1. paragraph開始時にstateをneutralへreset。
2. 現在行のBODY H1は、その行より前に**完了したeligible行だけ**から作ったstateを参照。
3. 現在行のeligible H1はpending bufferへ入る。
4. 次の物理行開始時にpendingをrunning stateへflush。
5. paragraphが変わればstateを破棄してreset。

同じ行の先行語は、その行自身のH1選択には使いません。

## baseline残差

running stateは、単純なH1頻度ではなく、target-blind baselineからの残差です。

baselineは検定と同じ：

- exact stable glyph length
- boundary / previous terminal T
- external Pure A
- target pageを除くleaf-known-3

を使います。

各完了済み行までの観測H1 countを O、baseline期待を E、事象数を n とすると、

`m = E / n`

`S = (O + 32*m) / (n + 32)`

`gain = S / m`

を次行H1へ掛けます。

## H1-only intervention

今回の最重要安全条件です。

H1変更候補は、親が生成した完成stable wordに対して：

- H1だけ変更
- H2+完全固定
- exact glyph length固定
- H1 physical width固定
- total physical width固定

を要求します。

さらに、H1変更は**親のpacking / rare glyph / route commitが終了した後**に書き込みます。

そのため：

- packingは親と同一
- rare glyph処理は親と同一
- route5/6/current memoryは親anchorでcommitされ同一
- parent RNGは無消費

です。

実装は `code/paragraph_h1_sampler.py`、transactional stateは `code/paragraph_h1_state.py` です。

## no-op

`PARAH1_NOOP` はparagraph state用state classを通しますがH1 interventionを無効化します。現行親 `SHORTBODY-H2-GLOBAL` と generated rows / surface commits が20/20完全一致することを検証しています。

## 審判

blind judgeは実行していません。
