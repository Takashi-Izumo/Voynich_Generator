# v21r + PRETERM Release Notes

- 親：`SAFE_LEFT_BT_OFF`
- 新候補：`PRETERM_QMAP9`
- 追加作用：低残幅・非LF BODYのterminal family holdingのみ
- 追加しなかった作用：narrow glyph bias（親packingで既に回収）
- literal runtime R<=6：3-seedでは変更0、非採用
- prevalence-mapped runtime R<=9：20-seedへ進行
- 20-seed：packing 400/400、support 0、invalid 0
- global judge：全差±2.2%以内、paired有意悪化なし
- targeted：low n/m/y target error 約86%縮小、close-score target error 約43%縮小

判定：`PROMOTE_AS_V21R_PRETERM_CANDIDATE`
