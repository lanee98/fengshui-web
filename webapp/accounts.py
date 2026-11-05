"""Local SQLite accounts for the existing Flask application."""
import datetime
import hashlib
import hmac
import json
import secrets
import sqlite3
from contextlib import contextmanager
from pathlib import Path
from urllib.parse import urlparse

from flask import jsonify, request, session


def install_accounts(app):
    directory = Path(app.root_path) / "instance"
    directory.mkdir(exist_ok=True)
    key = directory / "session.key"
    if not key.exists():
        key.write_bytes(secrets.token_bytes(32))
    app.secret_key = key.read_bytes()
    app.config.update(SESSION_COOKIE_HTTPONLY=True, SESSION_COOKIE_SAMESITE="Lax", MAX_CONTENT_LENGTH=20 * 1024 * 1024)
    database = directory / "accounts.sqlite3"

    @contextmanager
    def connect():
        db = sqlite3.connect(database)
        db.row_factory = sqlite3.Row
        try:
            with db:
                yield db
        finally:
            db.close()

    with connect() as db:
        db.execute("CREATE TABLE IF NOT EXISTS accounts (id INTEGER PRIMARY KEY, username TEXT UNIQUE NOT NULL, password TEXT NOT NULL, profile TEXT NOT NULL)")

    def password_hash(password, salt=None):
        salt = salt or secrets.token_hex(16)
        digest = hashlib.pbkdf2_hmac("sha256", password.encode(), bytes.fromhex(salt), 600000).hex()
        return salt + ":" + digest

    def payload_profile(data):
        if not isinstance(data, dict):
            raise ValueError("请提交有效的档案对象")
        result = {}
        for name in ("nickname", "birthday", "country", "province", "city", "district", "goal"):
            value = data.get(name, "")
            if not isinstance(value, str) or len(value) > 100:
                raise ValueError("档案字段格式不正确")
            result[name] = value.strip()
        for name in ("nickname", "country", "province", "city", "district"):
            if not result[name]:
                raise ValueError("请填写称呼与国家、省份、城市、区县")
        if result["birthday"]:
            try:
                birthday = datetime.date.fromisoformat(result["birthday"])
            except ValueError:
                raise ValueError("生日日期无效")
            if birthday > datetime.date.today() or birthday.year < 1900:
                raise ValueError("请填写有效生日")
        return result

    @app.before_request
    def protect_account_changes():
        if request.path.startswith("/api/account") and request.method != "GET":
            origin = request.headers.get("Origin")
            if (origin and urlparse(origin).netloc != request.host) or request.headers.get("X-Requested-With") != "ImmerseHome":
                return jsonify(error="请从本站页面提交请求"), 403
            if not request.is_json:
                return jsonify(error="请提交 JSON 数据"), 415

    @app.route("/api/account", methods=["GET", "PUT"])
    def account():
        with connect() as db:
            row = db.execute("SELECT id, username, profile FROM accounts WHERE id=?", (session.get("account_id"),)).fetchone()
            if not row:
                return (jsonify(user=None), 200) if request.method == "GET" else (jsonify(error="请先登录"), 401)
            if request.method == "PUT":
                try:
                    profile = payload_profile(request.get_json() or {})
                except ValueError as error:
                    return jsonify(error=str(error)), 400
                db.execute("UPDATE accounts SET profile=? WHERE id=?", (json.dumps(profile, ensure_ascii=False), row["id"]))
            else:
                profile = json.loads(row["profile"])
            return jsonify(user={"username": row["username"], "profile": profile})

    @app.route("/api/account/register", methods=["POST"])
    def register():
        data = request.get_json() or {}
        if not isinstance(data, dict):
            return jsonify(error="请提交有效的账号信息"), 400
        username, password = data.get("username", ""), data.get("password", "")
        if not isinstance(username, str) or not isinstance(password, str):
            return jsonify(error="账号或密码格式不正确"), 400
        username = username.strip()
        if not 3 <= len(username) <= 40 or not 8 <= len(password) <= 128:
            return jsonify(error="账号需 3–40 字，密码需 8–128 字"), 400
        try:
            profile = payload_profile(data)
        except ValueError as error:
            return jsonify(error=str(error)), 400
        try:
            with connect() as db:
                cursor = db.execute("INSERT INTO accounts(username,password,profile) VALUES(?,?,?)", (username, password_hash(password), json.dumps(profile, ensure_ascii=False)))
                account_id = cursor.lastrowid
        except sqlite3.IntegrityError:
            return jsonify(error="该账号已被使用"), 409
        session.clear()
        session["account_id"] = account_id
        return jsonify(user={"username": username, "profile": profile}), 201

    @app.route("/api/account/login", methods=["POST"])
    def login():
        data = request.get_json() or {}
        if not isinstance(data, dict):
            return jsonify(error="账号或密码不正确"), 401
        username, password = data.get("username", ""), data.get("password", "")
        if not isinstance(username, str) or not isinstance(password, str) or len(username) > 40 or len(password) > 128:
            return jsonify(error="账号或密码不正确"), 401
        with connect() as db:
            row = db.execute("SELECT * FROM accounts WHERE username=?", (username.strip(),)).fetchone()
        salt = row["password"].split(":")[0] if row else "0" * 32
        candidate = password_hash(password, salt)
        if not row or not hmac.compare_digest(row["password"], candidate):
            return jsonify(error="账号或密码不正确"), 401
        session.clear()
        session["account_id"] = row["id"]
        return jsonify(user={"username": row["username"], "profile": json.loads(row["profile"])})

    @app.route("/api/account/logout", methods=["POST"])
    def logout():
        session.clear()
        return jsonify(ok=True)
