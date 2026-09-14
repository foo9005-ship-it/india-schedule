#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Google Drive連携モジュール。Lambda/Cloud Functions内で generate_minutes.py と
組み合わせて使う想定。

役割:
  1. get_latest_base()  : 指定フォルダから最新の「打合せ記録簿_*.docx」を取得しローカル保存
  2. upload_result()    : 生成された新しい.docxを同フォルダにアップロード

AIを一切使わず、Google Drive API v3のみで完結する（トークン消費なし）。

--- 事前準備（1回だけ） ---
1. Google Cloud Consoleでサービスアカウントを作成し、JSON鍵をダウンロード
   （Drive API を有効化しておくこと）
2. 対象のGoogle Driveフォルダを、サービスアカウントのメールアドレス
   （xxxx@xxxx.iam.gserviceaccount.com）に「編集者」として共有
3. 依存パッケージ:
   pip install google-api-python-client google-auth --break-system-packages
4. Lambda/Cloud Functions環境変数に以下を設定:
   - GOOGLE_SERVICE_ACCOUNT_JSON : サービスアカウントJSON鍵の中身（文字列）
   - DRIVE_FOLDER_ID             : 対象フォルダのID（フォルダURLの末尾部分）
"""

import io
import json
import os
import re
from pathlib import Path

from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseDownload, MediaFileUpload

SCOPES = ["https://www.googleapis.com/auth/drive"]

# 対象ファイル名のパターン（案件ごとに変更可）
FILENAME_PATTERN = re.compile(r"打合せ記録簿_北山文化圏センター_(\d{8})\.docx")


def _get_drive_service():
    creds_json = os.environ["GOOGLE_SERVICE_ACCOUNT_JSON"]
    info = json.loads(creds_json)
    creds = service_account.Credentials.from_service_account_info(info, scopes=SCOPES)
    return build("drive", "v3", credentials=creds)


def get_latest_base(local_dir="/tmp") -> str:
    """
    DRIVE_FOLDER_ID 内から、ファイル名の日付(YYYYMMDD)が最も新しい
    「打合せ記録簿_北山文化圏センター_*.docx」を探してダウンロードし、
    ローカルパスを返す。generate_minutes.py の --base にそのまま渡せる。
    """
    service = _get_drive_service()
    folder_id = os.environ["DRIVE_FOLDER_ID"]

    query = f"'{folder_id}' in parents and trashed = false and name contains '打合せ記録簿_北山文化圏センター_'"
    results = service.files().list(
        q=query, fields="files(id, name)", pageSize=100
    ).execute()
    files = results.get("files", [])

    dated = []
    for f in files:
        m = FILENAME_PATTERN.match(f["name"])
        if m:
            dated.append((m.group(1), f["id"], f["name"]))

    if not dated:
        raise RuntimeError(
            "フォルダ内に「打合せ記録簿_北山文化圏センター_YYYYMMDD.docx」形式の"
            "ファイルが見つかりません。初回は手動でベースファイルを1つ配置してください。"
        )

    dated.sort(key=lambda x: x[0])  # 日付文字列の昇順 = 最新が末尾
    _, latest_id, latest_name = dated[-1]

    local_path = str(Path(local_dir) / latest_name)
    request = service.files().get_media(fileId=latest_id)
    with io.FileIO(local_path, "wb") as fh:
        downloader = MediaIoBaseDownload(fh, request)
        done = False
        while not done:
            _, done = downloader.next_chunk()

    print(f"最新のベースファイルを取得しました: {latest_name}")
    return local_path


def upload_result(local_path: str) -> str:
    """
    生成された.docxをDRIVE_FOLDER_IDにアップロードする。
    戻り値はアップロードされたファイルのGoogle Drive上のID。
    """
    service = _get_drive_service()
    folder_id = os.environ["DRIVE_FOLDER_ID"]

    filename = Path(local_path).name
    file_metadata = {"name": filename, "parents": [folder_id]}
    media = MediaFileUpload(
        local_path,
        mimetype="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    )
    uploaded = service.files().create(
        body=file_metadata, media_body=media, fields="id, webViewLink"
    ).execute()

    print(f"アップロード完了: {filename} -> {uploaded.get('webViewLink')}")
    return uploaded["id"]


# --- Lambda/Cloud Functions ハンドラの組み立て例 ------------------------
#
# from generate_minutes import main as generate_docx  # ※generate_minutes.py側を
#                                                        関数呼び出し可能に小改修する想定
# from drive_sync import get_latest_base, upload_result
#
# def handler(event, context):
#     base_path = get_latest_base()                    # ① 最新テンプレートを自動取得
#     data = event["ai_summary_json"]                   # ② Step3のAI出力（Makeから渡される）
#     out_path = f"/tmp/打合せ記録簿_北山文化圏センター_{data['meeting_date_yyyymmdd']}.docx"
#     generate_docx(base=base_path, data=data, out=out_path)  # ③ テンプレート流し込み
#     file_id = upload_result(out_path)                 # ④ Google Driveへアップロード
#     return {"status": "ok", "drive_file_id": file_id}
