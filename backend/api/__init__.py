"""The /api/v1 REST API."""
from flask import Blueprint

from api import auth, chat, comparison, diagnostics, evaluations, profile
from api.common import check_csrf

v1 = Blueprint("v1", __name__, url_prefix="/api/v1")
v1.before_request(check_csrf)
for module in (auth, profile, chat, comparison, evaluations, diagnostics):
    v1.register_blueprint(module.bp)
