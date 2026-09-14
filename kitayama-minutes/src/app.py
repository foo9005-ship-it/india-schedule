#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Zoom Webhookをローカルで受けるためのFlask開発サーバー。

デプロイ方式（Lambda / Cloud Functions / Make）が決まるまでの動作確認用。
実処理は zoom_webhook.handle_webhook_request() に集約してあるので、
デプロイ方式が決まったらそちらをラップするだけでよい。

起動:
    cd kitayama-minutes
    export ZOOM_WEBHOOK_SECRET_TOKEN=xxxx
    python3 src/app.py

Zoom側からアクセスできるようにするには、ngrok等でこのポートを公開し、
発行されたHTTPS URLをZoom AppのEvent Subscriptions設定に登録する。
（例: ngrok http 8080 → https://xxxx.ngrok-free.app/webhook/zoom）
"""

import os
import sys

sys.path.insert(0, os.path.dirname(__file__))

from flask import Flask, jsonify, request

from zoom_webhook import handle_webhook_request

app = Flask(__name__)


@app.route("/webhook/zoom", methods=["POST"])
def zoom_webhook():
    status, body = handle_webhook_request(dict(request.headers), request.get_data())
    return jsonify(body), status


@app.route("/", methods=["GET"])
def health():
    return jsonify({"status": "ok"}), 200


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 8080)), debug=True)
