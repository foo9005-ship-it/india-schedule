# AWS Lambdaデプロイ（未着手）

`src/handler.py` の `handler(event, context)` をエントリポイントとしてデプロイする想定。

## 検討事項
- `unzip`/`zip` コマンドに依存（`generate_minutes.py`）→ Lambdaレイヤーまたは
  コンテナイメージ（`unzip`が入っているベースイメージ）での対応が必要
- `/mnt/skills/public/docx/scripts/merge_runs.py`（`MERGE_RUNS`定数）は
  現在のClaude Code実行環境に依存したパス。Lambda環境に移植する際は
  このスクリプト自体を `src/` 配下に同梱し、パスを差し替える必要がある
- 環境変数: `.env.example` を参照（`GOOGLE_SERVICE_ACCOUNT_JSON`, `DRIVE_FOLDER_ID`,
  `ANTHROPIC_API_KEY`, `ZOOM_WEBHOOK_SECRET_TOKEN`）
- Zoom Webhookの受け口として API Gateway + Lambda（`src/zoom_webhook.py`）を別途用意するか、
  1つのLambdaに統合するかは要検討

## TODO
- [ ] SAM / CDK / Terraform いずれかでIaC化
- [ ] コンテナイメージ or レイヤーの決定
- [ ] デプロイ手順のドキュメント化
