# 北山文化圏センター 打合せ議事録 自動生成プロジェクト

Zoom録画 → 文字起こし → AI要約(JSON) → Word議事録(.docx)生成 → Google Driveアップロード
を自動化するプロジェクト。

## 全体フロー

```
1. Zoom Webhook (recording.completed)
       │  録画完了を検知
       ▼
2. 文字起こし(VTT)取得
       │
       ▼
3. Anthropic API /v1/messages
   system = prompts/system_prompt_v2.md
       │  文字起こし → 構造化JSON
       ▼
4. src/generate_minutes.py : generate(base, data, out)
       │  JSON を 打合せ記録簿.docx テンプレートに流し込み
       ▼
5. src/drive_sync.py : get_latest_base() / upload_result()
       │  最新テンプレート取得 / 生成物アップロード
       ▼
   Google Drive上の議事録フォルダ
```

## 現状（2026-09-14時点）

| コンポーネント | 状態 |
|---|---|
| `src/generate_minutes.py` | ✅ 完成・動作確認済み |
| `src/drive_sync.py` | ✅ サービスアカウント作成・Drive API接続・疎通確認まで完了（プロジェクト`giziroku-508607`） |
| `prompts/system_prompt_v2.md` | ✅ 完成（Step3用システムプロンプト） |
| `src/zoom_webhook.py` / `src/app.py` | ✅ 実装・ローカル動作確認済み（署名検証／URL検証／文字起こしファイル抽出） |
| Lambda/Cloud Functions統合ハンドラ | ❌ 未実装（`src/drive_sync.py`内にサンプルコードのみ） |
| デプロイ（Make / Lambda / Cloud Functions） | ❌ 未着手 |

## フォルダ構成

```
kitayama-minutes/
├── README.md                    このファイル
├── requirements.txt              Python依存パッケージ
├── .env.example                  環境変数テンプレート（実値は.envに、Git管理外）
├── src/
│   ├── generate_minutes.py       Step4: JSON→docx生成（完成済み）
│   ├── drive_sync.py             Step5: Google Drive連携（接続済み）
│   ├── zoom_webhook.py           Step1: Zoom Webhookの中核処理（実装済み・フレームワーク非依存）
│   ├── app.py                    Step1: ローカル動作確認用Flaskサーバー
│   ├── test_drive_connection.py  Drive接続確認スクリプト
│   └── handler.py                Lambda/Cloud Functions統合ハンドラ（未実装スタブ）
├── prompts/
│   └── system_prompt_v2.md       Step3用 Anthropic APIシステムプロンプト
├── templates/
│   └── （最新の「打合せ記録簿_北山文化圏センター_*.docx」を置く。Git管理外）
├── infra/
│   ├── lambda/                   AWS Lambdaデプロイ設定（SAM/Terraform等）
│   ├── gcp/                      GCP Cloud Functionsデプロイ設定
│   └── make/                     Makeシナリオでデプロイする場合のメモ
└── tests/
    ├── sample_data.json          generate_minutes.py 動作確認用のサンプルJSON
    └── test_zoom_webhook.py      zoom_webhook.py のユニットテスト
```

## 今後の作業（優先順位は要相談）

1. ~~Zoomの録画完了Webhook（`recording.completed`）受信部分の実装~~ ✅ 完了（2026-09-14）
   - `src/zoom_webhook.py`: 署名検証・URL検証チャレンジ応答・文字起こしファイル抽出・VTTダウンロード
   - `src/app.py`: ローカル動作確認用Flaskサーバー（`/webhook/zoom`）。デプロイ方式未定のため
     フレームワーク非依存の`handle_webhook_request()`をラップするだけの薄い作りにしてある
   - `tests/test_zoom_webhook.py`: 8件のユニットテスト、すべてパス
   - ⚠️ **未実施**: 実際のZoom Appでのイベント購読設定、および本物のWebhookイベントでの
     疎通確認（ローカルサーバーを外部公開する必要があるため。下記「Zoom側の設定」を参照）
   - ⚠️ **未実装**: 受理した`recording.completed`を実際にStep2以降（VTTダウンロード→
     AI要約→docx生成→アップロード）につなげる部分は、Step4（Lambda統合）で行う想定
2. ~~Google Cloudサービスアカウント作成・Drive API接続~~ ✅ 完了（2026-09-14）
   - サービスアカウント: `kitayama-minutes-drive-sync@giziroku-508607.iam.gserviceaccount.com`
   - 対象フォルダを、既存の手動運用フォルダ「２議事録」とは別に新規作成:
     「議事録_自動生成」（`DRIVE_FOLDER_ID=1dGlLk9n4SF5EnuJjphGd11FkN3XRPpw1`、
     親: 「2026北山文化圏センター」）
   - サービスアカウントには編集者として明示共有済み（公開リンク共有なし）
   - `get_latest_base()`用の初期ベースファイルとして、既存フォルダから
     `打合せ記録簿_北山文化圏センター_20260821.docx` をコピー済み
   - 旧フォルダ「２議事録」（`1_brqDoUoSx5kjIn5uGXOAn7Snzvmktjd`）は今後この用途では使わない
3. Make シナリオ、または AWS Lambda / GCP Cloud Functions としてデプロイ → `infra/`
4. `generate_minutes.py` と `drive_sync.py` を1つのLambdaハンドラとして結合 → `src/handler.py`

## ローカルでの動作確認

```bash
cd kitayama-minutes
pip install -r requirements.txt
python3 src/generate_minutes.py \
  --base templates/打合せ記録簿_北山文化圏センター_YYYYMMDD.docx \
  --json tests/sample_data.json \
  --out /tmp/打合せ記録簿_北山文化圏センター_新規.docx
```

`templates/` には過去に生成済みの打合せ記録簿（ベースファイル）を1つ手動で配置してください。

## Zoom Webhookのローカル動作確認

```bash
cd kitayama-minutes
export ZOOM_WEBHOOK_SECRET_TOKEN=任意のテスト用文字列
python3 src/app.py
# 別ターミナルで
curl -X POST http://127.0.0.1:8080/webhook/zoom -H "Content-Type: application/json" \
  -d '{"event":"endpoint.url_validation","payload":{"plainToken":"abc123"}}'
```

## Zoom側の設定（未実施・今後の作業）

1. https://marketplace.zoom.us/develop/create でApp（General App、またはWebhook Only）を作成
2. 「Feature」→「Event Subscriptions」で `Recording > All Recordings have completed`
   （`recording.completed`）を購読イベントに追加
3. Webhook URLには `src/app.py` を外部公開したURL（例: ngrokで一時公開、または本番デプロイ後のURL）
   の `/webhook/zoom` を指定
4. Zoomがこの時点で `endpoint.url_validation` イベントを送ってくるので、
   `ZOOM_WEBHOOK_SECRET_TOKEN`（App詳細画面の「Secret Token」）を環境変数に設定した状態で
   正しく応答できることを確認する
5. App詳細画面から実際にSecret Tokenを控え、`.env` の `ZOOM_WEBHOOK_SECRET_TOKEN` に設定

現時点では手元でのユニットテストとローカルFlaskサーバーでの動作確認のみ実施済みで、
実際のZoom Appからの疎通確認はまだ行っていません。
