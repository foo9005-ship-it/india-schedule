#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
JSON（Step3のAI要約出力）を、北山文化圏センター打合せ記録簿テンプレートに流し込み、
新しい.docxを生成するスクリプト。

使い方:
    python3 generate_minutes.py --base sample_0821.docx --json data.json --out result.docx

BASE には、過去に生成済みの打合せ記録簿（例: 打合せ記録簿_北山文化圏センター_20260821.docx）を
そのまま指定してよい。スクリプトが会議固有の内容(第◯回・日時・場所・出席者・テーマ・本文)を
すべて新しい内容で置き換える。フォント・表構造・書式は元ファイルのものをそのまま継承する。
"""

import argparse
import json
import re
import shutil
import subprocess
import sys
from pathlib import Path
from xml.sax.saxutils import escape as xml_escape

MERGE_RUNS = "/mnt/skills/public/docx/scripts/merge_runs.py"

# ---- paraId generator -------------------------------------------------

_paraid_counter = [0x1D000001]


def next_paraid():
    val = _paraid_counter[0]
    _paraid_counter[0] += 1
    return f"{val:08X}"


# ---- XML fragment builders ---------------------------------------------

FONT_MINCHO = 'w:ascii="ＭＳ 明朝" w:hAnsi="ＭＳ 明朝"'


def heading_para(text):
    """太字の見出し段落（会議のテーマ／詳細内容／１．〜等と同じ書式）"""
    pid = next_paraid()
    return (
        f'<w:p w14:paraId="{pid}" w14:textId="77777777" w:rsidR="007B4F5C" '
        f'w:rsidRDefault="007B4F5C" w:rsidP="007B4F5C">'
        f'<w:pPr><w:snapToGrid w:val="0"/><w:spacing w:line="300" w:lineRule="atLeast"/>'
        f'<w:ind w:rightChars="100" w:right="190"/>'
        f'<w:rPr><w:rFonts {FONT_MINCHO}/><w:b/><w:bCs/></w:rPr></w:pPr>'
        f'<w:r><w:rPr><w:rFonts {FONT_MINCHO} w:hint="eastAsia"/><w:b/><w:bCs/></w:rPr>'
        f'<w:t xml:space="preserve">{xml_escape(text)}</w:t></w:r></w:p>'
    )


def theme_para(text):
    """会議のテーマ、の下に入る一段インデントされた平文段落"""
    pid = next_paraid()
    return (
        f'<w:p w14:paraId="{pid}" w14:textId="77777777" w:rsidR="007B4F5C" '
        f'w:rsidRDefault="007B4F5C" w:rsidP="007B4F5C">'
        f'<w:pPr><w:snapToGrid w:val="0"/><w:spacing w:line="300" w:lineRule="atLeast"/>'
        f'<w:ind w:left="720" w:rightChars="100" w:right="190"/>'
        f'<w:rPr><w:rFonts {FONT_MINCHO}/></w:rPr></w:pPr>'
        f'<w:r><w:rPr><w:rFonts {FONT_MINCHO} w:hint="eastAsia"/></w:rPr>'
        f'<w:t xml:space="preserve">{xml_escape(text)}</w:t></w:r></w:p>'
    )


def bullet_para(text, ilvl=0, num_id=26):
    pid = next_paraid()
    return (
        f'<w:p w14:paraId="{pid}" w14:textId="77777777" w:rsidR="007B4F5C" '
        f'w:rsidRDefault="007B4F5C" w:rsidP="007B4F5C">'
        f'<w:pPr><w:numPr><w:ilvl w:val="{ilvl}"/><w:numId w:val="{num_id}"/></w:numPr>'
        f'<w:snapToGrid w:val="0"/><w:spacing w:line="300" w:lineRule="atLeast"/>'
        f'<w:ind w:rightChars="100" w:right="190"/>'
        f'<w:rPr><w:rFonts {FONT_MINCHO}/></w:rPr></w:pPr>'
        f'<w:r><w:rPr><w:rFonts {FONT_MINCHO} w:hint="eastAsia"/></w:rPr>'
        f'<w:t xml:space="preserve">{xml_escape(text)}</w:t></w:r></w:p>'
    )


BLOCK_BUILDERS = {
    "heading": lambda b: heading_para(b["text"]),
    "theme": lambda b: theme_para(b["text"]),
    "bullet0": lambda b: bullet_para(b["text"], ilvl=0),
    "bullet1": lambda b: bullet_para(b["text"], ilvl=1),
}


def build_body_blocks(blocks):
    return "".join(BLOCK_BUILDERS[b["type"]](b) for b in blocks)


# ---- attendee table row builder ----------------------------------------

def attendee_row(affiliation, names, is_first, is_last):
    label_paraid = next_paraid()
    org_paraid = next_paraid()
    names_paraid = next_paraid()

    if is_first:
        label_cell = (
            f'<w:tc><w:tcPr><w:tcW w:w="1063" w:type="dxa"/><w:vMerge w:val="restart"/>'
            f'<w:tcBorders><w:top w:val="single" w:sz="8" w:space="0" w:color="auto"/>'
            f'<w:left w:val="single" w:sz="12" w:space="0" w:color="auto"/>'
            f'<w:right w:val="single" w:sz="8" w:space="0" w:color="auto"/></w:tcBorders>'
            f'<w:vAlign w:val="center"/></w:tcPr>'
            f'<w:p w14:paraId="{label_paraid}" w14:textId="77777777" w:rsidR="001759D0" '
            f'w:rsidRDefault="00B17D5D" w:rsidP="008D4858">'
            f'<w:pPr><w:jc w:val="distribute"/>'
            f'<w:rPr><w:rFonts w:ascii="HGｺﾞｼｯｸM" w:eastAsia="HGｺﾞｼｯｸM" w:hAnsi="ＭＳ Ｐゴシック"/>'
            f'<w:sz w:val="20"/></w:rPr></w:pPr>'
            f'<w:r><w:rPr><w:rFonts w:ascii="HGｺﾞｼｯｸM" w:eastAsia="HGｺﾞｼｯｸM" '
            f'w:hAnsi="ＭＳ Ｐゴシック" w:hint="eastAsia"/><w:sz w:val="20"/></w:rPr>'
            f'<w:t>出席者</w:t></w:r></w:p>'
            f'<w:p w14:paraId="{next_paraid()}" w14:textId="77777777" w:rsidR="001759D0" '
            f'w:rsidRDefault="00B17D5D" w:rsidP="008D4858">'
            f'<w:pPr><w:jc w:val="distribute"/>'
            f'<w:rPr><w:rFonts w:ascii="HGｺﾞｼｯｸM" w:eastAsia="HGｺﾞｼｯｸM" w:hAnsi="ＭＳ Ｐゴシック"/>'
            f'<w:sz w:val="20"/><w:u w:val="single"/></w:rPr></w:pPr>'
            f'<w:r><w:rPr><w:rFonts w:ascii="HGｺﾞｼｯｸM" w:eastAsia="HGｺﾞｼｯｸM" '
            f'w:hAnsi="ＭＳ Ｐゴシック" w:hint="eastAsia"/><w:sz w:val="16"/></w:rPr>'
            f'<w:t>（敬称略）</w:t></w:r></w:p></w:tc>'
        )
        row_top = '<w:trPr><w:cantSplit/><w:trHeight w:val="325"/></w:trPr>'
    else:
        bottom_val = (
            '<w:bottom w:val="single" w:sz="12" w:space="0" w:color="auto"/>'
            if is_last else '<w:bottom w:val="single" w:sz="4" w:space="0" w:color="auto"/>'
        )
        label_cell = (
            f'<w:tc><w:tcPr><w:tcW w:w="1063" w:type="dxa"/><w:vMerge/>'
            f'<w:tcBorders><w:left w:val="single" w:sz="12" w:space="0" w:color="auto"/>'
            f'{bottom_val}'
            f'<w:right w:val="single" w:sz="8" w:space="0" w:color="auto"/></w:tcBorders>'
            f'<w:vAlign w:val="center"/></w:tcPr>'
            f'<w:p w14:paraId="{label_paraid}" w14:textId="77777777" w:rsidR="00117C99" '
            f'w:rsidRDefault="00117C99" w:rsidP="008D4858">'
            f'<w:pPr><w:jc w:val="distribute"/>'
            f'<w:rPr><w:rFonts w:ascii="HGｺﾞｼｯｸM" w:eastAsia="HGｺﾞｼｯｸM" w:hAnsi="ＭＳ Ｐゴシック"/>'
            f'<w:sz w:val="22"/></w:rPr></w:pPr></w:p></w:tc>'
        )
        row_top = '<w:tblPrEx><w:tblBorders><w:top w:val="single" w:sz="4" w:space="0" w:color="auto"/><w:left w:val="single" w:sz="4" w:space="0" w:color="auto"/><w:bottom w:val="single" w:sz="4" w:space="0" w:color="auto"/><w:right w:val="single" w:sz="4" w:space="0" w:color="auto"/><w:insideH w:val="single" w:sz="4" w:space="0" w:color="auto"/><w:insideV w:val="single" w:sz="4" w:space="0" w:color="auto"/></w:tblBorders></w:tblPrEx><w:trPr><w:cantSplit/><w:trHeight w:val="325"/></w:trPr>'

    bottom_mid = (
        '<w:bottom w:val="single" w:sz="12" w:space="0" w:color="auto"/>'
        if is_last else '<w:bottom w:val="single" w:sz="4" w:space="0" w:color="auto"/>'
    )
    top_mid = '<w:top w:val="single" w:sz="8" w:space="0" w:color="auto"/>' if is_first else (
        '' if is_last else '<w:top w:val="single" w:sz="4" w:space="0" w:color="auto"/>'
    )

    org_cell = (
        f'<w:tc><w:tcPr><w:tcW w:w="2054" w:type="dxa"/>'
        f'<w:tcBorders>{top_mid}<w:left w:val="single" w:sz="8" w:space="0" w:color="auto"/>'
        f'{bottom_mid}<w:right w:val="dotted" w:sz="4" w:space="0" w:color="auto"/></w:tcBorders>'
        f'<w:noWrap/><w:vAlign w:val="center"/></w:tcPr>'
        f'<w:p w14:paraId="{org_paraid}" w14:textId="77777777" w:rsidR="0086772B" '
        f'w:rsidRDefault="0086772B" w:rsidP="008D4858">'
        f'<w:pPr><w:rPr><w:rFonts w:ascii="HGｺﾞｼｯｸM" w:eastAsia="HGｺﾞｼｯｸM" '
        f'w:hAnsi="ＭＳ Ｐゴシック" w:hint="eastAsia"/><w:sz w:val="20"/></w:rPr></w:pPr>'
        f'<w:r><w:rPr><w:rFonts w:ascii="HGｺﾞｼｯｸM" w:eastAsia="HGｺﾞｼｯｸM" '
        f'w:hAnsi="ＭＳ Ｐゴシック" w:hint="eastAsia"/><w:sz w:val="20"/></w:rPr>'
        f'<w:t xml:space="preserve">{xml_escape(affiliation)}</w:t></w:r></w:p></w:tc>'
    )

    names_cell = (
        f'<w:tc><w:tcPr><w:tcW w:w="7089" w:type="dxa"/><w:gridSpan w:val="4"/>'
        f'<w:tcBorders>{top_mid}<w:left w:val="dotted" w:sz="4" w:space="0" w:color="auto"/>'
        f'{bottom_mid}<w:right w:val="single" w:sz="12" w:space="0" w:color="auto"/></w:tcBorders>'
        f'<w:vAlign w:val="center"/></w:tcPr>'
        f'<w:p w14:paraId="{names_paraid}" w14:textId="77777777" w:rsidR="0086772B" '
        f'w:rsidRDefault="0086772B" w:rsidP="008D4858">'
        f'<w:pPr><w:rPr><w:rFonts w:ascii="HGｺﾞｼｯｸM" w:eastAsia="HGｺﾞｼｯｸM" '
        f'w:hAnsi="ＭＳ Ｐゴシック"/><w:sz w:val="18"/><w:szCs w:val="18"/></w:rPr></w:pPr>'
        f'<w:r><w:rPr><w:rFonts w:ascii="HGｺﾞｼｯｸM" w:eastAsia="HGｺﾞｼｯｸM" '
        f'w:hAnsi="ＭＳ Ｐゴシック" w:hint="eastAsia"/><w:sz w:val="18"/><w:szCs w:val="18"/></w:rPr>'
        f'<w:t xml:space="preserve">{xml_escape(names)}</w:t></w:r></w:p></w:tc>'
    )

    tr_open = (
        f'<w:tr w:rsidR="0086772B" w:rsidRPr="00BA12F4" w14:paraId="{next_paraid()}" '
        f'w14:textId="77777777" w:rsidTr="0086772B">{row_top}'
    )
    return tr_open + label_cell + org_cell + names_cell + "</w:tr>"


def build_attendee_rows(groups):
    rows = []
    for i, g in enumerate(groups):
        rows.append(
            attendee_row(
                g["affiliation"], g["names"],
                is_first=(i == 0),
                is_last=(i == len(groups) - 1),
            )
        )
    return "".join(rows)


# ---- main document.xml surgery -----------------------------------------

def replace_meeting_number(xml, number):
    if not number:
        return xml
    return xml.replace("<w:t>第回</w:t>", f"<w:t>第{xml_escape(str(number))}回</w:t>", 1)


def replace_datetime(xml, new_dt):
    pattern = re.compile(
        r'(<w:t[^>]*>)\d{4}年\d{1,2}月\d{1,2}日.*?(</w:t>)', re.S
    )
    return pattern.sub(lambda m: m.group(1) + xml_escape(new_dt) + m.group(2), xml, count=1)


def replace_place(xml, place):
    if not place:
        return xml
    return xml.replace("<w:t>要記入</w:t>", f"<w:t xml:space=\"preserve\">{xml_escape(place)}</w:t>", 1)


def replace_attendees(xml, groups):
    start = xml.find("<w:tr")
    # locate the specific attendee <w:tr> block: it's the one right before </w:tbl>
    tbl_end = xml.find("</w:tbl>")
    # find the start of the *first* attendee row: search backward from tbl_end for
    # the row containing '出席者' label text, then walk forward collecting <w:tr>..</w:tr>
    # up to tbl_end.
    label_idx = xml.rfind("<w:t>出席者</w:t>", 0, tbl_end)
    row_start = xml.rfind("<w:tr ", 0, label_idx)
    old_rows_block = xml[row_start:tbl_end]
    new_rows_block = build_attendee_rows(groups)
    return xml[:row_start] + new_rows_block + xml[tbl_end:]


def replace_theme(xml, theme_text):
    idx = xml.find("<w:t>会議のテーマ</w:t>")
    if idx == -1:
        return xml
    # the theme value is the *next* <w:t ...>...</w:t> after the heading run
    after = xml.find("<w:t", idx + 10)
    m = re.match(r'(<w:t[^>]*>).*?(</w:t>)', xml[after:], re.S)
    old_full = xml[after:after + m.end()]
    new_full = m.group(1) + xml_escape(theme_text) + m.group(2)
    return xml[:after] + new_full + xml[after + m.end():]


def replace_body(xml, blocks):
    idx = xml.find("<w:t>詳細内容</w:t>")
    if idx == -1:
        raise RuntimeError("「詳細内容」見出しが見つかりません")
    # end of that heading paragraph
    body_start = xml.find("</w:p>", idx) + len("</w:p>")
    sectpr_idx = xml.find("<w:sectPr")
    # In this template, <w:sectPr> is a direct child of <w:body> (not wrapped in
    # a trailing paragraph), so we can cut straight up to it.
    new_body = build_body_blocks(blocks)
    return xml[:body_start] + new_body + xml[sectpr_idx:]


def default_output_name(data: dict) -> str:
    """meeting_date_yyyymmdd から標準ファイル名を組み立てる。"""
    ymd = data.get("meeting_date_yyyymmdd", "").strip()
    if not ymd:
        raise ValueError(
            "出力ファイル名を自動決定するには data['meeting_date_yyyymmdd'] "
            "（例: '20260910'）が必要です。--out を明示するか、JSONにこの項目を追加してください。"
        )
    return f"打合せ記録簿_北山文化圏センター_{ymd}.docx"


def generate(base: str, data: dict, out: str = None, workdir: str = None) -> str:
    """
    Lambda/Cloud Functionsから直接呼び出せる関数版。
    base: ベースとなる過去の打合せ記録簿.docxのパス
    data: Step3のAI出力（dict。ファイルではなくパース済みJSONそのもの）
    out : 出力.docxパス。省略時は data['meeting_date_yyyymmdd'] から自動生成し、
          base と同じディレクトリに書き出す。
    workdir: 展開用の作業ディレクトリ。省略時は /tmp/_minutes_gen（Lambda向けデフォルト）。
    戻り値: 生成された.docxの絶対パス（文字列）
    """
    base_path = Path(base)
    if out is None:
        out = str(base_path.parent / default_output_name(data))
    out_path = Path(out)

    work = Path(workdir) if workdir else Path("/tmp/_minutes_gen")
    if work.exists():
        shutil.rmtree(work)
    work.mkdir(parents=True)

    base_copy = work / "base.docx"
    shutil.copy(base_path, base_copy)

    unpacked = work / "unpacked"
    subprocess.run(["unzip", "-q", str(base_copy), "-d", str(unpacked)], check=True)
    for p in unpacked.rglob("*"):
        if p.is_symlink():
            p.unlink()
    subprocess.run([sys.executable, MERGE_RUNS, str(unpacked)], check=True)

    doc_path = unpacked / "word" / "document.xml"
    xml = doc_path.read_text(encoding="utf-8")

    xml = replace_meeting_number(xml, data.get("meeting_number", ""))
    xml = replace_datetime(xml, data.get("datetime_display", ""))
    xml = replace_place(xml, data.get("place", ""))
    xml = replace_attendees(xml, data.get("attendee_groups", []))
    xml = replace_theme(xml, data.get("theme", ""))
    xml = replace_body(xml, data.get("body_blocks", []))

    doc_path.write_text(xml, encoding="utf-8")

    if out_path.exists():
        out_path.unlink()
    subprocess.run(
        ["zip", "-X", "-r", str(out_path.resolve()), "."],
        cwd=str(unpacked), check=True,
    )
    return str(out_path.resolve())


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--base", required=True, help="ベースとなる過去の打合せ記録簿.docx")
    ap.add_argument("--json", required=True, help="Step3のAI出力JSONファイル")
    ap.add_argument("--out", default=None, help="出力.docxパス（省略時は自動命名）")
    args = ap.parse_args()

    data = json.loads(Path(args.json).read_text(encoding="utf-8"))
    out_path = generate(base=args.base, data=data, out=args.out)
    print(f"Wrote {out_path}")


if __name__ == "__main__":
    main()
