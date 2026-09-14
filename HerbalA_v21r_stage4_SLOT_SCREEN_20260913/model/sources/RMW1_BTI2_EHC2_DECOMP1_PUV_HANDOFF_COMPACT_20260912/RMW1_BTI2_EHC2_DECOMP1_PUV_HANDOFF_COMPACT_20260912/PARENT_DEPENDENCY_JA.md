# 親ランタイム依存

現行PUVの再生成には次の凍結親が必要:

- filename: `EHC1_E1GLOBAL_FULL_20260911.zip`
- SHA-256: `cf8ec127ab584a8460c3c02aa4f3a5b2a7f01a328a9b3568f58d6ce0c53c025f`

この親ZIPは本Project内に別ファイルとして存在する。

展開後、環境変数:

```bash
export EHC2_STAGE6_PARENT=/path/to/EHC1_E1GLOBAL_20260911
```

を設定する。

親ZIP自体はサイズ約205MBのため、このcompact handoffには重複同梱していない。
