import base64
import os
import threading
import mimetypes

# ============================================================
# ENVIRONMENT
# ============================================================

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass


# ============================================================
# FLASK / AUTH IMPORTS
# ============================================================

from flask import (
    Flask,
    render_template,
    request,
    redirect,
    url_for,
    session,
    jsonify,
    send_file,
    Response,
)

from authlib.integrations.flask_client import OAuth

import uuid
import io


# ============================================================
# DATABASE
# ============================================================

from database import database as db
from database.database import DatabaseError


# ============================================================
# CHATBOT LAZY LOADING
#
# IMPORTANT:
# Do not import the chatbot stack while Flask is starting.
#
# The chatbot has optional ML/data dependencies, and a missing
# model package must never prevent Login/Register/Onboarding
# pages from opening.
# ============================================================

ConversationManager = None


def _get_conversation_manager_class():
    global ConversationManager

    if ConversationManager is None:
        try:
            from chatbot.orchestrator.chat_manager import (
                ConversationManager as _ConversationManager
            )

            ConversationManager = _ConversationManager

        except Exception as error:
            app.logger.exception(
                "Chatbot stack could not be loaded: %s",
                error
            )

            raise RuntimeError(
                "The chatbot components could not be loaded. "
                "Login and onboarding are still available; "
                "install requirements and check the terminal "
                "before opening Chat."
            ) from error

    return ConversationManager


# ============================================================
# APP SETUP
# ============================================================

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

app = Flask(__name__)


# ============================================================
# SECRET KEY
# ============================================================

def get_secret_key():
    """
    Get Flask SECRET_KEY.

    Priority:
        1. Environment variable
        2. Existing .flask_secret
        3. Create a new local secret
    """

    env_key = os.environ.get("SECRET_KEY")

    if env_key:
        return env_key

    secret_file = os.path.join(
        BASE_DIR,
        ".flask_secret"
    )

    if os.path.exists(secret_file):
        with open(
            secret_file,
            "r",
            encoding="utf-8"
        ) as handle:

            stored_key = handle.read().strip()

            if stored_key:
                return stored_key

    new_key = os.urandom(24).hex()

    with open(
        secret_file,
        "w",
        encoding="utf-8"
    ) as handle:
        handle.write(new_key)

    return new_key


app.secret_key = get_secret_key()

app.config.update(
    SESSION_COOKIE_HTTPONLY=True,
    SESSION_COOKIE_SAMESITE="Lax",
)


# ============================================================
# GOOGLE OAUTH
# ============================================================

oauth = OAuth(app)

google = oauth.register(
    name="google",
    client_id=os.environ.get("GOOGLE_CLIENT_ID"),
    client_secret=os.environ.get("GOOGLE_CLIENT_SECRET"),
    server_metadata_url=(
        "https://accounts.google.com/"
        ".well-known/openid-configuration"
    ),
    client_kwargs={
        "scope": "openid email profile"
    },
)


# ============================================================
# DATABASE STARTUP
# ============================================================

db.create_database()


try:
    _startup_db_report = db.get_database_diagnostics()

    app.logger.info(
        "HealthBot SQLite: %s",
        _startup_db_report
    )

except Exception:
    app.logger.exception(
        "HealthBot database startup check failed"
    )


# ============================================================
# PER-CONVERSATION MANAGERS
# ============================================================

_conversation_managers = {}


def get_conversation_manager(conversation_id):
    """
    Return a ConversationManager for a specific conversation.

    Managers are keyed by conversation ID rather than the user's
    session so that New Chat actually creates a fresh context.
    """

    if conversation_id not in _conversation_managers:

        _conversation_managers[
            conversation_id
        ] = _get_conversation_manager_class()()

    return _conversation_managers[conversation_id]


def get_or_create_active_conversation_id():
    """
    Return the currently active conversation.

    If the session does not have a valid conversation, create one.
    """

    user_id = current_user_id()

    conv_id = session.get(
        "active_conversation_id"
    )

    if conv_id:

        conversation = db.get_conversation(
            conv_id,
            user_id
        )

        if (
            conversation is not None
            and not conversation["deleted"]
        ):
            return conv_id

    conv_id = db.create_conversation(
        user_id
    )

    session[
        "active_conversation_id"
    ] = conv_id

    return conv_id


def get_conversation_manager_for_current_user():
    """
    Get the manager for the currently active conversation and
    attach the latest user health profile.
    """

    conversation_id = (
        get_or_create_active_conversation_id()
    )

    manager = get_conversation_manager(
        conversation_id
    )

    manager.set_user_profile(
        db.get_user_profile(
            current_user_id()
        )
    )

    return manager, conversation_id


# ============================================================
# BOT TYPE COMPATIBILITY
# ============================================================

LEGACY_BOT_TYPE_MAP = {
    "rule_based": "rule",
    "machine_learning": "ml",
    "classification": "ml",
    "nlp_based": "ml",
    "deep_learning": "dl",
    "retrieval_based": "dl",
    "rag_based": "dl",
    "generation_based": "dl",
}


# ============================================================
# AUTH HELPERS
# ============================================================

def current_user_id():
    return session.get("user_id")


def login_required_page(
    redirect_to="login"
):
    """
    For normal HTML pages.
    """

    if not current_user_id():
        return redirect(
            url_for(redirect_to)
        )

    return None


def get_profile_for_user(user_id):
    """
    Return user profile.

    A missing profile is normal for a new user.
    A database error is not.
    """

    profile = db.get_user_profile(
        user_id
    )

    if (
        profile is None
        and db.LAST_DB_ERROR
        and db.LAST_DB_ERROR.get("operation")
        == "get_user_profile"
    ):

        details = db.LAST_DB_ERROR

        raise DatabaseError(
            "Health profile query failed: "
            f"{details.get('message', 'unknown database error')}"
        )

    return profile


def profile_exists(user_id):
    return (
        get_profile_for_user(user_id)
        is not None
    )


# ============================================================
# PUBLIC / MARKETING PAGES
# ============================================================

@app.route("/")
def home():
    return render_template(
        "home.html"
    )


@app.route("/welcome")
def welcome():
    return redirect(
        url_for("home")
    )


@app.route("/about")
def about():
    return redirect(
        url_for("home")
    )


@app.route("/forgot-password")
def forgot_password():
    return render_template(
        "login.html",
        error=(
            "Password reset isn't available yet. "
            "Please contact support or try logging in again."
        ),
    )


# ============================================================
# REGISTER
# ============================================================

@app.route(
    "/register",
    methods=["GET", "POST"]
)
def register():

    if request.method == "GET":
        return render_template(
            "register.html"
        )

    full_name = request.form.get(
        "name",
        ""
    ).strip()

    first_name = request.form.get(
        "first_name",
        ""
    ).strip()

    last_name = request.form.get(
        "last_name",
        ""
    ).strip()

    if full_name:

        name_parts = [
            part
            for part in full_name.split()
            if part
        ]

        if (
            not first_name
            and name_parts
        ):
            first_name = name_parts[0]

        if (
            not last_name
            and len(name_parts) > 1
        ):
            last_name = " ".join(
                name_parts[1:]
            )

    if not first_name:
        first_name = "User"

    if not last_name:
        last_name = "User"

    email = request.form.get(
        "email",
        ""
    ).strip().lower()

    password = request.form.get(
        "password",
        ""
    )

    confirm_password = request.form.get(
        "confirm_password",
        ""
    )

    if not email or not password:

        return render_template(
            "register.html",
            error=(
                "Please fill in all required fields."
            ),
        )

    if password != confirm_password:

        return render_template(
            "register.html",
            error="Passwords do not match.",
        )

    if len(password) < 6:

        return render_template(
            "register.html",
            error=(
                "Password must be at least "
                "6 characters long."
            ),
        )

    result = db.create_user(
        first_name,
        last_name,
        email,
        password
    )

    if not result.get("success"):

        return render_template(
            "register.html",
            error=result.get(
                "error",
                "Could not create account."
            ),
        )

    session["user_id"] = result[
        "user_id"
    ]

    session["user_name"] = (
        f"{first_name} {last_name}"
    )

    session["user_email"] = email

    return redirect(
        url_for("onboarding")
    )


# ============================================================
# LOGIN
# ============================================================

@app.route(
    "/login",
    methods=["GET", "POST"]
)
def login():

    if request.method == "GET":

        return render_template(
            "login.html"
        )

    email = request.form.get(
        "email",
        ""
    ).strip().lower()

    password = request.form.get(
        "password",
        ""
    )

    if not email or not password:

        return render_template(
            "login.html",
            error=(
                "Please enter your email "
                "and password."
            ),
            email=email,
        )

    user = db.verify_user(
        email,
        password
    )

    if not user:

        db_error = db.LAST_DB_ERROR

        if (
            db_error
            and db_error.get("operation")
            == "get_user_by_email"
        ):

            app.logger.error(
                "Login database failure: %s",
                db_error
            )

            return render_template(
                "login.html",
                error=(
                    "The account database "
                    "could not be read."
                ),
                email=email,
            ), 503

        return render_template(
            "login.html",
            error=(
                "Incorrect email or password."
            ),
            email=email,
        )

    session["user_id"] = user["id"]

    session["user_name"] = (
        f"{user['first_name']} "
        f"{user['last_name']}"
    )

    session["user_email"] = user["email"]

    session.pop(
        "conv_id",
        None
    )

    try:

        has_profile = profile_exists(
            user["id"]
        )

    except DatabaseError:

        app.logger.exception(
            "Login profile lookup failed for user %s",
            user["id"]
        )

        return render_template(
            "login.html",
            error=(
                "Your account was found, but "
                "the health database could not "
                "be read."
            ),
            email=email,
        ), 500

    if not has_profile:

        return redirect(
            url_for("onboarding")
        )

    return redirect(
        url_for("dashboard")
    )


# ============================================================
# GOOGLE LOGIN
# ============================================================

@app.route("/login/google")
def google_login():

    redirect_uri = url_for(
        "google_callback",
        _external=True
    )

    app.logger.info(
        "Google OAuth redirect URI: %s",
        redirect_uri
    )

    return google.authorize_redirect(
        redirect_uri
    )


