"""
common.py - response envelope, errors, auth and CSRF for every /api/v1 endpoint.

Success: {"success": true,  "data": ...}                       (+ "meta" for paginated lists)
Error:   {"success": false, "error": {"code": "...", "message": "..."}}
Internal errors are logged server-side; the client only ever sees a generic message.

CSRF: the SPA uses a session cookie, so every state-changing request (POST/PUT/PATCH/DELETE) must
send the per-session token from GET /api/v1/auth/csrf in the X-CSRF-Token header.
"""
import functools
import hmac
import secrets

from flask import current_app, jsonify, request, session


class ApiError(Exception):
    def __init__(self, code, message, status=400, extra=None):
        super().__init__(message)
        self.code, self.message, self.status, self.extra = code, message, status, extra or {}


def ok(data=None, status=200, meta=None):
    body = {"success": True, "data": data}
    if meta is not None:
        body["meta"] = meta
    return jsonify(body), status


def fail(code, message, status=400, **extra):
    return jsonify({"success": False, "error": {"code": code, "message": message, **extra}}), status


def current_user_id():
    uid = session.get("user_id")
    return int(uid) if uid is not None else None


def login_required(fn):
    @functools.wraps(fn)
    def wrapper(*a, **kw):
        if current_user_id() is None:
            raise ApiError("AUTH_REQUIRED", "Please sign in to continue.", 401)
        return fn(*a, **kw)
    return wrapper


def csrf_token():
    if "csrf_token" not in session:
        session["csrf_token"] = secrets.token_urlsafe(32)
    return session["csrf_token"]


def check_csrf():
    if request.method in ("GET", "HEAD", "OPTIONS") or current_app.config.get("CSRF_DISABLED"):
        return
    sent = request.headers.get("X-CSRF-Token", "")
    expected = session.get("csrf_token", "")
    if not expected or not sent or not hmac.compare_digest(sent, expected):
        raise ApiError("CSRF_FAILED", "Your session token is missing or expired. Please refresh the page.", 403)


def body():
    data = request.get_json(silent=True)
    if data is None:
        if request.data:
            raise ApiError("INVALID_JSON", "The request body must be valid JSON.")
        return {}
    if not isinstance(data, dict):
        raise ApiError("INVALID_JSON", "The request body must be a JSON object.")
    return data


def text_field(data, name, required=True, max_len=1000, min_len=1):
    v = data.get(name)
    if v is None or (isinstance(v, str) and not v.strip()):
        if required:
            raise ApiError("VALIDATION_ERROR", f"'{name}' is required.", extra={"field": name})
        return None
    if not isinstance(v, str):
        raise ApiError("VALIDATION_ERROR", f"'{name}' must be text.", extra={"field": name})
    v = " ".join(v.split()) if name not in ("password",) else v
    if len(v) > max_len:
        raise ApiError("VALIDATION_ERROR", f"'{name}' must be at most {max_len} characters.", extra={"field": name})
    if len(v) < min_len:
        raise ApiError("VALIDATION_ERROR", f"'{name}' must be at least {min_len} characters.", extra={"field": name})
    return v


def int_arg(name, default, lo=1, hi=100):
    try:
        v = int(request.args.get(name, default))
    except (TypeError, ValueError):
        raise ApiError("VALIDATION_ERROR", f"'{name}' must be a whole number.", extra={"field": name})
    return max(lo, min(hi, v))


def page_meta(page, per_page, total):
    return {"page": page, "per_page": per_page, "total": total, "pages": max(1, -(-total // per_page))}
