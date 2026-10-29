"""Health + diagnostics. Never exposes secrets, tokens, environment variables or tracebacks."""
import os

from flask import Blueprint, current_app

from api.common import login_required, ok
from database import database as db
from database import migrations

bp = Blueprint("diagnostics", __name__)


@bp.get("/health")
def health():
    try:
        db_ok = bool(db.database_health_check())
    except Exception:
        db_ok = False
    return ok({"status": "ok" if db_ok else "degraded", "database": db_ok}, 200 if db_ok else 503)


@bp.get("/diagnostics/database")
@login_required
def database():
    d = db.get_database_diagnostics()
    safe = {k: v for k, v in (d or {}).items() if k not in ("path", "database_path", "last_error")}
    safe["file"] = os.path.basename(db.DATABASE_PATH)
    safe["migrations"] = migrations.status()
    return ok(safe)


@bp.get("/diagnostics/routes")
@login_required
def routes():
    rules = sorted((r.rule, sorted(m for m in r.methods if m not in ("HEAD", "OPTIONS")))
                   for r in current_app.url_map.iter_rules() if r.rule.startswith("/api/v1"))
    return ok([{"rule": r, "methods": m} for r, m in rules])


@bp.get("/diagnostics/models")
@login_required
def models():
    from api.chat import bot_list
    return ok({"chatbots": bot_list()})