@app.route(
    "/login/google/callback"
)
def google_callback():

    try:

        token = (
            google.authorize_access_token()
        )

        user_info = token.get(
            "userinfo"
        )

        if not user_info:

            return render_template(
                "login.html",
                error=(
                    "Could not get your "
                    "Google account information."
                ),
            )

        email = user_info.get(
            "email"
        )

        name = user_info.get(
            "name",
            ""
        )

        if not email:

            return render_template(
                "login.html",
                error=(
                    "Google did not provide "
                    "an email address."
                ),
            )

        # Existing account
        user = db.get_user_by_email(
            email
        )

        if user:

            session["user_id"] = user[
                "id"
            ]

            session["user_name"] = (
                f"{user['first_name']} "
                f"{user['last_name']}"
            )

            session["user_email"] = (
                user["email"]
            )

            if not profile_exists(
                user["id"]
            ):

                return redirect(
                    url_for("onboarding")
                )

            return redirect(
                url_for("dashboard")
            )

        # New Google account
        name_parts = (
            name.strip().split()
        )

        first_name = (
            name_parts[0]
            if name_parts
            else "Google"
        )

        last_name = (
            " ".join(name_parts[1:])
            if len(name_parts) > 1
            else "User"
        )

        result = db.create_user(
            first_name,
            last_name,
            email,
            None
        )

        if not result.get("success"):

            return render_template(
                "login.html",
                error=result.get(
                    "error",
                    "Could not create your "
                    "MediChat account."
                ),
            )

        session["user_id"] = result[
            "user_id"
        ]

        session["user_name"] = (
            f"{first_name} {last_name}"
        )

        session["user_email"] = email

        return redirect(
            url_for("onboarding")
        )

    except Exception as error:

        app.logger.exception(
            "Google login failed: %s",
            error
        )

        return render_template(
            "login.html",
            error=(
                "Google login failed. "
                "Please try again."
            ),
        )


# ============================================================
# LOGOUT
# ============================================================

@app.route("/logout")
def logout():

    session.clear()

    return redirect(
        url_for("home")
    )


# ============================================================
# ONBOARDING
# ============================================================

@app.route(
    "/onboarding",
    methods=["GET", "POST"]
)
def onboarding():

    redirect_response = (
        login_required_page()
    )

    if redirect_response:
        return redirect_response

    if request.method == "GET":

        return render_template(
            "onboarding.html",
            user_name=session.get(
                "user_name",
                ""
            ),
        )

    age = request.form.get(
        "age",
        ""
    ).strip()

    sex = request.form.get(
        "sex",
        ""
    ).strip()

    allergies = request.form.get(
        "allergies",
        ""
    ).strip()

    medical_conditions = request.form.get(
        "medical_conditions",
        ""
    ).strip()

    medications = request.form.get(
        "medications",
        ""
    ).strip()

    health_notes = request.form.get(
        "health_notes",
        ""
    ).strip()

    height = request.form.get(
        "height",
        ""
    ).strip()

    weight = request.form.get(
        "weight",
        ""
    ).strip()

    smoking = request.form.get(
        "smoking",
        ""
    ).strip()

    activity_level = request.form.get(
        "activity_level",
        ""
    ).strip()

    # optional answers used for personalised chatbot suggestions
    health_concern = request.form.get(
        "health_concern",
        ""
    ).strip()[:120]

    health_goal = request.form.get(
        "health_goal",
        ""
    ).strip()[:120]

    if not age or not sex:

        return render_template(
            "onboarding.html",
            user_name=session.get(
                "user_name",
                ""
            ),
            error=(
                "Please provide at least "
                "your age and sex."
            ),
        )

    saved = db.save_user_profile(
        current_user_id(),
        age,
        sex,
        allergies,
        medical_conditions,
        medications,
        health_notes,
        height,
        weight,
        smoking,
        activity_level,
        health_concern,
        health_goal,
    )

    if not saved:

        details = (
            db.LAST_DB_ERROR
            or {}
        )

        app.logger.error(
            "Onboarding profile save failed: %s",
            details
        )

        return render_template(
            "onboarding.html",
            user_name=session.get(
                "user_name",
                ""
            ),
            error=(
                "Could not save your health "
                "profile. Check the terminal "
                "for the database error, then "
                "try again."
            ),
        ), 500

    return redirect(
        url_for("onboarding_summary")
    )


# ============================================================
# ONBOARDING SUMMARY ("Your Health Context")
# ============================================================

def get_context_items_for_user(user_id):
    """
    Returns [(label, value), ...] with the health concern and goal the
    user typed during onboarding. Allergies, medications and medical
    conditions are never shown here.
    """

    try:

        from chatbot.personalization.onboarding_context import (
            summary_items,
        )

        return summary_items(
            db.get_user_profile(user_id)
        )

    except Exception:

        app.logger.exception(
            "Could not read onboarding context"
        )

        return []


@app.route("/onboarding/summary")
def onboarding_summary():

    redirect_response = (
        login_required_page()
    )

    if redirect_response:
        return redirect_response

    if not profile_exists(current_user_id()):

        return redirect(
            url_for("onboarding")
        )

    return render_template(
        "onboarding_summary.html",
        user_name=session.get(
            "user_name",
            ""
        ),
        context_items=get_context_items_for_user(
            current_user_id()
        ),
    )


# ============================================================
# PROFILE
# ============================================================

@app.route("/profile")
def profile():

    redirect_response = (
        login_required_page()
    )

    if redirect_response:
        return redirect_response

    row = db.get_user_profile(
        current_user_id()
    )

    profile_data = (
        dict(row)
        if row
        else None
    )

    avatar_path = (
        db.get_user_avatar(
            current_user_id()
        )
    )

    return render_template(
        "health_profiles.html",
        profile=profile_data,
        user_name=session.get(
            "user_name",
            ""
        ),
        user_email=session.get(
            "user_email",
            ""
        ),
        avatar_url=(
            url_for(
                "static",
                filename=avatar_path
            )
            if avatar_path
            else None
        ),
    )


# ============================================================
# AVATAR
# ============================================================

ALLOWED_AVATAR_EXTENSIONS = {
    "png",
    "jpg",
    "jpeg",
    "webp",
}

MAX_AVATAR_SIZE_BYTES = (
    2 * 1024 * 1024
)


@app.route(
    "/api/profile/avatar",
    methods=["POST"]
)
def api_profile_avatar_upload():

    if not current_user_id():

        return jsonify({
            "success": False,
            "login_required": True
        }), 401

    if "avatar" not in request.files:

        return jsonify({
            "success": False,
            "error": (
                "No file was uploaded."
            )
        }), 400

    file = request.files[
        "avatar"
    ]

    if not file or file.filename == "":

        return jsonify({
            "success": False,
            "error": (
                "No file was selected."
            )
        }), 400

    extension = (
        file.filename.rsplit(
            ".",
            1
        )[-1].lower()
        if "." in file.filename
        else ""
    )

    if (
        extension
        not in ALLOWED_AVATAR_EXTENSIONS
    ):

        return jsonify({
            "success": False,
            "error": (
                "Unsupported file type. "
                "Please upload a PNG, JPG, "
                "or WEBP image."
            ),
        }), 400

    file_bytes = file.read()

    if (
        len(file_bytes)
        > MAX_AVATAR_SIZE_BYTES
    ):

        return jsonify({
            "success": False,
            "error": (
                "Image is too large "
                "(max 2MB). Please choose "
                "a smaller file."
            ),
        }), 400

    if len(file_bytes) == 0:

        return jsonify({
            "success": False,
            "error": (
                "The uploaded file is empty."
            ),
        }), 400

    signatures = {
        b"\xff\xd8\xff": "jpg",
        b"\x89PNG\r\n\x1a\n": "png",
        b"RIFF": "webp",
    }

    is_recognized_image = any(
        file_bytes.startswith(
            signature
        )
        for signature in signatures
    )

    if not is_recognized_image:

        return jsonify({
            "success": False,
            "error": (
                "That file does not look "
                "like a valid image."
            ),
        }), 400

    upload_dir = os.path.join(
        app.root_path,
        "static",
        "uploads",
        "avatars"
    )

    os.makedirs(
        upload_dir,
        exist_ok=True
    )

    filename = (
        f"user_{current_user_id()}."
        f"{extension}"
    )

    filepath = os.path.join(
        upload_dir,
        filename
    )

    try:

        with open(
            filepath,
            "wb"
        ) as file_handle:

            file_handle.write(
                file_bytes
            )

    except OSError:

        app.logger.exception(
            "Avatar save failed"
        )

        return jsonify({
            "success": False,
            "error": (
                "Could not save the image."
            ),
        }), 500

    relative_path = (
        f"uploads/avatars/{filename}"
    )

    if not db.update_user_avatar(
        current_user_id(),
        relative_path
    ):

        return jsonify({
            "success": False,
            "error": (
                "Could not update your profile."
            ),
        }), 500

    return jsonify({
        "success": True,
        "avatar_url": url_for(
            "static",
            filename=relative_path
        ),
    })


# ============================================================
# DASHBOARD
# ============================================================

@app.route(
    "/dashboard",
    methods=["GET", "POST"]
)
def dashboard():

    redirect_response = (
        login_required_page()
    )

    if redirect_response:
        return redirect_response

    try:

        has_profile = profile_exists(
            current_user_id()
        )

    except DatabaseError:

        app.logger.exception(
            "Dashboard profile lookup failed for user %s",
            current_user_id()
        )

        return render_template(
            "error.html",
            code=500,
            title="Database connection problem",
            message=(
                "HealthBot could not read "
                "your health profile. See "
                "the terminal or "
                "/diagnostics/database "
                "for details."
            ),
        ), 500

    if not has_profile:

        return redirect(
            url_for("onboarding")
        )

    context = {
        "user_name": session.get(
            "user_name",
            ""
        ),
        "user_email": session.get(
            "user_email",
            ""
        ),
        "stats": db.get_dashboard_stats(
            current_user_id()
        ),
        "recent_chats": db.get_recent_chats(
            current_user_id(),
            limit=5
        ),
        "best_architecture": None,
    }

    try:

        from evaluation.results_store import (
            load_latest_results
        )

        results = (
            load_latest_results()
        )

        if results:

            context[
                "best_architecture"
            ] = results[
                "summary"
            ][
                "best_accuracy"
            ]

    except Exception:

        context[
            "best_architecture"
        ] = None

    if request.method == "POST":

        message = request.form.get(
            "message",
            ""
        ).strip()

        selected_bot = request.form.get(
            "bot",
            "rule"
        )

        bot_type = (
            LEGACY_BOT_TYPE_MAP.get(
                selected_bot,
                selected_bot
            )
        )

        context[
            "selected_bot"
        ] = selected_bot

        context[
            "message"
        ] = message

        if message:

            try:

                manager, conversation_id = (
                    get_conversation_manager_for_current_user()
                )

            except Exception:

                app.logger.exception(
                    "Chatbot initialization "
                    "failed from dashboard"
                )

                context[
                    "response"
                ] = (
                    "The chatbot components "
                    "are not available yet. "
                    "Check the Flask terminal "
                    "and install requirements.txt."
                )

                context[
                    "response_time"
                ] = 0

                return render_template(
                    "dashboard.html",
                    **context
                )

            result = manager.process_message(
                message,
                bot_type=bot_type
            )

            db.save_chat(
                message,
                result["response"],
                result.get(
                    "source",
                    bot_type
                ),
                result["response_time"],
                user_id=current_user_id(),
                conversation_id=conversation_id,
            )

            context[
                "response"
            ] = result["response"]

            context[
                "response_time"
            ] = result[
                "response_time"
            ]

    return render_template(
        "dashboard.html",
        **context
    )


