"""Auth: register, login, logout, current user, CSRF token, account deletion."""
import re

from flask import Blueprint, current_app, session

from api.common import ApiError, body, csrf_token, current_user_id, login_required, ok, text_field
from database import database as db
from database import repository as repo
from extensions import limiter

bp = Blueprint("auth", __name__, url_prefix="/auth")
EMAIL = re.compile(r"^[^@\s]{1,64}@[^@\s]{1,190}\.[A-Za-z]{2,}$")


def _auth_limit():
    return current_app.config["AUTH_RATE_LIMIT"]


def _start_session(user_id):
    session.clear()
    session.permanent = True
    session["user_id"] = int(user_id)
    csrf_token()                                      # fresh token after login (session fixation defence)


def _me(user_id):
    u = repo.public_user(repo.get_user(user_id))
    if not u:
        return None
    profile = repo.get_profile(user_id)
    return {**u, "onboarded": bool(profile and profile.get("consent_at")), "has_profile": profile is not None}


@bp.get("/csrf")
def csrf():
    return ok({"csrf_token": csrf_token()})


@bp.post("/register")
@limiter.limit(_auth_limit)
def register():
    d = body()
    name = text_field(d, "name", max_len=80)
    email = text_field(d, "email", max_len=254).lower()
    password = d.get("password")
    if not EMAIL.match(email):
        raise ApiError("VALIDATION_ERROR", "Please enter a valid email address.", extra={"field": "email"})
    if not isinstance(password, str) or len(password) < 8 or not re.search(r"[A-Za-z]", password) or not re.search(r"\d", password):
        raise ApiError("VALIDATION_ERROR", "Password must be at least 8 characters and include a letter and a number.",
                       extra={"field": "password"})
    if len(password) > 128:
        raise ApiError("VALIDATION_ERROR", "Password must be at most 128 characters.", extra={"field": "password"})
    result = db.create_user(name, "", email, password)
    if not result["success"]:
        if "already exists" in result["error"]:
            raise ApiError("EMAIL_TAKEN", "An account with this email already exists.", 409, {"field": "email"})
        raise ApiError("DATABASE_ERROR", "Your account could not be created. Please try again.", 503)
    _start_session(result["user_id"])
    return ok({"user": _me(result["user_id"]), "csrf_token": csrf_token()}, 201)


@bp.post("/login")
@limiter.limit(_auth_limit)
def login():
    d = body()
    email = (text_field(d, "email", max_len=254) or "").lower()
    password = d.get("password") or ""
    user = db.verify_user(email, password) if isinstance(password, str) else None
    if not user:
        raise ApiError("INVALID_CREDENTIALS", "The email or password is incorrect.", 401)
    _start_session(user["id"])
    return ok({"user": _me(user["id"]), "csrf_token": csrf_token()})


@bp.post("/logout")
def logout():
    session.clear()
    return ok({"logged_out": True, "csrf_token": csrf_token()})


@bp.get("/me")
def me():
    uid = current_user_id()
    user = _me(uid) if uid else None
    if uid and not user:                              # account deleted in another session
        session.clear()
    return ok({"user": user, "csrf_token": csrf_token()})


@bp.patch("/me")
@login_required
def update_me():
    name = text_field(body(), "name", max_len=80)
    repo.rename_user(current_user_id(), name)
    return ok({"user": _me(current_user_id())})


@bp.delete("/account")
@login_required
def delete_account():
    d = body()
    if d.get("confirm") != "DELETE":
        raise ApiError("CONFIRMATION_REQUIRED", "Type DELETE to confirm permanent account deletion.")
    repo.delete_account(current_user_id())
    session.clear()
    return ok({"deleted": True, "csrf_token": csrf_token()})
