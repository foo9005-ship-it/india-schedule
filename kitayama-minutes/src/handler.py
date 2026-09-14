#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
generate_minutes.py と drive_sync.py を結合するLambda/Cloud Functions統合ハンドラのスタブ。

drive_sync.py 末尾のコメントにあった組み立て例をベースに、これから実装する。

TODO（次のステップで実装）:
  1. zoom_webhook.handle_recording_completed() の出力（文字起こしURL）を受け取る
  2. 文字起こしをダウンロードし、Anthropic API（system=prompts/system_prompt_v2.md）で要約JSON化する
  3. drive_sync.get_latest_base() で最新テンプレートを取得する
  4. generate_minutes.generate(base, data, out) で新しい.docxを生成する
  5. drive_sync.upload_result(out) でGoogle Driveにアップロードする
"""

import os
import sys

sys.path.insert(0, os.path.dirname(__file__))

from drive_sync import get_latest_base, upload_result
from generate_minutes import generate


def handler(event, context):
    base_path = get_latest_base()
    data = event["ai_summary_json"]
    out_path = (
        f"/tmp/打合せ記録簿_北山文化圏センター_{data['meeting_date_yyyymmdd']}.docx"
    )
    generate(base=base_path, data=data, out=out_path)
    file_id = upload_result(out_path)
    return {"status": "ok", "drive_file_id": file_id}
