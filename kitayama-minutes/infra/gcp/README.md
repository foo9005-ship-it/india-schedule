# GCP Cloud Functionsデプロイ（未着手）

`src/handler.py` を Cloud Functions（第2世代）のHTTPトリガーとしてデプロイする想定。

## 検討事項
- ランタイムに `unzip`/`zip` コマンドが必要（`generate_minutes.py`）
  → Cloud Functions第2世代（Cloud Run基盤）ならDockerfileでベースイメージを制御しやすい
- Google Drive連携先とサービスアカウントの発行元が同じGCPプロジェクトであれば、
  Cloud Functions自体にサービスアカウントを直接紐付けられる可能性がある
  （`GOOGLE_SERVICE_ACCOUNT_JSON`環境変数を使わずデフォルト認証にできるか要確認）

## TODO
- [ ] Cloud Functions 第1世代 / 第2世代の選定
- [ ] デプロイ手順のドキュメント化（`gcloud functions deploy`）
