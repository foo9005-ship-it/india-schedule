# Makeシナリオでのデプロイ（未着手）

コードを書かず Make（旧Integromat）のシナリオとして組む場合のメモ。

## モジュール構成案
1. Webhooks > Custom webhook（Zoomの `recording.completed` を受信）
2. HTTP > Make a request（Zoom APIから文字起こし(VTT)をダウンロード）
3. Anthropic（HTTPモジュール、または対応アプリがあればそれ）
   `/v1/messages` を呼び出し、system に `prompts/system_prompt_v2.md` の内容を設定
4. HTTP > Make a request（要約JSONを、`generate_minutes.py`をラップした
   自前APIエンドポイント、またはLambda/Cloud Functionsに渡す）
5. Google Drive > Upload a file（生成された.docxをアップロード）

## メリット・デメリット
- メリット: コード不要、Zoom/Google Driveの公式アプリ連携が使える
- デメリット: `generate_minutes.py`のXML操作（unzip/zip、merge_runs.py実行）は
  Make単体では実行できないため、結局その部分だけはLambda/Cloud Functionsに
  切り出してMakeから呼び出すハイブリッド構成になる見込み

## TODO
- [ ] Lambda/Cloud Functions側の「JSON→docx生成」APIを先に確定させる
- [ ] Makeシナリオのスクリーンショット/エクスポートをここに保存
