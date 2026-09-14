# AWS Lambdaデプロイ

`src/handler.py` の `lambda_handler(event, context)` を、コンテナイメージのAWS Lambda
としてデプロイする。API Gateway(HTTP API)経由でZoomのWebhookを受ける構成。

## 解決済みの検討事項

- ~~`unzip`/`zip`コマンド依存~~ → `infra/lambda/Dockerfile`でLambdaのPythonベースイメージに
  `zip`/`unzip`を追加してビルドする
- ~~`/mnt/skills/public/docx/scripts/merge_runs.py`への依存~~ → `src/vendor/merge_runs.py`
  として同梱済み。`generate_minutes.py`はClaude Codeのdocxスキルが存在すればそちらを、
  なければvendor版を自動的に使う（`generate_minutes.py`冒頭の`MERGE_RUNS`定数を参照）。
  実際にvendor版でdocx生成が正しく動作することは2026-09-14に確認済み
- 環境変数: `template.yaml`のParametersとして定義済み（`.env.example`と同じ4つ:
  `GOOGLE_SERVICE_ACCOUNT_JSON`, `DRIVE_FOLDER_ID`, `ANTHROPIC_API_KEY`,
  `ZOOM_WEBHOOK_SECRET_TOKEN`）
- Zoom Webhookの受け口とパイプライン本体は`src/handler.py`の`lambda_handler()`に統合済み
- IaC: AWS SAM（`template.yaml`）を採用

## ⚠️ このセッションでは実施できなかったこと

このリポジトリを操作している環境にはDockerデーモンおよびAWS CLI/SAM CLIがなく、
実際の `docker build` / `sam deploy` はユーザー側の環境で実行する必要がある。
Pythonロジック自体（`generate_minutes.py`がvendor版`merge_runs.py`で正しく動作すること）は
コンテナを使わない形で動作確認済み。

## デプロイ手順

### 0. 前提

- AWS CLIの認証情報が設定済みであること（`aws configure`等）
- Docker Desktop等、ローカルでDockerが使えること
- [AWS SAM CLI](https://docs.aws.amazon.com/serverless-application-model/latest/developerguide/install-sam-cli.html) をインストール済みであること

### 1. ビルド

```bash
cd kitayama-minutes
sam build --template infra/lambda/template.yaml
```

初回はDockerでコンテナイメージをビルドするため数分かかる。

### 2. デプロイ

```bash
sam deploy --guided \
  --template infra/lambda/template.yaml \
  --stack-name kitayama-minutes
```

対話式プロンプトで以下を聞かれるので入力する:

- `GoogleServiceAccountJson`: サービスアカウントJSON鍵の中身（`infra/gcp/service_account_setup.md`参照）
- `DriveFolderId`: 未入力ならデフォルト値（`議事録_自動生成`フォルダ）が使われる
- `AnthropicApiKey`: Anthropic APIキー
- `ZoomWebhookSecretToken`: Zoom AppのSecret Token（先にZoom App作成が必要。
  `README.md`の「Zoom側の設定」参照。仮の値でデプロイし、後から
  `sam deploy`を再実行して更新してもよい）
- `Confirm changes before deploy`: `Y`
- `Allow SAM CLI IAM role creation`: `Y`
- 以降はデフォルトのまま進めてよい

デプロイが完了すると、出力(Outputs)に `ZoomWebhookUrl` が表示される。
このURLをZoom AppのEvent SubscriptionsのWebhook URLに設定する
（`../../README.md`の「Zoom側の設定」手順3参照）。

### 3. 動作確認

```bash
# ヘルスチェック代わりにURL検証イベントを直接叩く
curl -X POST <ZoomWebhookUrlの値> -H "Content-Type: application/json" \
  -d '{"event":"endpoint.url_validation","payload":{"plainToken":"abc123"}}'
```

`{"plainToken":"abc123","encryptedToken":"..."}` が返れば疎通成功。

### 4. ログ確認

```bash
sam logs --stack-name kitayama-minutes --tail
```

## 既知の制約（本番運用前に対応推奨）

- **同期実行**: Zoomは3秒以内の応答を要求するが、`lambda_handler()`は
  VTT取得〜AI要約〜docx生成〜アップロードまで同期的に行うため、Zoom側で
  タイムアウト・リトライが発生する可能性がある。対策案:
  1. Webhook受信用Lambdaと処理本体用Lambdaを分離し、SQS等で非同期化する
  2. `lambda_handler()`内で`recording.completed`受理後すぐ200を返し、
     本処理は別途 `boto3` で自分自身を非同期Invokeする
- **シークレット管理**: 現状はLambda環境変数（デフォルトのAWS管理KMSキーで暗号化）に
  直接格納している。より厳格に管理したい場合はAWS Secrets Managerへの移行を検討する
