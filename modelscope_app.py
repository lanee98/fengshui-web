"""Production entry point for the public ModelScope demonstration."""
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent / 'webapp'))
from app import app
from flask import jsonify, request

app.config.update(MAX_CONTENT_LENGTH=2 * 1024 * 1024, SESSION_COOKIE_SECURE=True)


@app.before_request
def public_demo_boundary():
    # Public previews must never expose accounts or spend the owner's API quota.
    if request.path == '/api/account' and request.method == 'GET':
        return jsonify(user=None, publicDemo=True)
    if request.path.startswith('/api/account'):
        return jsonify(error='共享演示暂不开放账号注册'), 403
    if request.path == '/api/aholo/status':
        return jsonify(configured=False, provider='共享演示', model='本地方案', tasks=[], publicDemo=True)
    if request.path.startswith('/api/aholo/'):
        return jsonify(error='共享演示未开放云端建模'), 403


@app.get('/healthz')
def health():
    return jsonify(status='ok')
