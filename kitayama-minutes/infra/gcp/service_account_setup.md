# Google Cloud サービスアカウント作成 & Drive API接続手順

`drive_sync.py` から Google Drive を操作するためのサービスアカウントを作る手順。
GCPコンソールでの操作が必要なため、ここはユーザー側の作業になります。

**ステータス: 2026-09-14に手順1〜6すべて完了・接続確認済み。**
以下は実施済みの手順の記録（再セットアップや別プロジェクトへの展開時の参考用）。

## 0. 対象フォルダ（確認済み・自動生成専用に分離済み）

自動生成した議事録の保存先として、既存の手動運用フォルダ「２議事録」とは別に
新規フォルダを作成した。

- フォルダ名: **議事録_自動生成**
- フォルダID: **`1dGlLk9n4SF5EnuJjphGd11FkN3XRPpw1`**
- 親フォルダ: 「2026北山文化圏センター」
- オーナー: `foo9005@gmail.com`
- 共有設定: `kitayama-minutes-drive-sync@giziroku-508607.iam.gserviceaccount.com` に編集者として共有済み。
  公開リンク共有なし（当初の「２議事録」フォルダで問題になった
  「リンクを知っている全員が編集者」という公開設定は、この新フォルダでは行っていない）
- 初期状態: `get_latest_base()` が動作するよう、既存フォルダから
  `打合せ記録簿_北山文化圏センター_20260821.docx` をコピー済み

→ `.env` の `DRIVE_FOLDER_ID` にはこのIDを設定する（`.env.example` にも記載済み）。

参考: 旧フォルダ「２議事録」（`1_brqDoUoSx5kjIn5uGXOAn7Snzvmktjd`、
オーナー `tomari.s078@gmail.com`）は人手で作成してきた過去の議事録の保管場所として
残っているが、今後の自動生成フローでは使わない。

## 1. GCPプロジェクトの作成（既存プロジェクトがあれば流用可）

1. https://console.cloud.google.com/projectcreate にアクセス
2. プロジェクト名を入力（例: `kitayama-minutes-automation`）し「作成」

✅ 完了: プロジェクト `giziroku-508607` を使用。

## 2. Drive APIの有効化

1. 作成したプロジェクトを選択した状態で
   https://console.cloud.google.com/apis/library/drive.googleapis.com を開く
2. 「有効にする」をクリック

✅ 完了。

## 3. サービスアカウントの作成とJSON鍵の発行

1. https://console.cloud.google.com/iam-admin/serviceaccounts を開く（対象プロジェクトを選択）
2. 「サービスアカウントを作成」
   - 名前: 例 `kitayama-minutes-drive-sync`
   - ロールは付与不要（Drive側の共有だけで権限を制御するため、プロジェクトロールはスキップして可）
3. 作成したサービスアカウントの詳細画面 →「キー」タブ →「鍵を追加」→「新しい鍵を作成」→ 形式は **JSON** を選択
4. JSONファイルがダウンロードされる。中身をそのまま `.env` の `GOOGLE_SERVICE_ACCOUNT_JSON` に設定する
   （ファイルの中身を1行の文字列としてコピペ、または `.env` 読み込み側でファイルパスから読む実装に変えてもよい）
5. サービスアカウントのメールアドレス（`xxxx@<project-id>.iam.gserviceaccount.com` の形式）を控えておく

✅ 完了: `kitayama-minutes-drive-sync@giziroku-508607.iam.gserviceaccount.com`
（鍵は接続確認後にチャット上で共有された経緯があるため、失効・再発行を推奨）

## 4. 対象フォルダをサービスアカウントに共有

1. Google Driveで対象フォルダ（上記0節のフォルダ）を開く
2. 「共有」→ 手順3で控えたサービスアカウントのメールアドレスを追加 →「編集者」権限で共有
3. 公開リンク共有は行わない（必要な人＋サービスアカウントのみのアクセスに絞る）

✅ 完了: 「議事録_自動生成」フォルダに編集者として共有済み、公開リンク共有なし。

## 5. 依存パッケージのインストール

```bash
cd kitayama-minutes
pip install -r requirements.txt
```

✅ 完了。

## 6. 接続確認

`.env` を用意した上で、`src/test_drive_connection.py` を実行して疎通確認する。

```bash
cd kitayama-minutes
export $(grep -v '^#' .env | xargs)   # .envを環境変数として読み込む（簡易版）
python3 src/test_drive_connection.py
```

「議事録_自動生成」フォルダ内のファイル一覧が表示されれば接続成功。

✅ 完了: 2026-09-14に接続確認済み（初期ベースファイル1件を検出）。
