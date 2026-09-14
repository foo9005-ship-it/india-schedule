#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Zoom Webhook（recording.completed）受信スタブ。

TODO（次のステップで実装）:
  1. Zoom App の Webhook検証イベント（endpoint.url_validation）に応答する
  2. x-zm-signature ヘッダーで署名検証する（ZOOM_WEBHOOK_SECRET_TOKEN を使用）
  3. event == "recording.completed" のとき、payload.object.recording_files から
     文字起こし(VTT)ファイルのdownload_urlを取得する
  4. 取得したVTTを Step3（Anthropic API要約）に渡す

参考: https://developers.zoom.us/docs/api/webhooks/
"""

import hashlib
import hmac
import os


def verify_zoom_signature(request_body: str, timestamp: str, signature: str) -> bool:
    """Zoom Webhookの署名を検証する。"""
    secret_token = os.environ["ZOOM_WEBHOOK_SECRET_TOKEN"]
    message = f"v0:{timestamp}:{request_body}"
    computed = "v0=" + hmac.new(
        secret_token.encode(), message.encode(), hashlib.sha256
    ).hexdigest()
    return hmac.compare_digest(computed, signature)


def handle_recording_completed(payload: dict) -> dict:
    """recording.completed イベントのペイロードを受け取り、文字起こしファイル情報を返す。"""
    raise NotImplementedError("Step1: Zoom Webhook受信の実装はこれから")
