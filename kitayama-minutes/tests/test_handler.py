#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
handler.py のユニットテスト。外部サービス呼び出し(Zoom/Anthropic/Drive)は全てモック化する。

実行:
    cd kitayama-minutes
    python3 -m unittest tests.test_handler -v
"""

import hashlib
import hmac
import json
import os
import sys
import unittest
from unittest.mock import patch

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

import handler  # noqa: E402

SECRET = "test-secret-token"


def sign(body: str, timestamp: str) -> str:
    message = f"v0:{timestamp}:{body}"
    return "v0=" + hmac.new(SECRET.encode(), message.encode(), hashlib.sha256).hexdigest()


class TestProcessRecording(unittest.TestCase):
    @patch("zoom_webhook.download_transcript_vtt", return_value="VTTの中身...")
    @patch("handler.upload_result", return_value="drive-file-id-123")
    @patch("handler.generate", return_value="/tmp/out.docx")
    @patch("handler.get_latest_base", return_value="/tmp/base.docx")
    @patch("handler.summarize_transcript")
    def test_process_recording_happy_path(
        self, mock_summarize, mock_get_base, mock_generate, mock_upload, mock_download
    ):
        mock_summarize.return_value = {
            "meeting_date_yyyymmdd": "20260910",
            "theme": "テストテーマ",
        }
        result = handler.process_recording(
            {"download_url": "https://example.com/a.vtt"}, "dl-token", meeting_date_hint="20260910"
        )
        self.assertEqual(result["status"], "ok")
        self.assertEqual(result["drive_file_id"], "drive-file-id-123")
        mock_download.assert_called_once()
        mock_summarize.assert_called_once_with("VTTの中身...", meeting_date_hint="20260910")
        mock_generate.assert_called_once()
        mock_upload.assert_called_once_with("/tmp/打合せ記録簿_北山文化圏センター_20260910.docx")


class TestLambdaHandler(unittest.TestCase):
    def _make_event(self, payload: dict) -> dict:
        body = json.dumps(payload)
        timestamp = "1700000000"
        headers = {"x-zm-request-timestamp": timestamp, "x-zm-signature": sign(body, timestamp)}
        return {"headers": headers, "body": body}

    @patch.dict(os.environ, {"ZOOM_WEBHOOK_SECRET_TOKEN": SECRET})
    @patch("handler.process_recording")
    def test_lambda_handler_triggers_pipeline(self, mock_process):
        mock_process.return_value = {"status": "ok", "drive_file_id": "fid", "docx_filename": "x.docx"}
        payload = {
            "event": "recording.completed",
            "payload": {
                "download_token": "dl-token",
                "object": {
                    "topic": "第5回打合せ",
                    "uuid": "uuid-1",
                    "start_time": "2026-09-10T05:00:00Z",
                    "recording_files": [
                        {"file_type": "TRANSCRIPT", "download_url": "https://example.com/a.vtt"},
                    ],
                },
            },
        }
        event = self._make_event(payload)
        response = handler.lambda_handler(event, None)
        self.assertEqual(response["statusCode"], 200)
        body = json.loads(response["body"])
        self.assertEqual(body["status"], "ok")
        self.assertEqual(body["drive_file_id"], "fid")
        mock_process.assert_called_once_with(
            {"file_type": "TRANSCRIPT", "download_url": "https://example.com/a.vtt"},
            "dl-token",
            meeting_date_hint="20260910",
        )

    @patch.dict(os.environ, {"ZOOM_WEBHOOK_SECRET_TOKEN": SECRET})
    def test_lambda_handler_url_validation(self):
        payload = {"event": "endpoint.url_validation", "payload": {"plainToken": "abc"}}
        event = {"headers": {}, "body": json.dumps(payload)}
        response = handler.lambda_handler(event, None)
        self.assertEqual(response["statusCode"], 200)
        body = json.loads(response["body"])
        self.assertEqual(body["plainToken"], "abc")

    @patch.dict(os.environ, {"ZOOM_WEBHOOK_SECRET_TOKEN": SECRET})
    @patch("handler.process_recording")
    def test_lambda_handler_pipeline_error_still_acks(self, mock_process):
        mock_process.side_effect = RuntimeError("Drive API error")
        payload = {
            "event": "recording.completed",
            "payload": {
                "download_token": "dl-token",
                "object": {
                    "topic": "t",
                    "uuid": "u",
                    "start_time": "2026-09-10T05:00:00Z",
                    "recording_files": [{"file_type": "TRANSCRIPT", "download_url": "https://x/a.vtt"}],
                },
            },
        }
        event = self._make_event(payload)
        response = handler.lambda_handler(event, None)
        self.assertEqual(response["statusCode"], 200)
        body = json.loads(response["body"])
        self.assertEqual(body["status"], "error")
        self.assertIn("Drive API error", body["error"])


if __name__ == "__main__":
    unittest.main()
