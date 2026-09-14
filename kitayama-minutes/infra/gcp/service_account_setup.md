# Google Cloud サービスアカウント作成 & Drive API接続手順

`drive_sync.py` から Google Drive を操作するためのサービスアカウントを作る手順。
GCPコンソールでの操作が必要なため、ここはユーザー側の作業になります。

## 0. 対象フォルダ（確認済み）

Google Drive内を検索した結果、`打合せ記録簿_北山文化圏センター_*.docx` は
以下のフォルダに格納されていました。

- フォルダ名: **２議事録**
- フォルダID: **`1_brqDoUoSx5kjIn5uGXOAn7Snzvmktjd`**
- オーナー: `tomari.s078@gmail.com`
- 現在の共有設定: **リンクを知っている全員が「編集者」**

→ `.env` の `DRIVE_FOLDER_ID` にはこのIDを設定してください（`.env.example` にも記載済み）。

⚠️ 現状「リンクを知っている全員が編集可能」という公開範囲になっています。
サービスアカウントを個別に共有すれば、この公開設定は「制限付き」に戻せます
（本番運用前にセキュリティ上ここは見直すことをお勧めします＝手順3で対応）。

## 1. GCPプロジェクトの作成（既存プロジェクトがあれば流用可）

1. https://console.cloud.google.com/projectcreate にアクセス
2. プロジェクト名を入力（例: `kitayama-minutes-automation`）し「作成」

## 2. Drive APIの有効化

1. 作成したプロジェクトを選択した状態で
   https://console.cloud.google.com/apis/library/drive.googleapis.com を開く
2. 「有効にする」をクリック

## 3. サービスアカウントの作成とJSON鍵の発行

1. https://console.cloud.google.com/iam-admin/serviceaccounts を開く（対象プロジェクトを選択）
2. 「サービスアカウントを作成」
   - 名前: 例 `kitayama-minutes-drive-sync`
   - ロールは付与不要（Drive側の共有だけで権限を制御するため、プロジェクトロールはスキップして可）
3. 作成したサービスアカウントの詳細画面 →「キー」タブ →「鍵を追加」→「新しい鍵を作成」→ 形式は **JSON** を選択
4. JSONファイルがダウンロードされる。中身をそのまま `.env` の `GOOGLE_SERVICE_ACCOUNT_JSON` に設定する
   （ファイルの中身を1行の文字列としてコピペ、または `.env` 読み込み側でファイルパスから読む実装に変えてもよい）
5. サービスアカウントのメールアドレス（`xxxx@<project-id>.iam.gserviceaccount.com` の形式）を控えておく

## 4. 対象フォルダをサービスアカウントに共有

1. Google Driveで「２議事録」フォルダ（上記ID）を開く
2. 「共有」→ 手順3で控えたサービスアカウントのメールアドレスを追加 →「編集者」権限で共有
3. （推奨）このタイミングで「リンクを知っている全員」の公開設定を解除し、
   必要な人＋サービスアカウントのみのアクセスに絞る

## 5. 依存パッケージのインストール

```bash
cd kitayama-minutes
pip install -r requirements.txt
```

## 6. 接続確認

`.env` を用意した上で、`src/test_drive_connection.py` を実行して疎通確認する。

```bash
cd kitayama-minutes
export $(grep -v '^#' .env | xargs)   # .envを環境変数として読み込む（簡易版）
python3 src/test_drive_connection.py
```

「２議事録」フォルダ内の `打合せ記録簿_北山文化圏センター_*.docx` の一覧が表示されれば接続成功。
