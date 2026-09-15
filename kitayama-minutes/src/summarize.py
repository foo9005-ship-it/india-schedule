#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Step3: 文字起こし(VTT) → Anthropic API → generate_minutes.py用の構造化JSON。

prompts/system_prompt_v3.txt をsystemプロンプトとして使う。
内容の正本は prompts/system_prompt_v3.md（ドキュメント）と同期させること。
"""

import json
from pathlib import Path

import anthropic

SYSTEM_PROMPT_PATH = Path(__file__).parent.parent / "prompts" / "system_prompt_v3.txt"
MODEL = "claude-opus-5"


def _load_system_prompt() -> str:
    return SYSTEM_PROMPT_PATH.read_text(encoding="utf-8")


def read_text_auto_encoding(path: str) -> str:
    """
    UTF-8を優先し、失敗したらShift-JIS(CP932)で読む。依頼者作成の補足メモが
    Shift-JISで保存されているケースへの対応（要件定義書4.4）。
    """
    data = Path(path).read_bytes()
    for encoding in ("utf-8", "cp932"):
        try:
            return data.decode(encoding)
        except UnicodeDecodeError:
            continue
    raise UnicodeDecodeError("auto", data, 0, 1, "utf-8/cp932のいずれでもデコードできませんでした")


def _parse_json_response(text: str) -> dict:
    """Claudeの応答テキストからJSONを取り出す。コードフェンスで囲まれていても対応する。"""
    text = text.strip()
    if text.startswith("```"):
        text = text.split("\n", 1)[1] if "\n" in text else ""
        if text.rstrip().endswith("```"):
            text = text.rstrip()[: -len("```")]
    return json.loads(text.strip())


def summarize_transcript(
    vtt_text: str,
    meeting_date_hint: str = "",
    meeting_notes: str = "",
    attendee_info: str = "",
    speaker_mapping: str = "",
) -> dict:
    """
    文字起こし(VTT)テキストをAnthropic APIに渡し、generate_minutes.py用のJSON(dict)を得る。

    meeting_date_hint: 文字起こし中に日付情報がない場合のフォールバック(YYYYMMDD)。
    meeting_notes:     依頼者が別途作成した会議メモ・要約テキスト（あれば要約精度向上に使う）。
    attendee_info:      出席者情報（会社名・氏名）。文字起こしだけでは把握できない出席者を補う。
    speaker_mapping:    「Zoom表示名→実際の発言者名」の対応指示（例:
                         "末吉司 と表示されている発言はすべて大浜(HOPE)の発言として扱う"）。
                         Zoomの表示名が実際の発言者と異なるケースがあるため（要件定義書4.2）。
    """
    client = anthropic.Anthropic()

    context_blocks = []
    if meeting_date_hint:
        context_blocks.append(f"[会議日付のヒント: {meeting_date_hint}。文字起こし中に日付情報がなければこれを使うこと]")
    if speaker_mapping:
        context_blocks.append(f"[話者マッピング指示]\n{speaker_mapping}")
    if attendee_info:
        context_blocks.append(f"[出席者情報]\n{attendee_info}")
    if meeting_notes:
        context_blocks.append(f"[依頼者作成の補足メモ]\n{meeting_notes}")
    context_blocks.append(f"[文字起こし]\n{vtt_text}")

    user_content = "\n\n".join(context_blocks)

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