# ============================================================
# SETTINGS
# ============================================================

@app.route(
    "/settings",
    methods=["GET", "POST"]
)
def settings():

    redirect_response = (
        login_required_page()
    )

    if redirect_response:
        return redirect_response

    saved = False

    if request.method == "POST":

        first_name = request.form.get(
            "first_name",
            ""
        ).strip()

        last_name = request.form.get(
            "last_name",
            ""
        ).strip()

        if (
            first_name
            and last_name
        ):

            if db.update_user_name(
                current_user_id(),
                first_name,
                last_name
            ):

                session[
                    "user_name"
                ] = (
                    f"{first_name} "
                    f"{last_name}"
                )

                saved = True

    return render_template(
        "settings.html",
        user_name=session.get(
            "user_name",
            ""
        ),
        user_email=session.get(
            "user_email",
            ""
        ),
        saved=saved,
    )


# ============================================================
# CHAT PAGE
# ============================================================

@app.route("/chat")
def chat_page():

    redirect_response = (
        login_required_page()
    )

    if redirect_response:
        return redirect_response

    try:

        has_profile = profile_exists(
            current_user_id()
        )

    except DatabaseError:

        app.logger.exception(
            "Chat profile lookup failed for user %s",
            current_user_id()
        )

        return render_template(
            "error.html",
            code=500,
            title="Database connection problem",
            message=(
                "HealthBot could not read "
                "your health profile. See "
                "the terminal or "
                "/diagnostics/database "
                "for details."
            ),
        ), 500

    if not has_profile:

        return redirect(
            url_for("onboarding")
        )

    return render_template(
        "chat.html",
        user_name=session.get(
            "user_name",
            ""
        ),
        user_email=session.get(
            "user_email",
            ""
        ),
        context_items=get_context_items_for_user(
            current_user_id()
        ),
    )


# ============================================================
# COMPARISON / ANALYSIS PAGES
# ============================================================

@app.route("/comparison")
def comparison():

    redirect_response = (
        login_required_page()
    )

    if redirect_response:
        return redirect_response

    try:
        from comparison_service import get_examples, scoring_info
        examples = get_examples()
        scoring = scoring_info()
    except Exception:
        app.logger.exception("Could not load comparison examples")
        examples = []
        scoring = {"version": "", "weights": {}, "tie_margin": 2.0, "min_candidates": 2}

    return render_template(
        "comparison.html",
        examples=examples,
        scoring=scoring,
    )


# ------------------------------------------------------------
# COMPARISON - STANDALONE ENDPOINTS
#
# Used only by the Comparison page. They call the Rule-Based,
# ML (TF-IDF + SVM) and DL (DistilBERT) bots directly. They do
# not use chat history, the database, the evaluation system,
# Analysis, User Study or evaluation_questions.csv.
# ------------------------------------------------------------

@app.route("/api/comparison/warmup", methods=["POST"])
def api_comparison_warmup():

    if not current_user_id():
        return jsonify({"success": False, "login_required": True}), 401

    try:
        from comparison_service import warm_up
        warm_up()
    except Exception:
        app.logger.exception("Comparison warm-up failed")

    return jsonify({"success": True})


@app.route("/api/health-chat/ask", methods=["POST"])
def api_health_chat_ask():
    """Chat on the SAME pipelines + response library as Comparison (one model, documented routing).

    Request : {"question": str, "conversation_id": int?, "context_topic": str?}
    Response: the route_chat() result plus {"success", "conversation_id", "next_context_topic", "reply"}.
    Each turn is stored in the existing `chats` / `conversations` tables, so history, search, pin,
    share and export keep working. A missing/foreign conversation_id is rejected (404), never reused.
    """
    if not current_user_id():
        return jsonify({"success": False, "login_required": True}), 401
    payload = request.get_json(silent=True) or {}
    question = str(payload.get("question", "")).strip()
    context_topic = str(payload.get("context_topic") or "")[:80] or None
    conversation_id = payload.get("conversation_id")

    if conversation_id not in (None, ""):
        try:
            conversation_id = int(conversation_id)
        except (TypeError, ValueError):
            return jsonify({"success": False, "error": "Invalid conversation id."}), 400
        if db.get_conversation(conversation_id, current_user_id()) is None:
            return jsonify({"success": False, "error": "Conversation not found."}), 404
    else:
        conversation_id = None

    try:
        from comparison_service import route_chat
        data = route_chat(question, {"topic": context_topic} if context_topic else None)
    except ValueError as error:
        return jsonify({"success": False, "error": str(error)}), 400
    except Exception:
        app.logger.exception("Health chat failed")
        return jsonify({"success": False, "error": "The health chatbot could not answer right now."}), 500

    result = data["result"]
    if conversation_id is None:
        conversation_id = db.create_conversation(current_user_id())
        if conversation_id is None:
            return jsonify({"success": False, "error": "Could not create a conversation (database error)."}), 500
    session["active_conversation_id"] = conversation_id
    db.save_chat(question, result["response"], data["answered_by"],
                 (result.get("inference_ms") or 0) / 1000.0,
                 user_id=current_user_id(), conversation_id=conversation_id)
    data["conversation_id"] = conversation_id
    data["next_context_topic"] = (result.get("reply_topic") or result.get("intent")
                                  if result.get("intent") not in (None, "out_of_scope", "follow_up_simplify", "follow_up_next_steps")
                                  or result.get("reply_topic") else context_topic)
    data["success"] = True
    return jsonify(data)


@app.route("/api/comparison/ask", methods=["POST"])
def api_comparison_ask():

    if not current_user_id():
        return jsonify({
            "success": False,
            "login_required": True,
            "error": "Please login to use Comparison.",
        }), 401

    payload = request.get_json(silent=True) or {}
    question = str(payload.get("question", "")).strip()

    if not question:
        return jsonify({
            "success": False,
            "error": "Please enter a healthcare question.",
        }), 400

    try:
        from comparison_service import run_comparison, model_versions
        from database import database as db
        ctx = payload.get("context_topic")
        data = run_comparison(question, {"topic": str(ctx)[:80]} if ctx else None)
    except ValueError as error:
        return jsonify({"success": False, "error": str(error)}), 400
    except Exception:
        app.logger.exception("Comparison failed")
        return jsonify({
            "success": False,
            "error": "Comparison could not be completed.",
        }), 500

    # Keep the exact responses so a User Study rating always refers to what was shown.
    data["run_id"] = db.save_comparison_run(
        current_user_id(), data["question"], data["results"], model_versions()
    )
    data["success"] = True
    return jsonify(data)


# ------------------------------------------------------------
# COMPARISON - EVALUATION + USER STUDY (real stored data only)
# ------------------------------------------------------------

def _study_participant_id():
    """Pseudonymous id: salted hash of the user id (the raw id is never stored)."""
    import hashlib
    raw = f"{app.secret_key}|study|{current_user_id()}".encode()
    return "P-" + hashlib.sha256(raw).hexdigest()[:10]


@app.route("/api/comparison/evaluation")
def api_comparison_evaluation():
    if not current_user_id():
        return jsonify({"success": False, "login_required": True}), 401
    import json as _json
    path = os.path.join(BASE_DIR, "models", "evaluation", "comparison_eval.json")
    if not os.path.isfile(path):
        return jsonify({"success": False, "error": "No evaluation has been run yet. "
                        "Run: python -m chatbot.health_qa.evaluate"}), 404
    with open(path, encoding="utf-8") as f:
        return jsonify({"success": True, "data": _json.load(f)})


@app.route("/api/comparison/performance")
def api_comparison_performance():
    """Measured per-architecture scores (correctness, safety, quality, response time) from the saved evaluation runs."""
    if not current_user_id():
        return jsonify({"success": False, "login_required": True}), 401
    try:
        import performance_service as ps
        return jsonify({"success": True, "data": ps.benchmark_performance()})
    except Exception:
        app.logger.exception("Performance overview failed")
        return jsonify({"success": False, "error": "The performance overview could not be calculated."}), 500


@app.route("/api/comparison/history")
def api_comparison_history():
    """The signed-in user's OWN comparisons, re-scored from the stored replies (questions may contain health details)."""
    if not current_user_id():
        return jsonify({"success": False, "login_required": True}), 401
    try:
        limit = max(1, min(int(request.args.get("limit", 50)), 200))
    except ValueError:
        limit = 50
    try:
        from database import database as db
        import performance_service as ps
        runs = db.list_comparison_runs_with_results(current_user_id(), limit)
        if runs is None:
            return jsonify({"success": False, "error": "Could not read your comparison history."}), 500
        return jsonify({"success": True, "data": ps.live_history(runs)})
    except Exception:
        app.logger.exception("Comparison history failed")
        return jsonify({"success": False, "error": "Your comparison history could not be calculated."}), 500


# ------------------------------------------------------------
# COMPARISON - REAL DATASET EVALUATION (evaluation_service.py)
# Runs in a background thread; results are saved to
# models/evaluation/runs/<run_id>.json so a refresh re-opens them.
# ------------------------------------------------------------

def _eval_login():
    if not current_user_id():
        return jsonify({"success": False, "login_required": True}), 401
    return None


@app.route("/api/comparison/evaluation/datasets")
def api_eval_datasets():
    denied = _eval_login()
    if denied:
        return denied
    import evaluation_service as ev
    return jsonify({"success": True, "datasets": ev.list_datasets(), "quick_size": ev.QUICK_SIZE})


