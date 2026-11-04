# 昇格検証

## 独立15seed再現

元5seedとは別に 91326--91340 を追加し、各leaf内paired・20葉を推論単位として再審判した。

- bigram: **-1.6581%**, 16/20葉改善, sign-flip p=0.016747
- ng: **-2.4870%**, 14/20, p=0.013617
- trigram: **-2.3336%**, 14/20, p=0.030052

3 n-gram family の Holm 補正後も3指標とも q<=0.040850。

## 全20seed

- bigram: **-2.1542%**, 16/20, p=0.002277
- ng: **-2.3367%**, 15/20, p=0.013830
- trigram: **-2.6271%**, 16/20, p=0.005253

regression/safety 5指標（bigram/ng/trigram/route56/bT leaf-excess）のHolm補正後:

- bigram q=0.011387
- ng q=0.041491
- trigram q=0.021011
- route56 q=1
- bT leaf-excess q=1

## Safety

全20seedで:

- SPACE_RAW: 完全不変
- route56: 完全不変
- bT leaf-excess: 完全不変
- length/width: 完全不変
- glyph-depth: +0.063%, p=0.793（中立）
- packing: 全PASS
- support violation: 0
- invalid row: 0
- segment retry: 0

H2_RAWは安定改善しなかったため、昇格根拠には使わない。
