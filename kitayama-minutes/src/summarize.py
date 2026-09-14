#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Step3: 文字起こし(VTT) → Anthropic API → generate_minutes.py用の構造化JSON。

prompts/system_prompt_v2.txt をsystemプロンプトとして使う。
内容の正本は prompts/system_prompt_v2.md（ドキュメント）と同期させること。
"""

import json
from pathlib import Path

import anthropic

SYSTEM_PROMPT_PATH = Path(__file__).parent.parent / "prompts" / "system_prompt_v2.txt"
MODEL = "claude-opus-5"


def _load_system_prompt() -> str:
    return SYSTEM_PROMPT_PATH.read_text(encoding="utf-8")


def _parse_json_response(text: str) -> dict:
    """Claudeの応答テキストからJSONを取り出す。コードフェンスで囲まれていても対応する。"""
    text = text.strip()
    if text.startswith("```"):
        text = text.split("\n", 1)[1] if "\n" in text else ""
        if text.rstrip().endswith("```"):
            text = text.rstrip()[: -len("```")]
    return json.loads(text.strip())


def summarize_transcript(vtt_text: str, meeting_date_hint: str = "") -> dict:
    """
    文字起こし(VTT)テキストをAnthropic APIに渡し、generate_minutes.py用のJSON(dict)を得る。

    meeting_date_hint: 文字起こし中に日付情報がない場合のフォールバック(YYYYMMDD)。
                        Zoom Webhookのstart_timeなどから呼び出し側が渡す想定。
    """
    client = anthropic.Anthropic()

    user_content = vtt_text
    if meeting_date_hint:
        user_content = (
            f"[会議日付のヒント: {meeting_date_hint}。"
            "文字起こし中に日付情報がなければこれを使うこと]\n\n" + vtt_text
        )

    response = client.messages.create(
        model=MODEL,
        max_tokens=16000,
        system=_load_system_prompt(),
        messages=[{"role": "user", "content": user_content}],
    )

    text = next((b.text for b in response.content if b.type == "text"), "")
    if not text:
        raise RuntimeError(f"Anthropic APIからテキスト応答が得られませんでした (stop_reason={response.stop_reason})")

    return _parse_json_response(text)
