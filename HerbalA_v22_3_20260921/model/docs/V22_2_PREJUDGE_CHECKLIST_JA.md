# v22.2 審判前チェックリスト

このファイルは実装段階の停止点を固定する。

## 実装済み

- [x] 親 `HerbalA-v22r-W2B2` を自己完結パッケージとして継承
- [x] normal F1-LF scopeを単一関数で定義
- [x] scope中のみroute candidate scoreを0へneutral化
- [x] candidate bank生成は親のまま
- [x] plant-restart BODYを除外
- [x] paragraph-final FIRSTを除外
- [x] S_LF / BODY terminal rowを未導入
- [x] v22.2専用runner作成
- [x] v22.2専用validator作成

## 審判前に許可する検査

- Python compile
- 設定・model_id整合
- scope truth table
- 1ケース程度のmechanical smoke
- package SHA-256 / ZIP integrity

## まだ実行しない

- F1-LF NLL/JSD審判
- y/NMY/LR slope審判
- global bigram/trigram審判
- frequency spectrum比較
- 4-seed judge
- 200-run contest

`judge_status` は `NOT_RUN` のままにする。
