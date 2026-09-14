#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
drive_sync.py がサービスアカウントでGoogle Driveに接続できるかを確認するスクリプト。

事前に .env（または環境変数）で GOOGLE_SERVICE_ACCOUNT_JSON と DRIVE_FOLDER_ID を
設定してから実行する。詳しい手順は infra/gcp/service_account_setup.md を参照。

    python3 src/test_drive_connection.py
"""

import os
import sys

sys.path.insert(0, os.path.dirname(__file__))

from drive_sync import _get_drive_service


def main():
    missing = [k for k in ("GOOGLE_SERVICE_ACCOUNT_JSON", "DRIVE_FOLDER_ID") if not os.environ.get(k)]
    if missing:
        print(f"環境変数 {', '.join(missing)} が設定されていません。.env を確認してください。", file=sys.stderr)
        sys.exit(1)

    service = _get_drive_service()
    folder_id = os.environ["DRIVE_FOLDER_ID"]

    query = f"'{folder_id}' in parents and trashed = false"
    results = service.files().list(
        q=query, fields="files(id, name, modifiedTime)", pageSize=50
    ).execute()
    files = results.get("files", [])

    if not files:
        print("接続はできましたが、フォルダ内にファイルが見つかりませんでした。")
        print("→ フォルダIDが正しいか、サービスアカウントがフォルダに共有されているか確認してください。")
        return

    print(f"接続成功。フォルダ内のファイル {len(files)} 件:")
    for f in files:
        print(f"  - {f['name']}  (id={f['id']}, modified={f['modifiedTime']})")


if __name__ == "__main__":
    main()