@app.route("/api/comparison/evaluation/run", methods=["POST"])
def api_eval_run():
    denied = _eval_login()
    if denied:
        return denied
    import evaluation_service as ev
    p = request.get_json(silent=True) or {}
    limit = p.get("limit")
    try:
        limit = int(limit) if limit not in (None, "", 0) else None
        if limit is not None and limit < 1:
            raise ValueError("limit must be a positive number")
        category = p.get("category")
        category = str(category).strip() if category not in (None, "") else None
        run = ev.start_run(str(p.get("dataset") or "question_bank"), str(p.get("mode") or "quick"),
                           limit=limit, user_id=current_user_id(), category=category)
    except ValueError as error:
        return jsonify({"success": False, "error": str(error)}), 400
    except RuntimeError as error:
        return jsonify({"success": False, "error": str(error), "busy": True}), 409
    except Exception:
        app.logger.exception("Could not start evaluation")
        return jsonify({"success": False, "error": "The evaluation could not be started."}), 500
    return jsonify({"success": True, "run": run}), 202


@app.route("/api/comparison/evaluation/status/<run_id>")
def api_eval_status(run_id):
    denied = _eval_login()
    if denied:
        return denied
    import evaluation_service as ev
    st = ev.get_status(run_id)
    if not st:
        return jsonify({"success": False, "error": "Run not found."}), 404
    return jsonify({"success": True, "run": st})


@app.route("/api/comparison/evaluation/runs")
def api_eval_runs():
    denied = _eval_login()
    if denied:
        return denied
    import evaluation_service as ev
    return jsonify({"success": True, "runs": ev.list_runs()})


@app.route("/api/comparison/evaluation/runs/<run_id>")
def api_eval_run_detail(run_id):
    denied = _eval_login()
    if denied:
        return denied
    import evaluation_service as ev
    st = ev.get_run(run_id)
    if not st:
        return jsonify({"success": False, "error": "Run not found."}), 404
    return jsonify({"success": True, "run": st})


@app.route("/api/comparison/evaluation/runs/<run_id>/export.csv")
def api_eval_run_export(run_id):
    denied = _eval_login()
    if denied:
        return denied
    import evaluation_service as ev
    text = ev.export_csv(run_id)
    if text is None:
        return jsonify({"success": False, "error": "Run not found."}), 404
    return Response(text, mimetype="text/csv",
                    headers={"Content-Disposition": f"attachment; filename=evaluation_{run_id}.csv"})


@app.route("/api/comparison/study/runs")
def api_comparison_study_runs():
    """The signed-in user's own recent comparison runs (others' questions may contain personal health information)."""
    if not current_user_id():
        return jsonify({"success": False, "login_required": True}), 401
    runs = db.list_comparison_runs_for_user(current_user_id())
    if runs is None:
        return jsonify({"success": False, "error": "Database error."}), 500
    return jsonify({"success": True, "runs": runs})


@app.route("/api/comparison/study/run/<run_id>")
def api_comparison_study_run(run_id):
    """One stored run (question + the three actual responses) plus this participant's earlier ratings."""
    if not current_user_id():
        return jsonify({"success": False, "login_required": True}), 401
    run = db.get_comparison_run(run_id)
    if not run or run.get("user_id") != current_user_id():
        return jsonify({"success": False, "error": "Comparison run not found."}), 404
    mine = db.get_participant_ratings(_study_participant_id(), run_id) or {}
    responses = {}
    for key in db.STUDY_ARCHITECTURES:
        r = run["results"].get(key) or {}
        responses[key] = {"architecture": key, "name": r.get("name"), "status": r.get("status"), "response": r.get("response", ""),
                          "version": run["model_versions"].get(key), "error": r.get("error"),
                          "ratable": r.get("status") not in (None, "unavailable", "error"),
                          "my_rating": {c: mine[key].get(c) for c in db.STUDY_CRITERIA + ("comment",)} if key in mine else None}
    return jsonify({"success": True, "run": {"run_id": run_id, "question": run["question"], "responses": responses,
                                              "criteria": list(db.STUDY_CRITERIA)}})


@app.route("/api/comparison/study/submit", methods=["POST"])
def api_comparison_study_submit():
    if not current_user_id():
        return jsonify({"success": False, "login_required": True}), 401
    from database import database as db
    data = request.get_json(silent=True) or {}
    if data.get("consent") is not True:
        return jsonify({"success": False, "error": "Please tick the consent box before submitting."}), 400
    result = db.save_comparison_study(
        _study_participant_id(), str(data.get("run_id", "")), data.get("ratings"), data.get("positions"))
    return jsonify(result), (200 if result["success"] else 400)


@app.route("/api/comparison/study/summary")
def api_comparison_study_summary():
    if not current_user_id():
        return jsonify({"success": False, "login_required": True}), 401
    from database import database as db
    summary = db.get_comparison_study_summary()
    if "error" in summary:
        return jsonify({"success": False, "error": summary["error"]}), 500
    return jsonify({"success": True, "data": summary})


@app.route("/api/comparison/study/export.csv")
def api_comparison_study_export():
    if not current_user_id():
        return jsonify({"success": False, "login_required": True}), 401
    import csv, io
    from database import database as db
    rows = db.get_comparison_study_rows()
    if rows is None:
        return jsonify({"success": False, "error": "Database error."}), 500
    buf = io.StringIO()
    cols = ["study_response_id", "participant_id", "run_id", "question_text", "architecture",
            "response_shown", "display_position", "helpfulness", "relevance", "clarity", "trustworthiness",
            "safety", "comment", "model_version", "created_at", "updated_at", "correctness", "completeness"]
    writer = csv.DictWriter(buf, fieldnames=cols, extrasaction="ignore")
    writer.writeheader()
    writer.writerows(rows)
    return Response(buf.getvalue(), mimetype="text/csv",
                    headers={"Content-Disposition": "attachment; filename=comparison_study.csv"})


@app.route("/analysis")
def analysis():

    redirect_response = (
        login_required_page()
    )

    if redirect_response:
        return redirect_response

    return render_template(
        "analysis.html"
    )


# ============================================================
# EVALUATION QUESTION BANK API
#
# THIS IS THE IMPORTANT FIX FOR:
#
#     Evaluation Question 0 questions
#     No questions found
#     Route not found
#
# The Comparison page calls:
#
#     GET /api/evaluation/questions
#
# This endpoint uses the same loader used by the actual
# evaluation system.
# ============================================================

@app.route(
    "/api/evaluation/questions",
    methods=["GET"]
)
def api_evaluation_questions():

    if not current_user_id():

        return jsonify({
            "success": False,
            "login_required": True,
            "error": (
                "Please login to access "
                "evaluation questions."
            ),
        }), 401

    try:

        from evaluation.evaluation_runner import (
            load_and_validate_questions,
            EvaluationValidationError,
        )

        questions = (
            load_and_validate_questions()
        )

    except EvaluationValidationError as error:

        app.logger.error(
            "Evaluation question validation failed: %s",
            error
        )

        return jsonify({
            "success": False,
            "questions": [],
            "count": 0,
            "total_questions": 0,
            "error": str(error),
        }), 400

    except Exception as error:

        app.logger.exception(
            "Could not load evaluation question bank"
        )

        return jsonify({
            "success": False,
            "questions": [],
            "count": 0,
            "total_questions": 0,
            "error": (
                "Could not load the evaluation "
                "question bank. Check "
                "evaluation_questions.csv "
                "and the Flask terminal."
            ),
        }), 500

    output = []

    for question in questions:

        raw_id = question.get(
            "question_id"
        )

        numeric_id = None

        # Supports:
        #
        # 1
        # "1"
        # "Q001"
        # "Q1"
        #
        if raw_id is not None:

            raw_text = str(
                raw_id
            ).strip()

            try:

                numeric_id = int(
                    raw_text
                )

            except ValueError:

                digits = "".join(
                    character
                    for character in raw_text
                    if character.isdigit()
                )

                if digits:

                    try:

                        numeric_id = int(
                            digits
                        )

                    except ValueError:

                        numeric_id = None

        question_text = str(
            question.get(
                "question",
                ""
            )
        ).strip()

        if not question_text:
            continue

        if numeric_id is not None:

            display_id = (
                f"Q{numeric_id:03d}"
            )

        else:

            display_id = str(
                raw_id or ""
            ).strip()

        output.append({
            "question_id": numeric_id,
            "id": display_id,
            "question": question_text,

            "category": str(
                question.get(
                    "category"
                ) or ""
            ).strip(),

            "question_type": str(
                question.get(
                    "question_type"
                ) or ""
            ).strip(),

            "safety_level": str(
                question.get(
                    "safety_level"
                ) or ""
            ).strip(),

            "expected_intent": str(
                question.get(
                    "expected_intent"
                ) or ""
            ).strip(),

            "expected_keywords": str(
                question.get(
                    "expected_keywords"
                ) or ""
            ).strip(),
        })

    output.sort(
        key=lambda item: (
            item["question_id"]
            if item["question_id"] is not None
            else 999999999
        )
    )

    return jsonify({
        "success": True,
        "questions": output,
        "count": len(output),
        "total_questions": len(output),
    })


# ============================================================
# SINGLE QUESTION EVALUATION
# ============================================================

