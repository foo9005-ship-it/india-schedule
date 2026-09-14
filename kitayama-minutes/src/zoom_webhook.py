#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Zoom Webhook（recording.completed）受信。

Zoomの「Webhookのみ」タイプのApp（またはGeneral App内のEvent Subscriptions）に、
このモジュールが提供するエンドポイントのURLを登録して使う。

対応するイベント:
  - endpoint.url_validation : Zoom側でWebhook URLを登録する際の検証チャレンジに応答する
  - recording.completed     : 録画完了。文字起こし(VTT)ファイルの情報を取り出す

参考: https://developers.zoom.us/docs/api/webhooks/
"""

import hashlib
import hmac
import json
import os

import requests


def _get_header(headers: dict, name: str) -> str:
    """ヘッダー名の大文字小文字を区別せずに値を取得する。"""
    name_lower = name.lower()
    for k, v in headers.items():
        if k.lower() == name_lower:
            return v
    return ""


def verify_zoom_signature(request_body: str, timestamp: str, signature: str) -> bool:
    """Zoom Webhookの署名(x-zm-signature)を検証する。"""
    secret_token = os.environ["ZOOM_WEBHOOK_SECRET_TOKEN"]
    message = f"v0:{timestamp}:{request_body}"
    computed = "v0=" + hmac.new(
        secret_token.encode(), message.encode(), hashlib.sha256
    ).hexdigest()
    return hmac.compare_digest(computed, signature)


def handle_url_validation(plain_token: str) -> dict:
    """
    endpoint.url_validation イベントへの応答を作る。
    Zoom側の仕様: plainTokenを、Secret TokenをキーにしたHMAC-SHA256でハッシュ化して返す。
    """
    secret_token = os.environ["ZOOM_WEBHOOK_SECRET_TOKEN"]
    encrypted_token = hmac.new(
        secret_token.encode(), plain_token.encode(), hashlib.sha256
    ).hexdigest()
    return {"plainToken": plain_token, "encryptedToken": encrypted_token}


def extract_transcript_file(payload: dict) -> dict:
    """
    recording.completed の payload から、文字起こし(TRANSCRIPT/VTT)ファイルの
    情報を取り出す。見つからなければ None を返す。
    """
    obj = payload.get("object", {})
    for f in obj.get("recording_files", []):
        if f.get("file_type") == "TRANSCRIPT":
            return f
    return None


def handle_recording_completed(payload: dict) -> dict:
    """
    recording.completed イベントのpayloadを受け取り、後続処理に必要な情報をまとめて返す。
    戻り値: {
        "meeting_topic": str, "meeting_uuid": str, "start_time": str,
        "transcript_file": dict | None, "download_token": str,
    }
    """
    obj = payload.get("object", {})
    return {
        "meeting_topic": obj.get("topic", ""),
        "meeting_uuid": obj.get("uuid", ""),
        "start_time": obj.get("start_time", ""),
        "transcript_file": extract_transcript_file(payload),
        "download_token": payload.get("download_token", ""),
    }


def download_transcript_vtt(transcript_file: dict, download_token: str, timeout: int = 30) -> str:
    """文字起こし(VTT)ファイルの中身をダウンロードして文字列で返す。"""
    if transcript_file is None:
        raise RuntimeError("文字起こし(TRANSCRIPT)ファイルが見つかりません")
    resp = requests.get(
        transcript_file["download_url"],
        params={"access_token": download_token},
        timeout=timeout,
    )
    resp.raise_for_status()
    return resp.text


def handle_webhook_request(headers: dict, raw_body: bytes) -> "tuple[int, dict]":
    """
    HTTPフレームワークに依存しない、Zoom Webhookリクエストの中核処理。
    (status_code, response_body_dict) を返す。Flask/Lambda/Cloud Functionsいずれからも
    このまま呼び出せる。
    """
    body_str = raw_body.decode("utf-8") if isinstance(raw_body, (bytes, bytearray)) else raw_body
    data = json.loads(body_str)
    event = data.get("event", "")

    if event == "endpoint.url_validation":
        plain_token = data.get("payload", {}).get("plainToken", "")
        return 200, handle_url_validation(plain_token)

    timestamp = _get_header(headers, "x-zm-request-timestamp")
    signature = _get_header(headers, "x-zm-signature")
    if not verify_zoom_signature(body_str, timestamp, signature):
        return 401, {"error": "invalid signature"}

    if event == "recording.completed":
        info = handle_recording_completed(data.get("payload", {}))
        if info["transcript_file"] is None:
            return 200, {"status": "ignored", "reason": "no transcript file in this recording"}
        # TODO(Step4): ここでStep2(VTTダウンロード)〜Step5(Driveアップロード)の
        # パイプラインをトリガーする（handler.py側に統合する想定）。
        return 200, {
            "status": "accepted",
            "meeting_topic": info["meeting_topic"],
            "meeting_uuid": info["meeting_uuid"],
        }

    return 200, {"status": "ignored", "reason": f"unhandled event: {event}"}
