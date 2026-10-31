# ヴォイニッチ草本A・実測語から帰納した自由作文文法

**2026年10月31日 / 英語LaTeX版・単独再現パッケージ**

## 今回の改訂の意味

これは以前の「VSL-2.1生成器の内部動作を説明する文法書」を**置き換える独立の文法書**です。語形・位置・部分経路は実際に転写されたヴォイニッチ語から直接再集計し、**生成器の確率表、隠れた状態、出力サンプルは使用していません**。

目的は、固定的な例文の模写ではなく、**文法で許可された語を自分で選び、好きな数の新しい行・段落を作文すること**です。

ただし、未解読のため「文法適合」とは **語形・語内接続・位置・段落構造の適合**を意味し、ヴォイニッチ語として意味が通る／当時の話者に理解されることは保証しません。名詞、動詞、時制、格、語義は確定していません。

## 意味・品詞の自由記入欄（改訂）

**全1,971語の `Meaning`（意味）と `Part of Speech`（品詞）は、初期状態ですべて空欄**です。研究者・読者が好きな語義や品詞を後から記入できます。確定した訳や品詞を著者側で割り当てることはしません。

- `Voynich_A_Editable_Lexicon_EN.xlsx`：**Lexicon シートのC列・D列**に自由記入。色付き空欄を設けています。
- `data/attested_lexicon_editable.csv`：Excel以外でも編集できる全1,971語の辞書。両列は空文字です。
- `Voynich_A_Attested_Lexicon_EN.tex`／`.pdf`：元の頻度・位置情報は残し、空欄の2列を設けた英語版索引。印刷して手書きすることもできます。

`data/attested_lexicon.csv` は**改変しない原本の実測表**として保持します。実測を更新するときは `python tools/derive_corpus_evidence.py` に続いて `python tools/prepare_lexicon_annotations.py` を実行すると、**編集用CSV内の既存の記入を語形キーで維持**して集計値だけを更新できます。`.xlsx`で入力した内容はCSVに自動反映されません。Excelを編集する場合はそのファイル自体を保存するか、編集用CSVへ書き出してから再構築してください。記入された訳は利用者の仮説であり、手稿から実証された意味ではありません。

## 完成版

- `Voynich_A_Induced_Compositional_Grammar_EN.tex`：**文法書（英語、TeX単独）**
- `Voynich_A_Induced_Compositional_Grammar_EN.pdf`：上記のPDF（16ページ）
- `Voynich_A_Attested_Lexicon_EN.tex`：**実在1,971語型と共有経路715件の完全索引（英語、TeX単独）**
- `Voynich_A_Attested_Lexicon_EN.pdf`：上記のPDF（74ページ）
- `data/attested_lexicon.csv`：語形、実測回数、字形分節、頁、葉、各位置の頻度、出典行（実測原本）
- `data/attested_lexicon_editable.csv`：記入欄付き全1,971語辞書
- `Voynich_A_Editable_Lexicon_EN.xlsx`：編集しやすいExcel辞書（意味・品詞の空欄付き）
- `data/shared_routes.csv`：4～6字形共有経路715件と複数の実在carrier例
- `data/word_internal_bigrams.csv`：観測された229種類の語内字形隣接ペア
- `data/word_internal_trigrams.csv`：観測された881種類の語内3字形経路
- `data/attested_single_substitutions.csv`：実在語同士の一字形置換対応
- `tools/check_composition.py`：**ユーザー自身の文章の適合判定**（生成機能なし）
- `tools/derive_corpus_evidence.py`：統計表を元コーパスから独立再計算
- `tools/recheck_l2_l3.py`：第二行〜第三行の探索的共有経路検定
- `tools/build_latex_books.py`：TeX全内容の再構築
- `tools/self_test.py`：自動テスト10件
- `examples/grade_A_original.eva`：新規に作文した2段落（実在語のみ）
- `examples/grade_B_one_edit_original.eva`：未観測語形 `doin` の一編集を許す拡張作文例
- `examples/COMPOSITION_WORKSHEET_EN.md`：作文用のワークシート
- `data/source_pureA85_observed_tokens.csv.gz`：本文表の原入力。旧生成器の同梱入力から**データ部分のみ**引用（生成器コード・モデルは未使用）

## 自由作文ルール（要約）

- **第一行**： `PHW  F1_BODY*  F1_LF`
- **第二行以降の中間行**：`HEAD  W2  BODY*  LF`
- **最終行**：`PF_HEAD  PF_BODY*  PF_LF`
- 行は改行、段落は空行で区切ります。中間行は何行でも、内部語 `BODY` は何語でも追加できます。厳格版は3行以上の段落を対象とした保守的な教則文法です。
- A級：位置ごとに実在する単語を選ぶだけ。自分で自由に作文できます。
- B級：実在語から `ch/sh, k/t, l/r, o/a` などの一編集を行う新語も、実測語内bigram・trigramを保持する場合に限り追加許可。
- C級：実験用。語内部bigram/trigramの合法性のみで組み合わせた形は、実在語でも確定した文法でもありません。
- 第二行→第三行の共有4字形経路、第一行頭のgallowsなどは **推奨傾向であり、必須ではありません**。

## 実行（Python標準ライブラリのみ）

ZIPを解凍し、そのディレクトリで：

```bash
python tools/check_composition.py examples/grade_A_original.eva --level A
python tools/check_composition.py examples/grade_B_one_edit_original.eva --level B
python tools/check_composition.py examples/grade_A_original.eva --level A --json
python tools/check_composition.py --list-role PHW
python tools/self_test.py
python tools/derive_corpus_evidence.py
python tools/recheck_l2_l3.py
```

自分でテキストファイルを作り、スペース区切りの語を改行で並べ、空行で段落を区切ってチェッカーに渡せます。

TeXはそれぞれ外部入力ファイルを参照せず、**単独でLuaLaTeXによりコンパイル**できます。`lualatex` を2回実行すると目次とページ数も確定します。

## 実測の範囲と注意

対象は**純草本A85面／22 bifolia／165段落／1,090行／6,836実測語／1,971異なり語型**です。23字形分節。これは別の正規化版（6,853語、28字形）や草本Bには自動的に適用できません。

観測された語内部bigram229種類、trigram881種類は**この転写と範囲での事実**です。見つからなかった組合せを歴史的な絶対禁止として立証したものではありません。共有経路715件は少なくとも2語型、2面、3トークンで成立する4〜6字形の連続部分列という**操作的な定義**です。

4行以上の142段落における第二行→第三行の共有4字形経路は、実測161件、内部行だけを入れ替えた5,000回の平均142.106、片側plus-one p=0.03559。探索的であり、意味上の主題継承は未確認です。