@app.route(
    "/api/evaluation/question",
    methods=["POST"]
)
def api_evaluation_question():

    if not current_user_id():
        return jsonify({
            "success": False,
            "login_required": True,
            "error": "Please login to analyze evaluation questions."
        }), 401

    try:
        data = request.get_json(silent=True) or {}

        question = str(
            data.get("question", "")
        ).strip()

        if not question:
            return jsonify({
                "success": False,
                "error": "Question is required."
            }), 400

        import time

        results = {}

        # ----------------------------------------------------
        # RULE-BASED
        # ----------------------------------------------------
        try:
            start = time.perf_counter()

            manager, conversation_id = (
                get_conversation_manager_for_current_user()
            )

            manager.set_user_profile(
                db.get_user_profile(current_user_id())
            )

            rule_result = manager.process_message(
                question,
                bot_type="rule"
            )

            elapsed = time.perf_counter() - start

            results["rule_based"] = {
                "model": "Rule-Based",
                "response": rule_result.get(
                    "response",
                    "No response returned."
                ),
                "response_time": round(
                    rule_result.get(
                        "response_time",
                        elapsed
                    ),
                    4
                ),
                "score": rule_result.get("score")
            }

        except Exception as error:
            app.logger.exception(
                "Rule-Based question evaluation failed"
            )

            results["rule_based"] = {
                "model": "Rule-Based",
                "response": "Unable to analyze this question.",
                "response_time": None,
                "score": None,
                "error": str(error)
            }

        # ----------------------------------------------------
        # MACHINE LEARNING
        # ----------------------------------------------------
        try:
            start = time.perf_counter()

            manager, conversation_id = (
                get_conversation_manager_for_current_user()
            )

            manager.set_user_profile(
                db.get_user_profile(current_user_id())
            )

            ml_result = manager.process_message(
                question,
                bot_type="ml"
            )

            elapsed = time.perf_counter() - start

            results["machine_learning"] = {
                "model": "Machine Learning",
                "response": ml_result.get(
                    "response",
                    "No response returned."
                ),
                "response_time": round(
                    ml_result.get(
                        "response_time",
                        elapsed
                    ),
                    4
                ),
                "score": ml_result.get("score")
            }

        except Exception as error:
            app.logger.exception(
                "Machine Learning question evaluation failed"
            )

            results["machine_learning"] = {
                "model": "Machine Learning",
                "response": "Unable to analyze this question.",
                "response_time": None,
                "score": None,
                "error": str(error)
            }

        # ----------------------------------------------------
        # DEEP LEARNING
        # ----------------------------------------------------
        try:
            start = time.perf_counter()

            manager, conversation_id = (
                get_conversation_manager_for_current_user()
            )

            manager.set_user_profile(
                db.get_user_profile(current_user_id())
            )

            dl_result = manager.process_message(
                question,
                bot_type="dl"
            )

            elapsed = time.perf_counter() - start

            results["deep_learning"] = {
                "model": "Deep Learning",
                "response": dl_result.get(
                    "response",
                    "No response returned."
                ),
                "response_time": round(
                    dl_result.get(
                        "response_time",
                        elapsed
                    ),
                    4
                ),
                "score": dl_result.get("score")
            }

        except Exception as error:
            app.logger.exception(
                "Deep Learning question evaluation failed"
            )

            results["deep_learning"] = {
                "model": "Deep Learning",
                "response": "Unable to analyze this question.",
                "response_time": None,
                "score": None,
                "error": str(error)
            }

        # ----------------------------------------------------
        # FINAL RESPONSE
        # ----------------------------------------------------
        return jsonify({
            "success": True,
            "question": question,
            "data": results
        })

    except Exception as error:

        app.logger.exception(
            "Single question evaluation failed"
        )

        return jsonify({
            "success": False,
            "error": "Could not evaluate this question."
        }), 500


# ============================================================
# LEGACY ARCHITECTURE ANALYSIS ROUTES
# ============================================================

@app.route(
    "/analysis/<architecture>"
)
def analysis_architecture(
    architecture
):

    allowed = {
        "rule",
        "ml",
        "dl",
    }

    if architecture not in allowed:

        return redirect(
            url_for("analysis")
        )

    return render_template(
        "analysis.html",
        selected_architecture=architecture,
    )


# ============================================================
# PROFILE SETUP COMPATIBILITY
# ============================================================

@app.route(
    "/profile-setup",
    methods=["GET", "POST"]
)
def profile_setup():

    return redirect(
        url_for("onboarding")
    )


# ============================================================
# CHAT API
# ============================================================

MAX_MESSAGE_LENGTH = 2000


def _handle_chat_api(bot_type):
    if not current_user_id():
        return jsonify({
            "success": False,
            "login_required": True,
            "response": "Please login to continue using HealthBot.",
        }), 401

    try:
        if not profile_exists(current_user_id()):
            return jsonify({
                "success": False,
                "profile_required": True,
                "response": (
                    "Please complete your health profile "
                    "before using HealthBot."
                ),
            }), 403

        data = request.get_json(silent=True) or {}
        message = str(data.get("message", "")).strip()

        if not message:
            return jsonify({
                "success": False,
                "response": "Please enter a message.",
            }), 400

        if len(message) > MAX_MESSAGE_LENGTH:
            return jsonify({
                "success": False,
                "response": (
                    f"Message exceeds {MAX_MESSAGE_LENGTH} characters."
                ),
            }), 400

        conversation_id = data.get("conversation_id")

        if conversation_id:
            conversation = db.get_conversation(
                conversation_id,
                current_user_id(),
            )

            if conversation is None:
                return jsonify({
                    "success": False,
                    "response": "Conversation not found.",
                }), 404

            manager = get_conversation_manager(conversation_id)
            manager.set_user_profile(
                db.get_user_profile(current_user_id())
            )
        else:
            manager, conversation_id = (
                get_conversation_manager_for_current_user()
            )

        result = manager.process_message(
            message,
            bot_type=bot_type,
        )

        chatbot_type = result.get(
            "source",
            bot_type or "auto",
        )

        db.save_chat(
            message,
            result["response"],
            chatbot_type,
            result["response_time"],
            user_id=current_user_id(),
            conversation_id=conversation_id,
        )

        return jsonify({
            "success": True,
            "chatbot": chatbot_type,
            "chatbot_type": chatbot_type,
            "response": result["response"],
            "response_time": result["response_time"],
            "confidence": result.get("score"),
            "conversation_id": conversation_id,
        })

    except DatabaseError:
        app.logger.exception("Chat database error")

        return jsonify({
            "success": False,
            "database_error": True,
            "response": "HealthBot could not access the database.",
        }), 503

    except Exception:
        app.logger.exception("Chat API error")

        return jsonify({
            "success": False,
            "response": (
                "Sorry, something went wrong while "
                "processing your message."
            ),
        }), 500

# ============================================================
# CHAT API ROUTES
# ============================================================

@app.route(
    "/api/chat",
    methods=["POST"]
)
def api_chat():

    return _handle_chat_api(
        None
    )


@app.route(
    "/api/rule",
    methods=["POST"]
)
def api_rule():

    return _handle_chat_api(
        "rule"
    )


@app.route(
    "/api/ml",
    methods=["POST"]
)
def api_ml():

    return _handle_chat_api(
        "ml"
    )


@app.route(
    "/api/dl",
    methods=["POST"]
)
def api_dl():

    return _handle_chat_api(
        "dl"
    )


@app.route(
    "/api/rag",
    methods=["POST"]
)
def api_rag():

    return _handle_chat_api(
        "rag"
    )


@app.route(
    "/api/hybrid",
    methods=["POST"]
)
def api_hybrid():

    return _handle_chat_api(
        "hybrid"
    )


# ============================================================
# CONVERSATIONS
# ============================================================

@app.route(
    "/api/conversations/new",
    methods=["POST"]
)
def api_conversation_new():

    if not current_user_id():

        return jsonify({
            "success": False,
            "login_required": True
        }), 401

    conversation_id = (
        db.create_conversation(
            current_user_id()
        )
    )

    if conversation_id is None:

        return jsonify({
            "success": False,
            "error": (
                "Could not create a "
                "new conversation "
                "(database error)."
            ),
        }), 500

    session[
        "active_conversation_id"
    ] = conversation_id

    get_conversation_manager(
        conversation_id
    )

    return jsonify({
        "success": True,
        "conversation_id": conversation_id
    })


@app.route("/api/conversations")
def api_conversations_list():

    if not current_user_id():

        return jsonify({
            "success": False,
            "login_required": True
        }), 401

    search_query = request.args.get(
        "search",
        ""
    ).strip()

    if search_query:

        rows = (
            db.search_conversations(
                current_user_id(),
                search_query
            )
        )

    else:

        rows = (
            db.list_conversations(
                current_user_id(),
                include_archived=True
            )
        )

    active_id = session.get(
        "active_conversation_id"
    )

    return jsonify({
        "success": True,
        "active_conversation_id": active_id,
        "data": [
            {
                "id": row["id"],
                "title": row["title"],
                "pinned": bool(
                    row["pinned"]
                ),
                "archived": bool(
                    row["archived"]
                ),
                "shared": bool(
                    row["share_token"]
                ),
                "created_at": row[
                    "created_at"
                ],
                "updated_at": row[
                    "updated_at"
                ],
            }
            for row in rows
        ],
    })


@app.route(
    "/api/conversations/<int:conversation_id>"
)
def api_conversation_detail(
    conversation_id
):

    if not current_user_id():

        return jsonify({
            "success": False,
            "login_required": True
        }), 401

    conversation = db.get_conversation(
        conversation_id,
        current_user_id()
    )

    if conversation is None:

        return jsonify({
            "success": False,
            "error": (
                "Conversation not found."
            )
        }), 404

    messages = (
        db.get_conversation_messages(
            conversation_id,
            current_user_id()
        )
        or []
    )

    return jsonify({
        "success": True,
        "data": {
            "id": conversation["id"],
            "title": conversation[
                "title"
            ],
            "pinned": bool(
                conversation["pinned"]
            ),
            "archived": bool(
                conversation["archived"]
            ),
            "shared": bool(
                conversation["share_token"]
            ),
            "messages": [
                {
                    "user_message": message[
                        "user_message"
                    ],
                    "bot_response": message[
                        "bot_response"
                    ],
                    "chatbot_type": message[
                        "chatbot_type"
                    ],
                    "response_time": message[
                        "response_time"
                    ],
                    "created_at": message[
                        "created_at"
                    ],
                }
                for message in messages
            ],
        },
    })


@app.route(
    "/api/conversations/<int:conversation_id>/open",
    methods=["POST"]
)
def api_conversation_open(
    conversation_id
):

    if not current_user_id():

        return jsonify({
            "success": False,
            "login_required": True
        }), 401

    conversation = db.get_conversation(
        conversation_id,
        current_user_id()
    )

    if conversation is None:

        return jsonify({
            "success": False,
            "error": (
                "Conversation not found."
            )
        }), 404

    session[
        "active_conversation_id"
    ] = conversation_id

    return jsonify({
        "success": True,
        "conversation_id": conversation_id
    })


@app.route(
    "/api/conversations/<int:conversation_id>/pin",
    methods=["POST"]
)
def api_conversation_pin(
    conversation_id
):

    if not current_user_id():

        return jsonify({
            "success": False,
            "login_required": True
        }), 401

    conversation = db.get_conversation(
        conversation_id,
        current_user_id()
    )

    if conversation is None:

        return jsonify({
            "success": False,
            "error": (
                "Conversation not found."
            )
        }), 404

    new_value = not bool(
        conversation["pinned"]
    )

    ok = db.set_conversation_flag(
        conversation_id,
        current_user_id(),
        "pinned",
        new_value
    )

    if not ok:

        return jsonify({
            "success": False,
            "error": (
                "Could not update "
                "pin state."
            )
        }), 500

    return jsonify({
        "success": True,
        "pinned": new_value
    })


