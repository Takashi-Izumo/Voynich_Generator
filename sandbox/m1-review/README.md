# M1共有sandbox

共有先は `Takashi-Izumo/Voynich_Generator` の **`sandbox/m1-review` ブランチ**です。mainとは別に、実装側と検証側のクラウドが同じコードと依頼・報告を共有します。ZIPをチャット間で添付し直す必要はありません。

```text
experiments/m1_pf/               # 現在の実装（v2、実ファイル）
experiments/pf_generation/       # 新しいPF gate/語長法則・第1比較の実装
experiments/pf_controls/         # 原版BASEから隔離した64枝PF能力対照replay
sandbox/m1-review/
  status.json                   # 実装側が管理する現在地
  requests/018-pf-controls-independent-check.md # 現在の独立確認依頼
  designs/007-pf-generation-v1/ # 3案の評価・設計・入力監査
  designs/012-pf-review-corrections/ # CAL能力対照の設計訂正
  designs/017-pf-controls-v1/   # 64枝replay・支持内対照・新能力基準の実装設計
  implementation/014-pf-r2-contextfix/ # raw候補帰属修正の検証記録・manifest
  implementation/017-pf-controls-v1/ # 対照replayの封印plan・smoke・負例・manifest
  reports/001-forwarded-v1.md    # ユーザー経由で届いた旧版の指摘
  reports/<review-id>/...        # 検証側が追加する報告・再現手順
  responses/                    # 実装側の受領・確認記録
  templates/REVIEW_REPORT.md     # 検証報告のひな形
```

## 検証側クラウドの開始

既存チェックアウトと未保存変更を確認・保存してから、同リポジトリで次を実行してください。追加のworktreeは不要です。

```bash
git fetch origin refs/heads/sandbox/m1-review:refs/remotes/origin/sandbox/m1-review
git switch --track origin/sandbox/m1-review
```

ローカルに同名ブランチが既にある場合は `git switch sandbox/m1-review` に続けて `git pull --ff-only origin sandbox/m1-review` を使います。強制reset・force pushは使用しません。

`status.json` と指定された `requests/` の依頼を読み、開始時の `git rev-parse HEAD` を報告に記録してください。実装は既に `experiments/m1_pf/` にあるため、ZIPのpayloadを重ねてコピーしません。凍結CALモデルのみ必要な場合は、依頼に記載の公開ZIPから取得できます。

## 結果の返し方

検証側は `reports/<重複しないreview-id>/REVIEW.md` に報告を追加します。必要な小さい再現スクリプト・テキストログも同じディレクトリへ置けます。大きな生成物、真正/疑似の正解キー、parent archive、credentialは置きません。

```bash
git add sandbox/m1-review/reports/<review-id>/
git diff --cached --name-only
git commit -m "Report independent M1 v2 review"
git push origin HEAD:refs/heads/sandbox/m1-review
```

この共有sandboxでは、**検証報告だけのcommit/pushはユーザーの依頼する受け渡し手段**です。以前のZIP依頼にある一律のcommit/push禁止より、この報告手順を優先します。検証側は実装・原版・審判・status・依頼文を変更しません。実装側は受け取った報告を改変せず、新しい修正と次の依頼を追加します。

他クラウドのpushで通常pushが拒否された場合はfetchし、自分の未公開報告commitだけを最新sandboxへrebaseして通常pushします。競合したら変更を保存して停止・報告し、履歴を書き換えません。同じファイルを両者で編集せず、報告と依頼には新しい名前を使います。

## 運用範囲

- M1本比較は別途ユーザーが実行を指示した記述的な開発比較として完了し、報告004と追加診断・提案005を受領しました。現在地は `status.json`、確認内容は `responses/006-full-comparison-and-proposal-review.md` を参照してください。
- M1の2候補を現行v22.3の置換として推奨する結果には至っていません。その後の3案の評価・設計は `designs/007-pf-generation-v1/`、最優先案の実装は `experiments/pf_generation/` にあります。
- 第一案の独立検証010では通常生成・fit・恒等対照・CAL接続を再現できましたが、介入ログ欠落を新規監査が受理するR1があり、要修正となりました。
- 再検証013ではR1解消と訂正012を独立に確認しましたが、raw行の候補ラベルと結合先の矛盾を見逃すR2が追加されました。
- R2を5項目の型付きcontextの直接照合で修正し、報告015で130テスト・新規36面・固定CAL接続・R2/R1負例を独立PASSしました。既存生成法則・予測/採点の保存も確認されています。
- 能力対照のnear/base/far CAL順位は訂正012を参照してください。元の生NLLの大小をCALの順位へ直結させず、旧75%能力基準を無条件に適用しません。
- 報告016の契約に沿い、64枝replay・外部16葉proxy・支持内donor選択・真正面対改変面export・全recordのfresh再生監査・固定CAL能力判定を独立packageへ実装しました。依頼018で独立確認し、検証側が全対照と能力確認後の本比較を実行します。実装側は機構smokeまでを担当します。
- 個別末字・SPACEの生成器本体studyは後続です。smoke PASSで自動採用・昇格・mainへのmergeを行いません。
- クラウド間の自動起動・常駐ポーリングは設定していません。別チャットを開始/再開した時にfetchし、GitHub上の最新依頼・報告を読みます。
- sandboxは別リポジトリや秘密領域ではなく、同じリポジトリの専用ブランチです。
