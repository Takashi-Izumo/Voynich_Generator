# HerbalA v21r + PRETERM 実装仕様

## 1. 親モデル

親は Stage 4 終了時点の `SAFE_LEFT_BT_OFF`。既存のW1/W2/BODY/LF grammar、R4、bT、SPACE、packing、HEAD、W2 H2 spliceは変更しない。

## 2. 実測で見つかった残差

外部foldで固定した境界（中央値 5.75）より低い通常BODY語では、同一bifolium×同一語長で比較して、

- 平均glyph幅が低下
- 4幅glyph率が低下
- terminal `n/m/y` が低下
- terminal `l/r` が上昇
- 語内部non-END遷移と次語H1は変化しない

という局所的なpreterminal holdingが確認された。

## 3. 二重補正監査

親v21rを calibration seeds `91401–91403` ×20 bifoliaで再生成したところ、packingだけで低残幅語の細幅化は既に十分強く出ていた。このため **narrow glyph biasは追加しない**。

一方、terminal holdingは不足していたため、terminalだけを補正する。

## 4. runtime閾値

実測の5.75はleave-one-line-out推定容量座標であり、生成器の整数 `rstart` と同一尺度ではない。

実測BODY低帯の比率は `88/801 = 10.99%`。親生成器では、

- runtime `R<=6`: 約0.76%
- runtime `R<=9`: 約11.34%

だったため、主候補は **`R<=9`** とする。literal R6は3-seed controlとして残し、実際にはほぼ発火しなかった。

## 5. PRETERM_QMAP9

適用条件：

- `role=BODY`
- `board=BODY`（実際のLF語には適用しない）
- `end=False`
- `rstart<=9`
- 語長2以上

固定するもの：

- H1からterminal直前までのprefix全部
- exact glyph length
- terminal glyph physical width
- total physical word width
- packing fit

したがって内部trigramを直接書き換えない。

terminal close scoreを、

- `n/m/y = +1`
- `l/r = -1`
- その他 = 0

とし、

`weight *= exp(-0.29704000178961015 * close_score)`

で局所分布を傾ける。

選択はparent-local分布とtilted分布のmaximal coupling。lambda=0なら厳密no-opとなり、変更率を最小化する。

RNGは `V21_PRETERM_TERMINAL_QMAP9_V1` のSHA-256 request-local side stream。親RNGとsemantic stateは消費・変更しない。
