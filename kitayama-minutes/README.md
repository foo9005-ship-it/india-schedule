# 北山文化圏センター 打合せ議事録 自動生成プロジェクト

Zoom録画・文字起こしから、会社所定の「打合せ記録簿」（.docx）を生成するプロジェクト。

## 採用した運用方式（2026-09-15確定）

**トリガーは末吉氏による手動起動。文字起こし取得〜docx生成までをClaude Codeが行い、
Google Driveへの最終保存は末吉氏が手動で行う。**

```
1. 末吉氏がClaude Codeセッションを開始し、対象の会議を伝える
       │  （Zoom連携ツールで文字起こしを取得、または末吉氏がファイルを直接渡す）
       ▼
2. Claudeが文字起こしを読み、prompts/system_prompt_v3.txt のルールに従って
   議事録本文をJSON化する（Anthropic API呼び出し不要。Claude自身がこの場で行う）
       ▼
3. src/generate_minutes.py : generate(base, data, out)
       │  JSON を 打合せ記録簿.docx テンプレートに流し込み
       ▼
4. Claudeが生成したdocxをユーザーに直接送付（SendUserFile）
       ▼
5. 末吉氏がGoogle Driveの「議事録_自動生成」フォルダにドラッグ&ドロップ（手動・10秒程度）
```

### この形に落ち着いた経緯

- 完全自動化（Zoom Webhook + AWS Lambda + Google Drive自動アップロード）を最初に検討したが、
  AWS環境構築（会社PCでの仮想化制限、Docker Desktopの壁）とGoogle Driveへの認証情報の
  安全な永続化（環境変数はこの製品では平文保存＝シークレット非推奨）の両方で運用上のハードルが
  高いことが判明した。
- Google Drive/Dropboxいずれも、MCPコネクタ経由でのバイナリアップロードは
  「ファイルの中身をBase64テキストとしてモデル自身が出力する」必要があり、
  数万文字規模になると1ターンの出力上限を超えて技術的に実行不可能（実際に検証済み）。
  コード（`drive_sync.py`等）から直接API呼び出しすればこの問題は起きないが、
  その場合も認証情報を安全にどう渡すかという同じ課題が残る。
- 結論として、「Driveアップロードを自動化するための認証情報管理の手間」は
  「生成物を受け取って手動でドラッグ&ドロップする手間」とほぼ同等かそれ以上だったため、
  最後のアップロードだけ人手に残すことにした。手間のかかる部分（文字起こしの読解・要約・
  正確な書式でのdocx生成）はすべて自動化されている。

## 現状（2026-09-15時点）

| コンポーネント | 状態 |
|---|---|
| `src/generate_minutes.py` | ✅ 完成・実データで動作確認済み（採用中の運用方式の中核） |
| `prompts/system_prompt_v3.txt` | ✅ 採用中。Claude Coworkでの実運用検証を反映した最新の執筆ルール |
| Zoom文字起こしの取得 | ✅ このセッションのZoom連携ツール（`recordings_list`/`get_recording_resource`）で動作確認済み |
| Google Driveへの保存 | 手動（末吉氏がドラッグ&ドロップ）。自動化は技術的制約により不採用（上記参照） |
| `src/drive_sync.py` / `src/zoom_webhook.py` / `src/handler.py` / `src/summarize.py` | 🗄️ 実装・テスト済みだが現在未使用。Zoom Webhook + AWS Lambdaによる完全自動化を将来的に
再検討する場合の土台として残置 |
| AWS Lambdaデプロイ（`infra/lambda/`） | 🗄️ Dockerfile・SAMテンプレート・手順書は用意済みだが**不採用**（会社PCでの環境構築が困難だったため） |

## フォルダ構成

```
kitayama-minutes/
├── README.md                    このファイル
├── requirements.txt              Python依存パッケージ
├── .env.example                  環境変数テンプレート（現在の運用方式では未使用）
├── src/
│   ├── generate_minutes.py       ✅ 現役: JSON→docx生成
│   ├── vendor/                   ✅ 現役: docxスキル非依存化のためのvendorコード
│   ├── drive_sync.py             🗄️ 未使用: Google Drive自動連携（サービスアカウント方式）
│   ├── zoom_webhook.py           🗄️ 未使用: Zoom Webhook受信
│   ├── app.py                    🗄️ 未使用: ローカル動作確認用Flaskサーバー
│   ├── summarize.py              🗄️ 未使用: Anthropic API経由の要約（Claude Code内で直接行うため不要）
│   ├── handler.py                🗄️ 未使用: 全ステップを結合したLambdaハンドラ
│   └── test_drive_connection.py  🗄️ 未使用: Drive接続確認スクリプト
├── prompts/
│   ├── system_prompt_v3.txt      ✅ 現役: 最新の執筆ルール（Claudeがこの場で読んで従う）
│   ├── system_prompt_v3.md       ✅ 現役: 同内容のドキュメント版
│   ├── system_prompt_v2.txt/.md  🗄️ 旧版（履歴として残置）
├── templates/                    （最新の「打合せ記録簿_北山文化圏センター_*.docx」を置く。Git管理外）
├── infra/                        🗄️ 未使用: AWS Lambda/GCP Cloud Functions/Makeデプロイ設定一式
└── tests/                        既存コンポーネントのユニットテスト（🗄️印のコンポーネント含む）
```

## 使い方（現在の運用方式）

1. Claude Codeセッションで、対象のZoom会議（会議名・日付）を伝える、または文字起こし
   ファイルを直接渡す
2. 出席者情報（会社名・氏名）を伝える。Zoomの発言者ラベルが実際の発言者と異なる場合は
   話者マッピングも伝える（例:「"末吉司"とラベル付けされた発言はすべてHOPE大浜さんの発言」）
3. Claudeが`prompts/system_prompt_v3.txt`のルールに従って議事録本文を作成し、
   `generate_minutes.py`でdocxを生成、ファイルとして送付する
4. 末吉氏がGoogle Driveの「議事録_自動生成」フォルダに保存する

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

## 参考: 不採用となった完全自動化構成

`src/drive_sync.py`・`src/zoom_webhook.py`・`src/handler.py`・`src/summarize.py`・
`infra/`配下は、Zoom Webhookで自動トリガーし、AWS Lambda上でAI要約からGoogle Drive
アップロードまで完全自動で行う構成として実装・テスト済み（詳細は各ファイルのdocstring、
`infra/lambda/README.md`、`infra/lambda/aws_account_setup.md`を参照）。将来、以下が
解決すれば再検討の余地がある。

- AWS環境構築の負担（会社PCでの仮想化制限を回避する手段）
- Google Drive等への認証情報を安全に永続保存する仕組み（現在のClaude Code環境には
  シークレット専用の保管場所がない）
