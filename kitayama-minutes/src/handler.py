#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Zoom Webhook受信から、文字起こし取得・AI要約・docx生成・Driveアップロードまでを
1つに束ねるLambdaハンドラ。

パイプライン:
  Zoom Webhook (recording.completed)
    -> zoom_webhook.handle_webhook_request()  Step1: 署名検証・イベント振り分け
    -> zoom_webhook.download_transcript_vtt() Step2: 文字起こし(VTT)取得
    -> summarize.summarize_transcript()       Step3: Anthropic APIで要約JSON化
    -> drive_sync.get_latest_base()           Step5前半: 最新テンプレート取得
    -> generate_minutes.generate()            Step4: JSON->docx生成
    -> drive_sync.upload_result()             Step5後半: Driveアップロード

デプロイ方式（AWS Lambda / GCP Cloud Functions / Make）は未確定のため、中核処理
(process_recording)はプラットフォーム非依存にしてあり、lambda_handler()は
API Gateway（プロキシ統合）向けの薄いラッパーに過ぎない。Cloud Functionsにする場合は
このラッパー部分だけ差し替えればよい。

注意: Zoomは3秒以内にWebhookへの応答を要求する。process_recording()はVTT
ダウンロード・AI要約・docx生成・アップロードを含むため数秒〜数十秒かかりうる。
本番運用では、Webhook受信には即座に200を返し、process_recording()は非同期
（Lambdaの非同期呼び出し／SQS／Cloud Tasks等）に切り出すことを推奨する。
デプロイ方式が確定するまでは、同期呼び出しのままにしてある（Step3の課題）。
"""

import json
import os
import sys

sys.path.insert(0, os.path.dirname(__file__))

from drive_sync import get_latest_base, upload_result  # noqa: E402
from generate_minutes import generate  # noqa: E402
from summarize import summarize_transcript  # noqa: E402
from zoom_webhook import handle_recording_completed, handle_webhook_request  # noqa: E402


def process_recording(transcript_file: dict, download_token: str, meeting_date_hint: str = "") -> dict:
    """
    文字起こしファイル情報を受け取り、AI要約・docx生成・Driveアップロードまで実行する。
    戻り値: {"status": "ok", "drive_file_id": str, "docx_filename": str}
    """
    from zoom_webhook import download_transcript_vtt

    vtt_text = download_transcript_vtt(transcript_file, download_token)
    data = summarize_transcript(vtt_text, meeting_date_hint=meeting_date_hint)

    base_path = get_latest_base(local_dir="/tmp")
    out_path = f"/tmp/打合せ記録簿_北山文化圏センター_{data['meeting_date_yyyymmdd']}.docx"
    generate(base=base_path, data=data, out=out_path)
    file_id = upload_result(out_path)

    return {
        "status": "ok",
        "drive_file_id": file_id,
        "docx_filename": os.path.basename(out_path),
    }


def lambda_handler(event, context):
    """
    AWS Lambda + API Gateway（プロキシ統合）向けエントリポイント。
    event["headers"], event["body"] を前提とする。
    """
    headers = event.get("headers", {}) or {}
    raw_body = event.get("body", "") or ""

    status, response_body = handle_webhook_request(headers, raw_body)

    if status == 200 and response_body.get("status") == "accepted":
        data = json.loads(raw_body)
        info = handle_recording_completed(data.get("payload", {}))
        start_time = info.get("start_time", "")
        meeting_date_hint = start_time[:10].replace("-", "") if start_time else ""

        try:
            result = process_recording(
                info["transcript_file"], info["download_token"], meeting_date_hint=meeting_date_hint
            )
            response_body.update(result)
        except Exception as e:
            # Zoomへの応答自体は失敗させない（再送ループを避けるため200のまま返す）。
            # 本番ではここでエラー通知(SNS/Slack等)を送る想定。
            response_body["status"] = "error"
            response_body["error"] = str(e)

    return {
        "statusCode": status,
        "headers": {"Content-Type": "application/json"},
        "body": json.dumps(response_body, ensure_ascii=False),
    }
