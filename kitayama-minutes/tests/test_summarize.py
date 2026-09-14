#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
summarize.py のユニットテスト。Anthropic APIへの実際のネットワーク呼び出しは行わない。

実行:
    cd kitayama-minutes
    python3 -m unittest tests.test_summarize -v
"""

import os
import sys
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from summarize import _load_system_prompt, _parse_json_response  # noqa: E402


class TestLoadSystemPrompt(unittest.TestCase):
    def test_loads_non_empty_prompt_with_expected_content(self):
        prompt = _load_system_prompt()
        self.assertIn("打合せ議事録", prompt)
        self.assertIn("meeting_date_yyyymmdd", prompt)


class TestParseJsonResponse(unittest.TestCase):
    def test_plain_json(self):
        result = _parse_json_response('{"theme": "テスト"}')
        self.assertEqual(result["theme"], "テスト")

    def test_json_in_code_fence(self):
        text = '```json\n{"theme": "テスト"}\n```'
        result = _parse_json_response(text)
        self.assertEqual(result["theme"], "テスト")

    def test_json_in_plain_code_fence(self):
        text = '```\n{"theme": "テスト"}\n```'
        result = _parse_json_response(text)
        self.assertEqual(result["theme"], "テスト")


if __name__ == "__main__":
    unittest.main()
