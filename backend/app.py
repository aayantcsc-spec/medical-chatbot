"""
app.py - HealthBot Research: Flask REST API (/api/v1) + the built React app.

Development:  python app.py                 (API on http://127.0.0.1:5000; run the Vite dev server for the UI)
Production :  cd frontend && npm run build  then  python app.py  (or any WSGI server: app:create_app())

The original Jinja application is kept, unchanged, in legacy_app.py.
"""
import logging
import os
import threading

from flask import Flask, jsonify, request, send_from_directory
from werkzeug.exceptions import HTTPException

from config import Config, FRONTEND_DIST

log = logging.getLogger("healthbot")


def _warm_up():
    """Load models and indexes in the background so the first user request is not slow."""
    def work():
        try:
            import comparison_service as cs
            for k in cs.ORDER:
                cs.run_one(k, "warm up: headache")     # loads the model and runs one inference
            log.info("models warmed up")
        except Exception:
            log.exception("model warm-up failed (requests will load models lazily)")
    threading.Thread(target=work, daemon=True, name="warm-up").start()


def create_app(config=Config):
    app = Flask(__name__, static_folder=None)
    app.config.from_object(config)
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")

    from extensions import limiter
    app.config.setdefault("RATELIMIT_ENABLED", True)
    limiter.init_app(app)

    from flask_cors import CORS
    CORS(app, resources={r"/api/*": {"origins": app.config["CORS_ORIGINS"]}}, supports_credentials=True,
         allow_headers=["Content-Type", "X-CSRF-Token"], methods=["GET", "POST", "PUT", "PATCH", "DELETE"])

    from database.migrations import migrate
    applied = migrate()
    if applied:
        log.info("applied database migrations: %s", applied)

    from api import v1
    from api.common import ApiError
    app.register_blueprint(v1)

    @app.errorhandler(ApiError)
    def api_error(e):
        return jsonify({"success": False, "error": {"code": e.code, "message": e.message, **e.extra}}), e.status

    @app.errorhandler(HTTPException)
    def http_error(e):
        if request.path.startswith("/api/"):
            code = {404: "NOT_FOUND", 405: "METHOD_NOT_ALLOWED", 413: "PAYLOAD_TOO_LARGE", 429: "RATE_LIMITED"}.get(e.code, "HTTP_ERROR")
            msg = "Too many attempts. Please wait a minute and try again." if e.code == 429 else e.description
            return jsonify({"success": False, "error": {"code": code, "message": msg}}), e.code
        return e

    @app.errorhandler(Exception)
    def unhandled(e):
        log.exception("unhandled error on %s %s", request.method, request.path)
        return jsonify({"success": False, "error": {"code": "PROCESSING_ERROR",
                                                    "message": "The request could not be processed."}}), 500

    @app.after_request
    def security_headers(resp):
        resp.headers.setdefault("X-Content-Type-Options", "nosniff")
        resp.headers.setdefault("X-Frame-Options", "DENY")
        resp.headers.setdefault("Referrer-Policy", "same-origin")
        if request.path.startswith("/api/"):
            resp.headers.setdefault("Cache-Control", "no-store")
        return resp

    @app.route("/api/<path:path>", methods=["GET", "POST", "PUT", "PATCH", "DELETE"])
    def unknown_api(path):
        """Any /api path not matched above is a 404, whatever the method (not a 405 from the SPA route)."""
        return jsonify({"success": False, "error": {"code": "NOT_FOUND", "message": "Unknown API endpoint."}}), 404

    # ---- the React build (frontend/dist), with client-side routing fallback
    @app.get("/", defaults={"path": ""})
    @app.get("/<path:path>")
    def spa(path):
        if path.startswith("api/"):
            return jsonify({"success": False, "error": {"code": "NOT_FOUND", "message": "Unknown API endpoint."}}), 404
        if not os.path.isdir(FRONTEND_DIST):
            return ("<h1>HealthBot Research API</h1><p>The React app has not been built. Run <code>npm run dev</code> "
                    "in <code>frontend/</code> (development) or <code>npm run build</code> (production).</p>"), 200
        full = os.path.join(FRONTEND_DIST, path)
        if path and os.path.isfile(full):
            return send_from_directory(FRONTEND_DIST, path)
        return send_from_directory(FRONTEND_DIST, "index.html")

    if app.config.get("WARM_UP_MODELS") and not app.config.get("TESTING"):
        _warm_up()
    return app


if __name__ == "__main__":
    create_app().run(host=os.environ.get("HOST", "127.0.0.1"), port=int(os.environ.get("PORT", "5000")),
                     debug=os.environ.get("FLASK_DEBUG") == "1", use_reloader=False)
