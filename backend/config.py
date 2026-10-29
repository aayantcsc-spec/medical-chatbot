"""
config.py - environment-based configuration for the v1 app (see .env.example).
"""
import os
import secrets
from datetime import timedelta

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
FRONTEND_DIST = os.path.join(os.path.dirname(BASE_DIR), "frontend", "dist")

try:
    from dotenv import load_dotenv
    load_dotenv(os.path.join(BASE_DIR, ".env"))
except ImportError:                                  # python-dotenv is optional
    pass


def _bool(name, default=False):
    return str(os.environ.get(name, str(default))).strip().lower() in ("1", "true", "yes", "on")


def _secret_key():
    """SECRET_KEY from the environment, else a key persisted in backend/.flask_secret (never committed)."""
    key = os.environ.get("SECRET_KEY", "").strip()
    if key:
        return key
    path = os.path.join(BASE_DIR, ".flask_secret")
    if os.path.isfile(path):
        with open(path, encoding="utf-8") as f:
            key = f.read().strip()
    if not key:
        key = secrets.token_hex(32)
        with open(path, "w", encoding="utf-8") as f:
            f.write(key)
    return key


class Config:
    SECRET_KEY = _secret_key()
    ENV = os.environ.get("FLASK_ENV", "development")
    FRONTEND_URL = os.environ.get("FRONTEND_URL", "http://localhost:5173")
    CORS_ORIGINS = [o.strip() for o in os.environ.get("CORS_ORIGINS", FRONTEND_URL).split(",") if o.strip()]
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = "Lax"
    SESSION_COOKIE_SECURE = _bool("SESSION_COOKIE_SECURE", False)
    PERMANENT_SESSION_LIFETIME = timedelta(days=int(os.environ.get("SESSION_DAYS", "7")))
    MAX_CONTENT_LENGTH = 1 * 1024 * 1024             # 1 MB request bodies
    RATELIMIT_STORAGE_URI = os.environ.get("RATELIMIT_STORAGE_URI", "memory://")
    AUTH_RATE_LIMIT = os.environ.get("AUTH_RATE_LIMIT", "10 per minute; 50 per hour")
    WARM_UP_MODELS = _bool("WARM_UP_MODELS", True)
    TESTING = False


class TestConfig(Config):
    TESTING = True
    WARM_UP_MODELS = False
    AUTH_RATE_LIMIT = "1000 per minute"
    RATELIMIT_ENABLED = False