@app.route(
    "/api/conversations/<int:conversation_id>/archive",
    methods=["POST"]
)
def api_conversation_archive(
    conversation_id
):

    if not current_user_id():

        return jsonify({
            "success": False,
            "login_required": True
        }), 401

    conversation = db.get_conversation(
        conversation_id,
        current_user_id()
    )

    if conversation is None:

        return jsonify({
            "success": False,
            "error": (
                "Conversation not found."
            )
        }), 404

    new_value = not bool(
        conversation["archived"]
    )

    ok = db.set_conversation_flag(
        conversation_id,
        current_user_id(),
        "archived",
        new_value
    )

    if not ok:

        return jsonify({
            "success": False,
            "error": (
                "Could not update "
                "archive state."
            )
        }), 500

    return jsonify({
        "success": True,
        "archived": new_value
    })


@app.route(
    "/api/conversations/<int:conversation_id>",
    methods=["DELETE"]
)
def api_conversation_delete(
    conversation_id
):

    if not current_user_id():

        return jsonify({
            "success": False,
            "login_required": True
        }), 401

    conversation = db.get_conversation(
        conversation_id,
        current_user_id()
    )

    if conversation is None:

        return jsonify({
            "success": False,
            "error": (
                "Conversation not found."
            )
        }), 404

    ok = db.set_conversation_flag(
        conversation_id,
        current_user_id(),
        "deleted",
        True
    )

    if not ok:

        return jsonify({
            "success": False,
            "error": (
                "Could not delete "
                "conversation."
            )
        }), 500

    if (
        session.get(
            "active_conversation_id"
        )
        == conversation_id
    ):

        session.pop(
            "active_conversation_id",
            None
        )

    return jsonify({
        "success": True
    })


@app.route(
    "/api/conversations/<int:conversation_id>/share",
    methods=["POST"]
)
def api_conversation_share(
    conversation_id
):

    if not current_user_id():

        return jsonify({
            "success": False,
            "login_required": True
        }), 401

    conversation = db.get_conversation(
        conversation_id,
        current_user_id()
    )

    if conversation is None:

        return jsonify({
            "success": False,
            "error": (
                "Conversation not found."
            )
        }), 404

    token = db.generate_share_token(
        conversation_id,
        current_user_id()
    )

    if token is None:

        return jsonify({
            "success": False,
            "error": (
                "Could not create "
                "a share link."
            )
        }), 500

    share_url = url_for(
        "shared_conversation_view",
        token=token,
        _external=True
    )

    return jsonify({
        "success": True,
        "share_token": token,
        "share_url": share_url
    })


@app.route(
    "/api/conversations/<int:conversation_id>/share",
    methods=["DELETE"]
)
def api_conversation_unshare(
    conversation_id
):

    if not current_user_id():

        return jsonify({
            "success": False,
            "login_required": True
        }), 401

    ok = db.revoke_share_token(
        conversation_id,
        current_user_id()
    )

    if not ok:

        return jsonify({
            "success": False,
            "error": (
                "Conversation not found."
            )
        }), 404

    return jsonify({
        "success": True
    })


# ============================================================
# SHARED CONVERSATION
# ============================================================

@app.route(
    "/shared/<token>"
)
def shared_conversation_view(
    token
):

    conversation, messages = (
        db.get_conversation_by_share_token(
            token
        )
    )

    if conversation is None:

        return render_template(
            "shared_not_found.html"
        ), 404

    return render_template(
        "shared_conversation.html",
        conversation=conversation,
        messages=messages,
    )


# ============================================================
# DOWNLOAD CONVERSATION
# ============================================================

@app.route(
    "/api/conversations/<int:conversation_id>/download"
)
def api_conversation_download(
    conversation_id
):

    if not current_user_id():

        return jsonify({
            "success": False,
            "login_required": True
        }), 401

    conversation = db.get_conversation(
        conversation_id,
        current_user_id()
    )

    if conversation is None:

        return jsonify({
            "success": False,
            "error": (
                "Conversation not found."
            )
        }), 404

    messages = (
        db.get_conversation_messages(
            conversation_id,
            current_user_id()
        )
        or []
    )

    lines = [
        (
            "MediChat Conversation: "
            f"{conversation['title']}"
        ),
        (
            "Exported: "
            f"{conversation['updated_at']}"
        ),
        "=" * 60,
        "",
    ]

    for message in messages:

        lines.append(
            f"[{message['created_at']}] "
            f"You: {message['user_message']}"
        )

        lines.append(
            f"[{message['created_at']}] "
            f"MediChat "
            f"({message['chatbot_type']}): "
            f"{message['bot_response']}"
        )

        lines.append("")

    lines.append("-" * 60)

    lines.append(
        "MediChat is an educational AI "
        "system for healthcare information "
        "and chatbot architecture evaluation. "
        "It does not provide a medical diagnosis "
        "or replace a qualified healthcare "
        "professional."
    )

    transcript = (
        "\n".join(lines)
        .encode("utf-8")
    )

    safe_title = "".join(
        character
        if character.isalnum()
        or character in (
            " ",
            "-",
            "_"
        )
        else "_"
        for character in conversation[
            "title"
        ]
    ).strip() or "conversation"

    return send_file(
        io.BytesIO(transcript),
        mimetype="text/plain",
        as_attachment=True,
        download_name=(
            f"medichat_{safe_title}_"
            f"{conversation_id}.txt"
        ),
    )


# ============================================================
# ANALYSIS API
# ============================================================

@app.route("/api/analysis")
def api_analysis():

    if not current_user_id():

        return jsonify({
            "success": False,
            "login_required": True,
            "error": "Please login to view analysis."
        }), 401

    try:

        # IMPORTANT:
        # SQLite is the source of truth.
        # Do NOT depend on results_store here because
        # results_store can be empty after Flask restarts.

        run = db.get_latest_completed_run()

        if run is None:

            return jsonify({
                "success": True,
                "data": {
                    "run": None,
                    "chatbots": [],
                    "ranking": [],
                    "summary": {},
                    "weights": {},
                    "user_study": {
                        "participant_count": 0,
                        "averages": {}
                    },
                    "is_demo_data": False,
                    "has_completed_run": False
                }
            })

        comparison = _build_run_comparison(
            run["id"]
        )

        if comparison is None:

            return jsonify({
                "success": False,
                "error": (
                    f"Could not build analysis "
                    f"for evaluation run {run['id']}."
                )
            }), 500

        comparison["has_completed_run"] = True
        comparison["is_demo_data"] = False

        return jsonify({
            "success": True,
            "data": comparison
        })

    except Exception as error:

        app.logger.exception(
            "Analysis API failed: %s",
            error
        )

        return jsonify({
            "success": False,
            "error": (
                "Could not load evaluation analysis. "
                "Check the Flask terminal."
            )
        }), 500


@app.route(
    "/api/analysis/hybrid_insights"
)
def api_analysis_hybrid_insights():

    if not current_user_id():

        return jsonify({
            "success": False,
            "login_required": True
        }), 401

    try:

        from evaluation.hybrid_rag_metrics import (
            get_hybrid_rag_insights
        )

        insights = (
            get_hybrid_rag_insights(
                sample_size=15
            )
        )

        return jsonify({
            "success": True,
            "data": insights
        })

    except Exception as error:

        app.logger.exception(
            "Hybrid/RAG insights error: %s",
            error
        )

        return jsonify({
            "success": False,
            "error": (
                "Could not compute "
                "Hybrid/RAG insights "
                "right now."
            ),
        }), 500


@app.route(
    "/api/analysis/charts"
)
def api_analysis_charts():

    if not current_user_id():

        return jsonify({
            "success": False,
            "login_required": True
        }), 401

    try:

        # ----------------------------------------------------
        # ALWAYS GET THE LATEST COMPLETED DATABASE RUN
        # ----------------------------------------------------

        run = db.get_latest_completed_run()

        if run is None:

            return jsonify({
                "success": True,
                "data": {
                    "has_completed_run": False,
                    "run": None,
                    "chatbots": [],
                    "accuracy": [],
                    "precision": [],
                    "recall": [],
                    "f1": [],
                    "response_time": [],
                    "overall_scores": [],
                    "ranking": [],
                    "weights": {},
                    "user_study": {
                        "participant_count": 0,
                        "averages": {}
                    }
                }
            })

        # ----------------------------------------------------
        # BUILD THE SAME COMPARISON DATA USED BY
        # /api/evaluation/latest
        # ----------------------------------------------------

        comparison = _build_run_comparison(
            run["id"]
        )

        if comparison is None:

            return jsonify({
                "success": False,
                "error": (
                    f"Could not build chart data "
                    f"for evaluation run {run['id']}."
                )
            }), 500

        # ----------------------------------------------------
        # TRY EXISTING CHART BUILDER
        #
        # If chart_data.py is available, keep its additional
        # calculated fields.
        # ----------------------------------------------------

        chart_data = {}

        try:

            from evaluation.chart_data import (
                build_chart_dataset
            )

            chart_data = (
                build_chart_dataset()
                or {}
            )

        except Exception as chart_error:

            app.logger.warning(
                "chart_data.py could not be loaded: %s",
                chart_error
            )

        # ----------------------------------------------------
        # DATABASE RUN IS ALWAYS AUTHORITATIVE
        # ----------------------------------------------------

        chart_data["has_completed_run"] = True

        chart_data["run"] = (
            comparison["run"]
        )

        chart_data["chatbots"] = (
            comparison.get(
                "chatbots",
                []
            )
        )

        chart_data["ranking"] = (
            comparison.get(
                "ranking",
                []
            )
        )

        chart_data["weights"] = (
            comparison.get(
                "weights",
                {}
            )
        )

        chart_data["user_study"] = (
            comparison.get(
                "user_study",
                {}
            )
        )

        return jsonify({
            "success": True,
            "data": chart_data
        })

    except Exception as error:

        app.logger.exception(
            "Chart data build failed: %s",
            error
        )

        return jsonify({
            "success": False,
            "error": (
                "Could not build visual "
                "analytics data right now."
            )
        }), 500


# ============================================================
# AUTOMATED EVALUATION
# ============================================================

_evaluation_thread_lock = (
    threading.Lock()
)

_evaluation_thread = None


def _run_evaluation_in_background(
    run_label
):

    from evaluation import (
        progress as eval_progress
    )

    from evaluation.evaluation_runner import (
        run_evaluation,
        EvaluationValidationError,
    )

    try:

        run_evaluation(
            run_label=run_label,
            force=True,
            progress_callback=(
                eval_progress.update_from_event
            ),
        )

    except EvaluationValidationError as error:

        eval_progress.update_from_event({
            "type": "failed",
            "error": str(error)
        })

    except Exception as error:

        app.logger.exception(
            "Background evaluation run crashed"
        )

        eval_progress.update_from_event({
            "type": "failed",
            "error": str(error)
        })


