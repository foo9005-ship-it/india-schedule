#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
zoom_webhook.py のユニットテスト。実際のネットワーク通信は行わない。

実行:
    cd kitayama-minutes
    python3 -m unittest tests.test_zoom_webhook -v
"""

import hashlib
import hmac
import json
import os
import sys
import unittest
from unittest.mock import patch

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from zoom_webhook import (  # noqa: E402
    extract_transcript_file,
    handle_webhook_request,
    verify_zoom_signature,
)

SECRET = "test-secret-token"


def sign(body: str, timestamp: str) -> str:
    message = f"v0:{timestamp}:{body}"
    return "v0=" + hmac.new(SECRET.encode(), message.encode(), hashlib.sha256).hexdigest()


class TestVerifyZoomSignature(unittest.TestCase):
    @patch.dict(os.environ, {"ZOOM_WEBHOOK_SECRET_TOKEN": SECRET})
    def test_valid_signature(self):
        body = '{"event":"test"}'
        timestamp = "1700000000"
        self.assertTrue(verify_zoom_signature(body, timestamp, sign(body, timestamp)))

    @patch.dict(os.environ, {"ZOOM_WEBHOOK_SECRET_TOKEN": SECRET})
    def test_invalid_signature(self):
        self.assertFalse(verify_zoom_signature('{"event":"test"}', "1700000000", "v0=deadbeef"))


class TestExtractTranscriptFile(unittest.TestCase):
    def test_finds_transcript_file(self):
        payload = {
            "object": {
                "recording_files": [
                    {"file_type": "MP4", "download_url": "https://example.com/a.mp4"},
                    {"file_type": "TRANSCRIPT", "download_url": "https://example.com/a.vtt"},
                ]
            }
        }
        result = extract_transcript_file(payload)
        self.assertIsNotNone(result)
        self.assertEqual(result["download_url"], "https://example.com/a.vtt")

    def test_no_transcript_file(self):
        payload = {"object": {"recording_files": [{"file_type": "MP4"}]}}
        self.assertIsNone(extract_transcript_file(payload))


class TestHandleWebhookRequest(unittest.TestCase):
    @patch.dict(os.environ, {"ZOOM_WEBHOOK_SECRET_TOKEN": SECRET})
    def test_url_validation(self):
        body = json.dumps({
            "event": "endpoint.url_validation",
            "payload": {"plainToken": "abc123"},
        })
        status, resp = handle_webhook_request({}, body)
        self.assertEqual(status, 200)
        self.assertEqual(resp["plainToken"], "abc123")
        expected = hmac.new(SECRET.encode(), b"abc123", hashlib.sha256).hexdigest()
        self.assertEqual(resp["encryptedToken"], expected)

    @patch.dict(os.environ, {"ZOOM_WEBHOOK_SECRET_TOKEN": SECRET})
    def test_recording_completed_with_transcript(self):
        payload = {
            "event": "recording.completed",
            "payload": {
                "download_token": "dl-token",
                "object": {
                    "topic": "第5回打合せ",
                    "uuid": "meeting-uuid-123",
                    "start_time": "2026-09-10T05:00:00Z",
                    "recording_files": [
                        {"file_type": "TRANSCRIPT", "download_url": "https://example.com/a.vtt"},
                    ],
                },
            },
        }
        body = json.dumps(payload)
        timestamp = "1700000000"
        headers = {"x-zm-request-timestamp": timestamp, "x-zm-signature": sign(body, timestamp)}
        status, resp = handle_webhook_request(headers, body)
        self.assertEqual(status, 200)
        self.assertEqual(resp["status"], "accepted")
        self.assertEqual(resp["meeting_topic"], "第5回打合せ")

    @patch.dict(os.environ, {"ZOOM_WEBHOOK_SECRET_TOKEN": SECRET})
    def test_recording_completed_without_transcript_is_ignored(self):
        payload = {
            "event": "recording.completed",
            "payload": {"object": {"topic": "t", "uuid": "u", "recording_files": []}},
        }
        body = json.dumps(payload)
        timestamp = "1700000000"
        headers = {"x-zm-request-timestamp": timestamp, "x-zm-signature": sign(body, timestamp)}
        status, resp = handle_webhook_request(headers, body)
        self.assertEqual(status, 200)
        self.assertEqual(resp["status"], "ignored")

    @patch.dict(os.environ, {"ZOOM_WEBHOOK_SECRET_TOKEN": SECRET})
    def test_invalid_signature_returns_401(self):
        body = json.dumps({"event": "recording.completed", "payload": {"object": {}}})
        headers = {"x-zm-request-timestamp": "1700000000", "x-zm-signature": "v0=deadbeef"}
        status, resp = handle_webhook_request(headers, body)
        self.assertEqual(status, 401)


if __name__ == "__main__":
    unittest.main()