@app.route(
    "/api/evaluation/run",
    methods=["POST"]
)
def api_evaluation_run():

    if not current_user_id():

        return jsonify({
            "success": False,
            "login_required": True
        }), 401

    from database import database as db

    from evaluation import (
        progress as eval_progress
    )

    from evaluation.chatbot_adapter import (
        CHATBOT_NAMES
    )

    from evaluation.evaluation_runner import (
        load_and_validate_questions,
        EvaluationValidationError,
    )

    data = (
        request.get_json(
            silent=True
        )
        or {}
    )

    run_label = str(
        data.get(
            "label"
        )
        or ""
    ).strip() or None

    force = bool(
        data.get("force")
    )

    if (
        not force
        and db.has_running_evaluation()
    ):

        return jsonify({
            "success": False,
            "error": (
                "An evaluation run is "
                "already in progress. "
                "Pass force=true to start "
                "a new one anyway."
            ),
        }), 409

    global _evaluation_thread

    with _evaluation_thread_lock:

        if (
            _evaluation_thread
            and _evaluation_thread.is_alive()
            and not force
        ):

            return jsonify({
                "success": False,
                "error": (
                    "An evaluation run is "
                    "already in progress "
                    "on this server."
                ),
            }), 409

        try:

            questions = (
                load_and_validate_questions()
            )

        except EvaluationValidationError as error:

            return jsonify({
                "success": False,
                "error": str(error)
            }), 400

        eval_progress.reset(
            total_questions=len(
                questions
            ),
            total_chatbots=len(
                CHATBOT_NAMES
            )
        )

        _evaluation_thread = (
            threading.Thread(
                target=(
                    _run_evaluation_in_background
                ),
                args=(run_label,),
                daemon=True,
            )
        )

        _evaluation_thread.start()

    return jsonify({
        "success": True,
        "message": (
            "Evaluation started."
        ),
        "total_questions": len(
            questions
        ),
        "total_chatbots": len(
            CHATBOT_NAMES
        ),
    })


@app.route(
    "/api/evaluation/status"
)
def api_evaluation_status():

    if not current_user_id():

        return jsonify({
            "success": False,
            "login_required": True
        }), 401

    try:

        from evaluation import (
            progress as eval_progress
        )

        # Get the in-memory status first.
        status = (
            eval_progress.get_status()
        )

        # ----------------------------------------------------
        # DATABASE FALLBACK
        #
        # If Flask restarted, in-memory progress is lost.
        # The completed evaluation still exists in SQLite.
        # ----------------------------------------------------

        latest_run = (
            db.get_latest_completed_run()
        )

        if latest_run is not None:

            current_status = ""

            if isinstance(
                status,
                dict
            ):

                current_status = str(
                    status.get(
                        "status",
                        ""
                    )
                ).lower()

            # Do not overwrite a currently running evaluation.
            if current_status not in (
                "running",
                "starting",
                "processing"
            ):

                status = {
                    "status": "completed",
                    "completed": True,

                    "run_id": latest_run[
                        "id"
                    ],

                    "run_label": latest_run[
                        "run_label"
                    ],

                    "total_questions": latest_run[
                        "total_questions"
                    ],

                    "total_chatbots": latest_run[
                        "total_chatbots"
                    ],

                    "total_responses": latest_run[
                        "total_responses"
                    ],

                    "started_at": latest_run[
                        "started_at"
                    ],

                    "completed_at": latest_run[
                        "completed_at"
                    ],

                    "error": None
                }

        return jsonify({
            "success": True,
            "data": status
        })

    except Exception as error:

        app.logger.exception(
            "Evaluation status API failed: %s",
            error
        )

        return jsonify({
            "success": False,
            "error": (
                "Could not load evaluation status."
            )
        }), 500

# ============================================================
# BUILD EVALUATION COMPARISON
def _build_run_comparison(
    run_id
):



    from database import database as db

    from evaluation.chatbot_adapter import (
        CHATBOT_NAMES
    )

    from evaluation.metrics import (
        summarize_results,
        compute_overall_scores,
        OVERALL_SCORE_WEIGHTS,
    )

    run = db.get_evaluation_run(
        run_id
    )

    if run is None:
        return None

    results = db.get_evaluation_results(
        run_id
    )

    bot_summary = (
        summarize_results(
            results
        )
    )

    user_study_averages_raw = (
        db.get_user_study_averages()
    )

    user_rating_map = {
        name: info[
            "avg_overall"
        ]
        for name, info
        in user_study_averages_raw.items()
    }

    scored, ranking = (
        compute_overall_scores(
            bot_summary,
            user_rating_map
        )
    )

    chatbots_payload = []

    for name in CHATBOT_NAMES:

        score = scored.get(
            name
        )

        chatbots_payload.append(
            score
            if score is not None
            else {
                "chatbot_name": name
            }
        )

    return {
        "run": {
            "id": run["id"],
            "run_label": run[
                "run_label"
            ],
            "status": run[
                "status"
            ],
            "total_questions": run[
                "total_questions"
            ],
            "total_chatbots": run[
                "total_chatbots"
            ],
            "total_responses": run[
                "total_responses"
            ],
            "started_at": run[
                "started_at"
            ],
            "completed_at": run[
                "completed_at"
            ],
            "error_message": run[
                "error_message"
            ],
        },

        "chatbots": chatbots_payload,

        "ranking": [
            {
                "rank": index + 1,
                "chatbot_name": row[
                    "chatbot_name"
                ],
                "overall_score": row[
                    "overall_score"
                ],
            }
            for index, row
            in enumerate(ranking)
        ],

        "weights": (
            OVERALL_SCORE_WEIGHTS
        ),

        "user_study": {
            "participant_count": (
                db.get_user_study_participant_count()
            ),
            "averages": (
                user_study_averages_raw
            ),
        },
    }


# ============================================================
# EVALUATION RESULTS
# ============================================================

@app.route(
    "/api/evaluation/results/<int:run_id>"
)
def api_evaluation_results(
    run_id
):

    if not current_user_id():

        return jsonify({
            "success": False,
            "login_required": True
        }), 401

    comparison = (
        _build_run_comparison(
            run_id
        )
    )

    if comparison is None:

        return jsonify({
            "success": False,
            "error": (
                f"Run {run_id} not found."
            ),
        }), 404

    return jsonify({
        "success": True,
        "data": comparison
    })


@app.route(
    "/api/evaluation/latest"
)
def api_evaluation_latest():

    if not current_user_id():

        return jsonify({
            "success": False,
            "login_required": True
        }), 401

    try:

        run = (
            db.get_latest_completed_run()
        )

        if run is None:

            return jsonify({
                "success": True,
                "data": None
            })

        comparison = (
            _build_run_comparison(
                run["id"]
            )
        )

        if comparison is None:

            return jsonify({
                "success": False,
                "error": (
                    f"Could not load evaluation "
                    f"run {run['id']}."
                )
            }), 500

        return jsonify({
            "success": True,
            "data": comparison
        })

    except Exception as error:

        app.logger.exception(
            "Latest evaluation API failed: %s",
            error
        )

        return jsonify({
            "success": False,
            "error": (
                "Could not load the latest "
                "evaluation."
            )
        }), 500

# ============================================================
# EVALUATION EXPORT
# ============================================================

@app.route(
    "/api/evaluation/export/<int:run_id>"
)
def api_evaluation_export(
    run_id
):

    if not current_user_id():

        return jsonify({
            "success": False,
            "login_required": True
        }), 401

    from evaluation.export import (
        export_csv,
        export_excel,
        export_pdf,
        ExportError,
    )

    fmt = request.args.get(
        "format",
        "csv"
    ).lower()

    try:

        if fmt == "csv":

            payload = export_csv(
                run_id
            )

            return send_file(
                io.BytesIO(payload),
                mimetype="text/csv",
                as_attachment=True,
                download_name=(
                    f"medichat_evaluation_"
                    f"run_{run_id}.csv"
                ),
            )

        elif fmt in (
            "xlsx",
            "excel"
        ):

            payload = export_excel(
                run_id
            )

            return send_file(
                io.BytesIO(payload),
                mimetype=(
                    "application/vnd.openxmlformats-"
                    "officedocument.spreadsheetml.sheet"
                ),
                as_attachment=True,
                download_name=(
                    f"medichat_evaluation_"
                    f"run_{run_id}.xlsx"
                ),
            )

        elif fmt == "pdf":

            payload = export_pdf(
                run_id
            )

            return send_file(
                io.BytesIO(payload),
                mimetype="application/pdf",
                as_attachment=True,
                download_name=(
                    f"medichat_evaluation_report_"
                    f"run_{run_id}.pdf"
                ),
            )

        else:

            return jsonify({
                "success": False,
                "error": (
                    f"Unknown format '{fmt}'."
                ),
            }), 400

    except ExportError as error:

        return jsonify({
            "success": False,
            "error": str(error)
        }), 400

    except Exception:

        app.logger.exception(
            "Evaluation export failed"
        )

        return jsonify({
            "success": False,
            "error": (
                "Export failed due to "
                "a server error."
            ),
        }), 500


# ============================================================
# USER STUDY
# ============================================================

PARTICIPANT_SLOTS = [
    f"Participant {i:02d}"
    for i in range(1, 16)
]


def _encode_chatbot_token(
    chatbot_name
):

    return (
        base64.urlsafe_b64encode(
            chatbot_name.encode(
                "utf-8"
            )
        )
        .decode("ascii")
    )


def _decode_chatbot_token(
    token
):

    try:

        return (
            base64.urlsafe_b64decode(
                token.encode("ascii")
            )
            .decode("utf-8")
        )

    except Exception:

        return None


# ============================================================
# USER STUDY PAGE
# ============================================================

@app.route("/user-study")
def user_study_page():

    redirect_response = (
        login_required_page()
    )

    if redirect_response:
        return redirect_response

    return render_template(
        "user_study.html",
        participant_slots=(
            PARTICIPANT_SLOTS
        ),
        user_name=session.get(
            "user_name",
            ""
        ),
    )


# ============================================================
# USER STUDY QUESTION LIST
#
# FIX:
# Handles question IDs stored as:
#
#     1
#     "1"
#     "Q001"
#     "Q1"
# ============================================================

@app.route(
    "/api/user-study/question-list"
)
def api_user_study_question_list():

    if not current_user_id():

        return jsonify({
            "success": False,
            "login_required": True
        }), 401

    from evaluation.evaluation_runner import (
        load_and_validate_questions,
        EvaluationValidationError,
    )

    try:

        questions = (
            load_and_validate_questions()
        )

    except EvaluationValidationError as error:

        return jsonify({
            "success": False,
            "error": str(error)
        }), 400

    except Exception as error:

        app.logger.exception(
            "Could not load user-study questions"
        )

        return jsonify({
            "success": False,
            "error": (
                "Could not load evaluation "
                "questions."
            ),
        }), 500

    data = []

    for question in questions:

        raw_id = question.get(
            "question_id"
        )

        numeric_id = None

        if raw_id is not None:

            raw_text = str(
                raw_id
            ).strip()

            try:

                numeric_id = int(
                    raw_text
                )

            except ValueError:

                digits = "".join(
                    character
                    for character in raw_text
                    if character.isdigit()
                )

                if digits:

                    try:

                        numeric_id = int(
                            digits
                        )

                    except ValueError:

                        numeric_id = None

        if numeric_id is None:
            continue

        data.append({
            "question_id": numeric_id,
            "display_id": (
                f"Q{numeric_id:03d}"
            ),
            "category": question.get(
                "category"
            ),
            "question": question.get(
                "question",
                ""
            ),
        })

    return jsonify({
        "success": True,
        "data": data,
        "count": len(data),
        "total_questions": len(data),
    })


# ============================================================
# USER STUDY SINGLE QUESTION
# ============================================================

@app.route(
    "/api/user-study/question"
)
def api_user_study_question():

    if not current_user_id():

        return jsonify({
            "success": False,
            "login_required": True
        }), 401

    from database import database as db

    from evaluation.chatbot_adapter import (
        CHATBOT_NAMES
    )

    from evaluation.evaluation_runner import (
        load_and_validate_questions,
        EvaluationValidationError,
    )

    participant_id = request.args.get(
        "participant_id",
        ""
    )

    try:

        question_id = int(
            request.args.get(
                "question_id",
                "0"
            )
        )

    except ValueError:

        return jsonify({
            "success": False,
            "error": (
                "Invalid question_id."
            )
        }), 400

    run = (
        db.get_latest_completed_run()
    )

    if run is None:

        return jsonify({
            "success": False,
            "error": (
                "No completed evaluation "
                "run yet. Run the Comparative "
                "Evaluation first so the user "
                "study has real chatbot "
                "responses to show."
            ),
        }), 400

    try:

        questions = (
            load_and_validate_questions()
        )

    except EvaluationValidationError as error:

        return jsonify({
            "success": False,
            "error": str(error)
        }), 400

    def normalize_question_id(
        value
    ):
        try:

            return int(value)

        except (
            TypeError,
            ValueError
        ):

            text_value = str(
                value or ""
            ).strip()

            digits = "".join(
                character
                for character in text_value
                if character.isdigit()
            )

            if digits:

                try:
                    return int(digits)
                except ValueError:
                    return None

            return None

    question_row = next(
        (
            question
            for question in questions
            if normalize_question_id(
                question.get(
                    "question_id"
                )
            ) == question_id
        ),
        None
    )

    if question_row is None:

        return jsonify({
            "success": False,
            "error": (
                f"Question {question_id} "
                "not found."
            ),
        }), 404

    results = (
        db.get_evaluation_results(
            run["id"]
        )
    )

    responses_by_bot = {
        result["chatbot_name"]:
            result["response"]

        for result in results

        if normalize_question_id(
            result.get(
                "question_id"
            )
        ) == question_id

        and not result["is_error"]
    }

    # ========================================================
    # DETERMINISTIC BLIND SHUFFLE
    # ========================================================

    import random

    shuffle_seed = (
        hash(
            (
                participant_id,
                question_id
            )
        )
        & 0xFFFFFFFF
    )

    shuffled_names = list(
        CHATBOT_NAMES
    )

    random.Random(
        shuffle_seed
    ).shuffle(
        shuffled_names
    )

    labels = (
        "ABCDEFGHIJKLMNOPQRSTUVWXYZ"
    )

    blind_responses = []

    for index, name in enumerate(
        shuffled_names
    ):

        response_text = (
            responses_by_bot.get(
                name
            )
        )

        if response_text is None:
            continue

        if index >= len(labels):
            break

        blind_responses.append({
            "label": labels[index],
            "response": response_text,
            "chatbot_token": (
                _encode_chatbot_token(
                    name
                )
            ),
        })

    return jsonify({
        "success": True,
        "data": {
            "run_id": run["id"],
            "question_id": question_id,
            "category": question_row.get(
                "category"
            ),
            "question": question_row[
                "question"
            ],
            "total_questions": len(
                questions
            ),
            "responses": blind_responses,
        },
    })


# ============================================================
# USER STUDY SUBMIT
# ============================================================

@app.route(
    "/api/user-study/submit",
    methods=["POST"]
)
def api_user_study_submit():

    if not current_user_id():

        return jsonify({
            "success": False,
            "login_required": True
        }), 401

    from database import database as db

    data = (
        request.get_json(
            silent=True
        )
        or {}
    )

    participant_id = str(
        data.get(
            "participant_id",
            ""
        )
    ).strip()

    question_id = data.get(
        "question_id"
    )

    ratings = data.get(
        "ratings"
    )

    if participant_id not in (
        PARTICIPANT_SLOTS
    ):

        return jsonify({
            "success": False,
            "error": (
                "participant_id must be "
                "one of the 15 participant "
                "slots."
            ),
        }), 400

    if not isinstance(
        question_id,
        int
    ):

        return jsonify({
            "success": False,
            "error": (
                "question_id must be "
                "an integer."
            ),
        }), 400

    if (
        not isinstance(
            ratings,
            list
        )
        or not ratings
    ):

        return jsonify({
            "success": False,
            "error": (
                "ratings must be a "
                "non-empty list."
            ),
        }), 400

    if len(ratings) < 1:

        return jsonify({
            "success": False,
            "error": (
                "No ratings submitted."
            ),
        }), 400

    saved = 0
    errors = []

    for entry in ratings:

        token = entry.get(
            "chatbot_token"
        )

        chatbot_name = (
            _decode_chatbot_token(
                token
            )
            if token
            else None
        )

        if not chatbot_name:

            errors.append(
                "Invalid or missing "
                "chatbot_token in one "
                "rating."
            )

            continue

        result = (
            db.save_user_study_response(
                participant_id=participant_id,
                chatbot_name=chatbot_name,
                question_id=question_id,
                accuracy_rating=entry.get(
                    "accuracy_rating"
                ),
                clarity_rating=entry.get(
                    "clarity_rating"
                ),
                trust_rating=entry.get(
                    "trust_rating"
                ),
                overall_rating=entry.get(
                    "overall_rating"
                ),
                feedback=entry.get(
                    "feedback"
                ),
            )
        )

        if result["success"]:

            saved += 1

        else:

            errors.append(
                f"{chatbot_name}: "
                f"{result['error']}"
            )

    return jsonify({
        "success": saved > 0,
        "saved": saved,
        "errors": errors,
    })


# ============================================================
# USER STUDY RESULTS
# ============================================================

@app.route(
    "/api/user-study/results"
)
def api_user_study_results():

    if not current_user_id():

        return jsonify({
            "success": False,
            "login_required": True
        }), 401

    from database import database as db

    return jsonify({
        "success": True,
        "data": {
            "participant_count": (
                db.get_user_study_participant_count()
            ),
            "minimum_participants": 10,
            "averages": (
                db.get_user_study_averages()
            ),
        },
    })


# ============================================================
# DIAGNOSTICS
# ============================================================

@app.route(
    "/diagnostics/database"
)
def diagnostics_database():

    report = (
        db.get_database_diagnostics()
    )

    status = (
        200
        if report.get("ok")
        else 503
    )

    return jsonify(
        report
    ), status


@app.route(
    "/diagnostics/routes"
)
def diagnostics_routes():

    routes = []

    for rule in sorted(
        app.url_map.iter_rules(),
        key=lambda item: item.rule
    ):

        routes.append({
            "path": rule.rule,
            "methods": sorted(
                rule.methods
                - {
                    "HEAD",
                    "OPTIONS"
                }
            ),
            "endpoint": rule.endpoint,
        })

    return jsonify({
        "success": True,
        "routes": routes
    })


@app.route(
    "/diagnostics/session"
)
def diagnostics_session():

    return jsonify({
        "authenticated": bool(
            current_user_id()
        ),
        "user_id": current_user_id(),
        "user_name": session.get(
            "user_name"
        ),
        "user_email": session.get(
            "user_email"
        ),
        "has_conversation_id": bool(
            session.get(
                "active_conversation_id"
            )
        ),
    })


# ============================================================
# ERROR HANDLERS
# ============================================================

@app.errorhandler(404)
def not_found(_error):

    if request.path.startswith(
        "/api/"
    ):

        return jsonify({
            "success": False,
            "error": "Route not found",
            "path": request.path,
        }), 404

    return render_template(
        "error.html",
        code=404,
        title="Page not found",
        message=(
            f"The page {request.path} "
            "does not exist in this Flask "
            "application."
        ),
    ), 404


@app.errorhandler(500)
def server_error(_error):

    app.logger.exception(
        "Unhandled server error"
    )

    if request.path.startswith(
        "/api/"
    ):

        return jsonify({
            "success": False,
            "error": (
                "An unexpected server "
                "error occurred."
            ),
            "path": request.path,
        }), 500

    return render_template(
        "error.html",
        code=500,
        title="Application error",
        message=(
            "HealthBot encountered an "
            "internal error. Check the "
            "terminal for the traceback."
        ),
    ), 500


# ============================================================
# ARCHITECTURE WARM-UP
# ============================================================

def warm_up_all_architectures():

    try:

        from chatbot.orchestrator.bot_registry import (
            check_all_architectures_loaded
        )

        print(
            "[STARTUP] Warming up "
            "Rule-Based / ML / DL / "
            "RAG+LLM / Hybrid..."
        )

        report = (
            check_all_architectures_loaded()
        )

        for name, info in report.items():

            status = (
                "OK"
                if info["available"]
                else (
                    f"FAILED "
                    f"({info['error']})"
                )
            )

            print(
                f"[STARTUP]   {name}: "
                f"{status}"
            )

    except Exception as error:

        print(
            "[STARTUP] Warm-up skipped "
            f"due to an error: {error}"
        )




# ============================================================
# RUN APPLICATION
# ============================================================

if __name__ == "__main__":

    # Reloader intentionally disabled.
    warm_up_all_architectures()

    app.run(
        debug=True,
        use_reloader=False,
        port=5000
    )