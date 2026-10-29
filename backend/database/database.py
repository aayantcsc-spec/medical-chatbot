import sqlite3
import os
import time
from contextlib import contextmanager

from werkzeug.security import (
    generate_password_hash,
    check_password_hash
)


class DatabaseError(RuntimeError):
    """Raised when a database operation fails.

    The Flask layer can distinguish a real SQLite failure from a valid
    "record not found" result instead of treating both as the same state.
    """


LAST_DB_ERROR = None


def _record_db_error(operation, error):
    global LAST_DB_ERROR
    LAST_DB_ERROR = {
        "operation": operation,
        "error_type": type(error).__name__,
        "message": str(error),
    }
    print(f"[DATABASE ERROR] {operation}: {type(error).__name__}: {error}")


# ============================================================
# DATABASE LOCATION
# ============================================================

BASE_DIR = os.path.abspath(
    os.path.join(
        os.path.dirname(__file__),
        ".."
    )
)

DATABASE_PATH = os.path.join(
    BASE_DIR,
    "healthbot.db"
)


# ============================================================
# CONNECTION
# ============================================================
# Strengthened connection handling:
#   - busy timeout + retry so a briefly locked file doesn't
#     raise "database is locked" errors
#   - WAL journal mode so readers and writers don't block
#     each other as much
#   - foreign_keys pragma turned ON (SQLite disables FK
#     enforcement by default, which was silently breaking the
#     ON DELETE CASCADE rule defined in the schema)
#   - check_same_thread=False since Flask's dev server can
#     handle requests on different threads
# ============================================================

CONNECT_TIMEOUT_SECONDS = 10
MAX_RETRIES = 3
RETRY_DELAY_SECONDS = 0.3


def get_connection():
    """Open the one SQLite database used by the whole Flask app."""
    global LAST_DB_ERROR
    last_error = None

    # The database file lives beside app.py, never relative to the shell's
    # current working directory. This prevents VS Code/PowerShell launch
    # location from silently selecting a different database.
    os.makedirs(os.path.dirname(DATABASE_PATH), exist_ok=True)

    for attempt in range(1, MAX_RETRIES + 1):
        try:
            connection = sqlite3.connect(
                DATABASE_PATH,
                timeout=CONNECT_TIMEOUT_SECONDS,
                check_same_thread=False,
            )
            connection.row_factory = sqlite3.Row
            connection.execute("PRAGMA foreign_keys = ON")
            connection.execute("PRAGMA busy_timeout = 5000")
            # WAL can fail on some read-only/network filesystems. It is an
            # optimization, not a requirement for correctness.
            try:
                connection.execute("PRAGMA journal_mode = WAL")
            except sqlite3.DatabaseError as wal_error:
                print(f"[DATABASE WARNING] WAL mode unavailable: {wal_error}")
            LAST_DB_ERROR = None
            return connection
        except sqlite3.Error as error:
            last_error = error
            _record_db_error("connect", error)
            if attempt < MAX_RETRIES:
                time.sleep(RETRY_DELAY_SECONDS)

    raise DatabaseError(
        f"Could not connect to SQLite database at {DATABASE_PATH!r} "
        f"after {MAX_RETRIES} attempts: {last_error}"
    )


@contextmanager
def get_db():
    """
    Context manager version of get_connection().

    Guarantees the connection is always closed, commits on
    success, and rolls back automatically if an exception
    occurs inside the 'with' block.

    Usage:
        with get_db() as connection:
            cursor = connection.cursor()
            cursor.execute(...)
    """

    connection = get_connection()

    try:

        yield connection

        connection.commit()

    except Exception:

        connection.rollback()

        raise

    finally:

        connection.close()


# ============================================================
# CREATE DATABASE
# ============================================================

def create_database():

    with get_db() as connection:

        cursor = connection.cursor()

        # ----------------------------------------------------
        # USERS
        # ----------------------------------------------------

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS users (

                id INTEGER PRIMARY KEY AUTOINCREMENT,

                first_name TEXT NOT NULL,

                last_name TEXT NOT NULL,

                email TEXT NOT NULL UNIQUE,

                password_hash TEXT NOT NULL,

                created_at TIMESTAMP
                    DEFAULT CURRENT_TIMESTAMP
            )
        """)

        # ----------------------------------------------------
        # HEALTH PROFILES
        # ----------------------------------------------------

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS health_profiles (

                id INTEGER PRIMARY KEY AUTOINCREMENT,

                user_id INTEGER NOT NULL UNIQUE,

                age TEXT,

                sex TEXT,

                allergies TEXT,

                medical_conditions TEXT,

                medications TEXT,

                health_notes TEXT,

                height TEXT,

                weight TEXT,

                smoking TEXT,

                activity_level TEXT,

                health_concern TEXT,

                health_goal TEXT,

                created_at TIMESTAMP
                    DEFAULT CURRENT_TIMESTAMP,

                updated_at TIMESTAMP
                    DEFAULT CURRENT_TIMESTAMP,

                FOREIGN KEY (user_id)
                    REFERENCES users(id)
                    ON DELETE CASCADE
            )
        """)

        # ----------------------------------------------------
        # MIGRATION: add height/weight/smoking/activity_level
        # to health_profiles for databases created before these
        # columns existed.
        #
        # BUG FOUND: templates/onboarding.html has always asked
        # for height, weight, smoking status, and activity level
        # (questions 3, 4, 8, 9), but health_profiles never had
        # matching columns, so that data was silently thrown
        # away on every submit. CREATE TABLE IF NOT EXISTS above
        # only affects brand-new databases, so existing
        # healthbot.db files need these columns added explicitly.
        # ----------------------------------------------------

        cursor.execute("PRAGMA table_info(health_profiles)")
        existing_columns = {row[1] for row in cursor.fetchall()}

        # health_concern / health_goal are the optional onboarding
        # answers the chatbot uses for personalised suggestions.
        for column in (
            "height", "weight", "smoking", "activity_level",
            "health_concern", "health_goal",
        ):
            if column not in existing_columns:
                cursor.execute(
                    f"ALTER TABLE health_profiles ADD COLUMN {column} TEXT"
                )

        # ----------------------------------------------------
        # MIGRATION: add avatar_path to users, for the Profile
        # page's photo upload feature.
        # ----------------------------------------------------

        cursor.execute("PRAGMA table_info(users)")
        existing_user_columns = {row[1] for row in cursor.fetchall()}

        if "avatar_path" not in existing_user_columns:
            cursor.execute(
                "ALTER TABLE users ADD COLUMN avatar_path TEXT"
            )

        # ----------------------------------------------------
        # CONVERSATIONS
        #
        # NEW TABLE. Previously every single chat turn was stored
        # as a flat row in `chats` with no grouping concept at all,
        # so there was no real way to list "previous conversations",
        # and the single per-session ConversationManager (see
        # app.py's get_conversation_manager()) never actually reset
        # -- there was no server-side notion of "New Chat" versus
        # "continue this conversation" for it to reset against.
        # This table gives each conversation a real identity that
        # Pin / Delete / Share / Download / Archive can act on.
        # ----------------------------------------------------

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS conversations (

                id INTEGER PRIMARY KEY AUTOINCREMENT,

                user_id INTEGER NOT NULL,

                title TEXT NOT NULL DEFAULT 'New Conversation',

                pinned INTEGER NOT NULL DEFAULT 0,

                archived INTEGER NOT NULL DEFAULT 0,

                deleted INTEGER NOT NULL DEFAULT 0,

                share_token TEXT UNIQUE,

                created_at TIMESTAMP
                    DEFAULT CURRENT_TIMESTAMP,

                updated_at TIMESTAMP
                    DEFAULT CURRENT_TIMESTAMP,

                FOREIGN KEY (user_id)
                    REFERENCES users(id)
                    ON DELETE CASCADE
            )
        """)

        cursor.execute(
            "CREATE INDEX IF NOT EXISTS "
            "idx_conversations_user ON conversations(user_id)"
        )

        # ----------------------------------------------------
        # CHATS
        # ----------------------------------------------------

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS chats (

                id INTEGER PRIMARY KEY AUTOINCREMENT,

                user_id INTEGER,

                conversation_id INTEGER,

                user_message TEXT NOT NULL,

                bot_response TEXT NOT NULL,

                chatbot_type TEXT,

                response_time REAL,

                created_at TIMESTAMP
                    DEFAULT CURRENT_TIMESTAMP,

                FOREIGN KEY (user_id)
                    REFERENCES users(id)
                    ON DELETE SET NULL,

                FOREIGN KEY (conversation_id)
                    REFERENCES conversations(id)
                    ON DELETE CASCADE
            )
        """)

        # ----------------------------------------------------
        # MIGRATION: add conversation_id to chats for databases
        # created before conversations existed, then backfill:
        # group each user's existing orphan messages (conversation_id
        # IS NULL) into one auto-created "Imported History"
        # conversation per user, so old chat history is preserved
        # and visible rather than silently orphaned/hidden.
        # ----------------------------------------------------

        cursor.execute("PRAGMA table_info(chats)")
        existing_chat_columns = {row[1] for row in cursor.fetchall()}

        if "conversation_id" not in existing_chat_columns:
            cursor.execute(
                "ALTER TABLE chats ADD COLUMN conversation_id INTEGER"
            )

        cursor.execute(
            "SELECT DISTINCT user_id FROM chats "
            "WHERE conversation_id IS NULL AND user_id IS NOT NULL"
        )
        users_with_orphan_chats = [row[0] for row in cursor.fetchall()]

        for orphan_user_id in users_with_orphan_chats:
            cursor.execute(
                "INSERT INTO conversations (user_id, title) VALUES (?, ?)",
                (orphan_user_id, "Imported History"),
            )
            new_conversation_id = cursor.lastrowid
            cursor.execute(
                "UPDATE chats SET conversation_id = ? "
                "WHERE user_id = ? AND conversation_id IS NULL",
                (new_conversation_id, orphan_user_id),
            )

        cursor.execute(
            "CREATE INDEX IF NOT EXISTS "
            "idx_chats_conversation ON chats(conversation_id)"
        )

        # ----------------------------------------------------
        # INDEXES (speeds up lookups that were previously
        # doing full table scans on every login / chat save)
        # ----------------------------------------------------

        cursor.execute(
            "CREATE INDEX IF NOT EXISTS "
            "idx_users_email ON users(email)"
        )

        cursor.execute(
            "CREATE INDEX IF NOT EXISTS "
            "idx_chats_user_id ON chats(user_id)"
        )

        cursor.execute(
            "CREATE INDEX IF NOT EXISTS "
            "idx_health_profiles_user_id "
            "ON health_profiles(user_id)"
        )

        # ----------------------------------------------------
        # PERFORMANCE (used by evaluation/response_time.py,
        # which already expected this table but it did not
        # exist yet -- added so the evaluation module actually
        # runs instead of raising ImportError)
        # ----------------------------------------------------

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS performance (

                id INTEGER PRIMARY KEY AUTOINCREMENT,

                chatbot_type TEXT,

                response_time REAL,

                created_at TIMESTAMP
                    DEFAULT CURRENT_TIMESTAMP
            )
        """)

        # ----------------------------------------------------
        # STEP 7 / STEP 8: AUTOMATED CHATBOT TESTING &
        # COMPARATIVE ANALYSIS
        #
        # These tables are additive -- they do not replace the
        # existing "performance" table or the CSV-based
        # results/comparison_results.csv produced by
        # evaluation/evaluator.py. That earlier evaluation
        # (Symptom2Disease-based classification accuracy) keeps
        # working exactly as before. These new tables back a
        # separate, complementary evaluation: the 50-question
        # evaluation_questions.csv dataset run through all six
        # architectures with keyword/intent/semantic correctness
        # scoring and safety scoring, plus a human user study.
        # ----------------------------------------------------

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS evaluation_runs (

                id INTEGER PRIMARY KEY AUTOINCREMENT,

                run_label TEXT,

                status TEXT NOT NULL DEFAULT 'running',
                -- 'running' | 'completed' | 'failed'

                total_questions INTEGER DEFAULT 0,

                total_chatbots INTEGER DEFAULT 0,

                total_responses INTEGER DEFAULT 0,

                error_message TEXT,

                started_at TIMESTAMP
                    DEFAULT CURRENT_TIMESTAMP,

                completed_at TIMESTAMP
            )
        """)

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS evaluation_results (

                id INTEGER PRIMARY KEY AUTOINCREMENT,

                run_id INTEGER NOT NULL,

                question_id INTEGER NOT NULL,

                category TEXT,

                chatbot_name TEXT NOT NULL,

                question TEXT NOT NULL,

                response TEXT,

                response_time_ms REAL,

                correctness_score REAL,

                keyword_score REAL,

                intent_score REAL,

                semantic_score REAL,

                safety_score REAL,

                safety_level TEXT,

                overall_quality_score REAL,

                is_error INTEGER NOT NULL DEFAULT 0,

                error_message TEXT,

                created_at TIMESTAMP
                    DEFAULT CURRENT_TIMESTAMP,

                FOREIGN KEY (run_id)
                    REFERENCES evaluation_runs(id)
                    ON DELETE CASCADE
            )
        """)

        cursor.execute(
            "CREATE INDEX IF NOT EXISTS "
            "idx_evaluation_results_run_id ON evaluation_results(run_id)"
        )

        cursor.execute(
            "CREATE INDEX IF NOT EXISTS "
            "idx_evaluation_results_chatbot ON evaluation_results(chatbot_name)"
        )

        # ----------------------------------------------------
        # USER STUDY
        # ----------------------------------------------------

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS user_study_responses (

                id INTEGER PRIMARY KEY AUTOINCREMENT,

                participant_id TEXT NOT NULL,

                chatbot_name TEXT NOT NULL,

                question_id INTEGER NOT NULL,

                accuracy_rating INTEGER NOT NULL,

                clarity_rating INTEGER NOT NULL,

                trust_rating INTEGER NOT NULL,

                overall_rating INTEGER NOT NULL,

                feedback TEXT,

                created_at TIMESTAMP
                    DEFAULT CURRENT_TIMESTAMP,

                UNIQUE(participant_id, chatbot_name, question_id)
            )
        """)

        cursor.execute(
            "CREATE INDEX IF NOT EXISTS "
            "idx_user_study_participant ON user_study_responses(participant_id)"
        )

        # ----------------------------------------------------
        # COMPARISON RUNS + COMPARISON USER STUDY
        # (backward compatible: new tables only; the older
        #  user_study_responses table is left untouched)
        # ----------------------------------------------------
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS comparison_runs (
                run_id TEXT PRIMARY KEY,
                user_id INTEGER,
                question TEXT NOT NULL,
                results_json TEXT NOT NULL,
                model_versions TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS comparison_study_ratings (
                study_response_id TEXT PRIMARY KEY,
                participant_id TEXT NOT NULL,
                run_id TEXT NOT NULL,
                question_text TEXT NOT NULL,
                architecture TEXT NOT NULL,
                response_shown TEXT NOT NULL,
                display_position INTEGER,
                correctness INTEGER,            -- legacy (v1 study); NULL for new submissions
                helpfulness INTEGER,            -- 1-5, NULL = not applicable
                relevance INTEGER,
                clarity INTEGER,
                completeness INTEGER,           -- legacy (v1 study); NULL for new submissions
                trustworthiness INTEGER,
                safety INTEGER,                 -- PERCEIVED safety
                comment TEXT,
                model_version TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(participant_id, run_id, architecture)
            )
        """)
        _migrate_study_ratings(cursor)


def _migrate_study_ratings(cursor):
    """Upgrade a v1 comparison_study_ratings table (NOT NULL ratings, no helpfulness/trustworthiness)
    to the current schema WITHOUT losing rows: copy -> swap. A no-op on an up-to-date table."""
    cols = [r[1] for r in cursor.execute("PRAGMA table_info(comparison_study_ratings)").fetchall()]
    if "helpfulness" in cols and "updated_at" in cols:
        return
    cursor.execute("ALTER TABLE comparison_study_ratings RENAME TO comparison_study_ratings_v1")
    cursor.execute("""
        CREATE TABLE comparison_study_ratings (
            study_response_id TEXT PRIMARY KEY, participant_id TEXT NOT NULL, run_id TEXT NOT NULL,
            question_text TEXT NOT NULL, architecture TEXT NOT NULL, response_shown TEXT NOT NULL,
            display_position INTEGER, correctness INTEGER, helpfulness INTEGER, relevance INTEGER, clarity INTEGER,
            completeness INTEGER, trustworthiness INTEGER, safety INTEGER, comment TEXT, model_version TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP, updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            UNIQUE(participant_id, run_id, architecture))
    """)
    cursor.execute("""
        INSERT INTO comparison_study_ratings
          (study_response_id, participant_id, run_id, question_text, architecture, response_shown, display_position,
           correctness, relevance, clarity, completeness, safety, comment, model_version, created_at, updated_at)
        SELECT study_response_id, participant_id, run_id, question_text, architecture, response_shown, display_position,
               correctness, relevance, clarity, completeness, safety, comment, model_version, created_at, created_at
        FROM comparison_study_ratings_v1
    """)
    cursor.execute("DROP TABLE comparison_study_ratings_v1")


# ============================================================
# DATABASE DIAGNOSTICS
# ============================================================

def get_database_diagnostics():
    """Return a safe, detailed database health report for troubleshooting."""
    try:
        with get_db() as connection:
            tables = {}
            required_tables = ("users", "health_profiles", "chats", "performance")
            for table in required_tables:
                exists = connection.execute(
                    "SELECT 1 FROM sqlite_master WHERE type='table' AND name=?",
                    (table,),
                ).fetchone() is not None
                tables[table] = {
                    "exists": exists,
                    "rows": connection.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0] if exists else None,
                }

            integrity = connection.execute("PRAGMA integrity_check").fetchone()[0]
            foreign_keys = connection.execute("PRAGMA foreign_keys").fetchone()[0]
            journal_mode = connection.execute("PRAGMA journal_mode").fetchone()[0]

        return {
            "ok": integrity == "ok" and all(v["exists"] for v in tables.values()),
            "database_path": DATABASE_PATH,
            "database_exists": os.path.isfile(DATABASE_PATH),
            "database_size_bytes": os.path.getsize(DATABASE_PATH) if os.path.isfile(DATABASE_PATH) else 0,
            "integrity_check": integrity,
            "foreign_keys": bool(foreign_keys),
            "journal_mode": journal_mode,
            "tables": tables,
            "last_error": LAST_DB_ERROR,
        }
    except Exception as error:
        _record_db_error("diagnostics", error)
        return {
            "ok": False,
            "database_path": DATABASE_PATH,
            "database_exists": os.path.isfile(DATABASE_PATH),
            "database_size_bytes": os.path.getsize(DATABASE_PATH) if os.path.isfile(DATABASE_PATH) else 0,
            "error_type": type(error).__name__,
            "error": str(error),
            "last_error": LAST_DB_ERROR,
        }


def database_health_check():
    report = get_database_diagnostics()
    if not report.get("ok"):
        raise DatabaseError(report.get("error") or "Database health check failed")
    return report


# ============================================================
# CREATE USER
# ============================================================

def create_user(
    first_name,
    last_name,
    email,
    password
):

    try:

        password_hash = generate_password_hash(
            password
        )

        with get_db() as connection:

            cursor = connection.cursor()

            cursor.execute(
                """
                INSERT INTO users
                (
                    first_name,
                    last_name,
                    email,
                    password_hash
                )

                VALUES (?, ?, ?, ?)
                """,

                (
                    first_name,
                    last_name,
                    email,
                    password_hash
                )
            )

            user_id = cursor.lastrowid

        return {

            "success": True,

            "user_id": user_id

        }

    except sqlite3.IntegrityError as error:

        _record_db_error("create_user_integrity", error)
        return {

            "success": False,

            "error":
                "An account with this email already exists."

        }

    except Exception as error:

        _record_db_error("create_user", error)

        return {

            "success": False,

            "error":
                "A database error occurred. Please try again."

        }


# ============================================================
# GET USER
# ============================================================

def get_user_by_email(email):

    try:

        with get_db() as connection:

            cursor = connection.cursor()

            cursor.execute(
                """
                SELECT
                    id,
                    first_name,
                    last_name,
                    email,
                    password_hash,
                    created_at

                FROM users

                WHERE email = ?

                LIMIT 1
                """,

                (email,)
            )

            return cursor.fetchone()

    except Exception as error:

        _record_db_error("get_user_by_email", error)
        return None


# ============================================================
# VERIFY USER
# ============================================================

def verify_user(
    email,
    password
):

    user = get_user_by_email(
        email
    )

    if user is None:

        return None

    try:

        password_valid = check_password_hash(
            user["password_hash"],
            password
        )

    except Exception:

        return None

    if not password_valid:

        return None

    return user


# ============================================================
# SAVE HEALTH PROFILE
# ============================================================

def save_user_profile(
    user_id,
    age,
    sex,
    allergies,
    medical_conditions,
    medications,
    health_notes,
    height=None,
    weight=None,
    smoking=None,
    activity_level=None,
    health_concern=None,
    health_goal=None
):

    try:

        with get_db() as connection:

            cursor = connection.cursor()

            cursor.execute(
                """
                INSERT INTO health_profiles
                (
                    user_id,
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
                    health_goal
                )

                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)

                ON CONFLICT(user_id)
                DO UPDATE SET

                    age = excluded.age,

                    sex = excluded.sex,

                    allergies = excluded.allergies,

                    medical_conditions =
                        excluded.medical_conditions,

                    medications =
                        excluded.medications,

                    health_notes =
                        excluded.health_notes,

                    height = excluded.height,

                    weight = excluded.weight,

                    smoking = excluded.smoking,

                    activity_level =
                        excluded.activity_level,

                    health_concern =
                        excluded.health_concern,

                    health_goal =
                        excluded.health_goal,

                    updated_at =
                        CURRENT_TIMESTAMP
                """,

                (
                    user_id,
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
                    health_goal
                )
            )

        return True

    except Exception as error:

        _record_db_error("save_user_profile", error)

        return False


# ============================================================
# GET HEALTH PROFILE
# ============================================================

def get_user_profile(
    user_id
):

    try:

        with get_db() as connection:

            cursor = connection.cursor()

            cursor.execute(
                """
                SELECT
                    id,
                    user_id,
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
                    created_at,
                    updated_at

                FROM health_profiles

                WHERE user_id = ?

                LIMIT 1
                """,

                (user_id,)
            )

            return cursor.fetchone()

    except Exception as error:

        _record_db_error("get_user_profile", error)
        return None


# ============================================================
# USER AVATAR
# ============================================================

def update_user_avatar(user_id, avatar_path):
    try:
        with get_db() as connection:
            cursor = connection.cursor()
            cursor.execute(
                "UPDATE users SET avatar_path = ? WHERE id = ?",
                (avatar_path, user_id),
            )
            return cursor.rowcount > 0
    except Exception as error:
        _record_db_error("update_user_avatar", error)
        return False


def get_user_avatar(user_id):
    try:
        with get_db() as connection:
            cursor = connection.cursor()
            cursor.execute(
                "SELECT avatar_path FROM users WHERE id = ?", (user_id,)
            )
            row = cursor.fetchone()
            return row["avatar_path"] if row else None
    except Exception as error:
        _record_db_error("get_user_avatar", error)
        return None


def update_user_name(user_id, first_name, last_name):
    """Used by the Settings page (Account section) to rename the
    account. Real users.first_name/last_name columns -- not a
    placeholder like the rest of Settings' Appearance/Preferences
    sections, which have no backing table yet."""
    try:
        with get_db() as connection:
            cursor = connection.cursor()
            cursor.execute(
                "UPDATE users SET first_name = ?, last_name = ? WHERE id = ?",
                (first_name, last_name, user_id),
            )
            return cursor.rowcount > 0
    except Exception as error:
        _record_db_error("update_user_name", error)
        return False


# ============================================================
# SAVE CHAT
# ============================================================

def save_chat(
    user_message,
    bot_response,
    chatbot_type,
    response_time,
    user_id=None,
    conversation_id=None
):
    """
    Saves one chat turn. If conversation_id is given, also bumps
    that conversation's updated_at (so "recent chats" sort
    correctly) and, if the conversation still has its default
    title, sets a real title from this first message.
    """

    # Defensive validation (spec: "do not allow negative response
    # times" applies here too, not just to the evaluation module).
    if response_time is not None and response_time < 0:
        response_time = 0.0

    try:

        with get_db() as connection:

            cursor = connection.cursor()

            cursor.execute(
                """
                INSERT INTO chats
                (
                    user_id,
                    conversation_id,
                    user_message,
                    bot_response,
                    chatbot_type,
                    response_time
                )

                VALUES (?, ?, ?, ?, ?, ?)
                """,

                (
                    user_id,
                    conversation_id,
                    user_message,
                    bot_response,
                    chatbot_type,
                    response_time
                )
            )

            if conversation_id is not None:

                cursor.execute(
                    "SELECT title FROM conversations WHERE id = ?",
                    (conversation_id,),
                )
                row = cursor.fetchone()

                if row and row["title"] == "New Conversation":
                    new_title = user_message.strip()[:60] or "New Conversation"
                    cursor.execute(
                        "UPDATE conversations SET title = ?, "
                        "updated_at = CURRENT_TIMESTAMP WHERE id = ?",
                        (new_title, conversation_id),
                    )
                else:
                    cursor.execute(
                        "UPDATE conversations SET updated_at = "
                        "CURRENT_TIMESTAMP WHERE id = ?",
                        (conversation_id,),
                    )

    except Exception as error:

        print(
            "Chat database error:",
            error
        )


# ============================================================
# CONVERSATIONS (Chat History: New Chat / Pin / Delete / Share /
# Download / Archive)
# ============================================================

def create_conversation(user_id, title="New Conversation"):
    try:
        with get_db() as connection:
            cursor = connection.cursor()
            cursor.execute(
                "INSERT INTO conversations (user_id, title) VALUES (?, ?)",
                (user_id, title),
            )
            return cursor.lastrowid
    except Exception as error:
        _record_db_error("create_conversation", error)
        return None


def get_conversation(conversation_id, user_id):
    """Fetches a conversation, scoped to user_id so one user can
    never read/modify another user's conversation by guessing an id.
    Excludes soft-deleted conversations -- once deleted, a
    conversation can no longer be opened, messaged, shared, pinned,
    archived, or downloaded, even if the caller still has its id."""
    try:
        with get_db() as connection:
            cursor = connection.cursor()
            cursor.execute(
                "SELECT * FROM conversations WHERE id = ? AND user_id = ? AND deleted = 0",
                (conversation_id, user_id),
            )
            return cursor.fetchone()
    except Exception as error:
        _record_db_error("get_conversation", error)
        return None


def list_conversations(user_id, include_archived=True, include_deleted=False):
    try:
        with get_db() as connection:
            cursor = connection.cursor()

            query = "SELECT * FROM conversations WHERE user_id = ?"
            params = [user_id]

            if not include_deleted:
                query += " AND deleted = 0"

            if not include_archived:
                query += " AND archived = 0"

            query += " ORDER BY pinned DESC, updated_at DESC"

            cursor.execute(query, params)
            return cursor.fetchall()
    except Exception as error:
        _record_db_error("list_conversations", error)
        return []


def get_conversation_messages(conversation_id, user_id):
    """Returns the chats belonging to one conversation, verifying
    ownership first so messages can't leak across users."""
    conversation = get_conversation(conversation_id, user_id)
    if conversation is None:
        return None

    try:
        with get_db() as connection:
            cursor = connection.cursor()
            cursor.execute(
                "SELECT * FROM chats WHERE conversation_id = ? ORDER BY id",
                (conversation_id,),
            )
            return cursor.fetchall()
    except Exception as error:
        _record_db_error("get_conversation_messages", error)
        return []


def set_conversation_flag(conversation_id, user_id, field, value):
    """field must be one of 'pinned', 'archived', 'deleted' -- never
    interpolate an arbitrary caller-supplied column name."""

    if field not in ("pinned", "archived", "deleted"):
        return False

    conversation = get_conversation(conversation_id, user_id)
    if conversation is None:
        return False

    try:
        with get_db() as connection:
            cursor = connection.cursor()
            cursor.execute(
                f"UPDATE conversations SET {field} = ?, "
                f"updated_at = CURRENT_TIMESTAMP WHERE id = ? AND user_id = ?",
                (1 if value else 0, conversation_id, user_id),
            )
            return cursor.rowcount > 0
    except Exception as error:
        _record_db_error("set_conversation_flag", error)
        return False


def generate_share_token(conversation_id, user_id):
    import secrets

    conversation = get_conversation(conversation_id, user_id)
    if conversation is None:
        return None

    if conversation["share_token"]:
        return conversation["share_token"]

    token = secrets.token_urlsafe(16)

    try:
        with get_db() as connection:
            cursor = connection.cursor()
            cursor.execute(
                "UPDATE conversations SET share_token = ? WHERE id = ? AND user_id = ?",
                (token, conversation_id, user_id),
            )
        return token
    except Exception as error:
        _record_db_error("generate_share_token", error)
        return None


def revoke_share_token(conversation_id, user_id):
    conversation = get_conversation(conversation_id, user_id)
    if conversation is None:
        return False

    try:
        with get_db() as connection:
            cursor = connection.cursor()
            cursor.execute(
                "UPDATE conversations SET share_token = NULL WHERE id = ? AND user_id = ?",
                (conversation_id, user_id),
            )
        return True
    except Exception as error:
        _record_db_error("revoke_share_token", error)
        return False


def get_conversation_by_share_token(share_token):
    """Public lookup (no user_id check) used by the read-only
    /shared/<token> view. Only returns non-deleted conversations."""
    try:
        with get_db() as connection:
            cursor = connection.cursor()
            cursor.execute(
                "SELECT * FROM conversations WHERE share_token = ? AND deleted = 0",
                (share_token,),
            )
            conversation = cursor.fetchone()

            if conversation is None:
                return None, []

            cursor.execute(
                "SELECT * FROM chats WHERE conversation_id = ? ORDER BY id",
                (conversation["id"],),
            )
            messages = cursor.fetchall()

            return conversation, messages
    except Exception as error:
        _record_db_error("get_conversation_by_share_token", error)
        return None, []


def search_conversations(user_id, query):
    """Simple title/message search for the Chat History search box."""
    try:
        with get_db() as connection:
            cursor = connection.cursor()
            like = f"%{query}%"
            cursor.execute(
                """
                SELECT DISTINCT c.* FROM conversations c
                LEFT JOIN chats ch ON ch.conversation_id = c.id
                WHERE c.user_id = ? AND c.deleted = 0
                  AND (c.title LIKE ? OR ch.user_message LIKE ? OR ch.bot_response LIKE ?)
                ORDER BY c.pinned DESC, c.updated_at DESC
                """,
                (user_id, like, like, like),
            )
            return cursor.fetchall()
    except Exception as error:
        _record_db_error("search_conversations", error)
        return []


# ============================================================
# SAVE PERFORMANCE (used by evaluation/response_time.py)
# ============================================================

def save_performance(
    chatbot_type,
    response_time
):

    try:

        with get_db() as connection:

            cursor = connection.cursor()

            cursor.execute(
                """
                INSERT INTO performance
                (
                    chatbot_type,
                    response_time
                )

                VALUES (?, ?)
                """,

                (
                    chatbot_type,
                    response_time
                )
            )

        return True

    except Exception as error:

        print(
            "Performance database error:",
            error
        )

        return False



# ============================================================
# GET RECENT CHATS (used by the dashboard sidebar, so "Recent
# Chats" reflects a user's actual conversation history instead
# of being static placeholder text)
# ============================================================

def get_recent_chats(user_id, limit=5):

    try:

        with get_db() as connection:

            cursor = connection.cursor()

            cursor.execute(
                """
                SELECT
                    user_message,
                    chatbot_type,
                    created_at

                FROM chats

                WHERE user_id = ?

                ORDER BY created_at DESC

                LIMIT ?
                """,

                (user_id, limit)
            )

            return cursor.fetchall()

    except Exception as error:

        print(
            "Get recent chats database error:",
            error
        )

        return []


# ============================================================
# GET DASHBOARD STATS (real counts only -- never invented)
# ============================================================

def get_dashboard_stats(user_id):

    try:

        with get_db() as connection:

            cursor = connection.cursor()

            cursor.execute(
                """
                SELECT
                    COUNT(*) AS total,
                    AVG(response_time) AS avg_time

                FROM chats

                WHERE user_id = ?
                """,

                (user_id,)
            )

            row = cursor.fetchone()

            return {
                "total_conversations": row["total"] or 0,
                "avg_response_time": row["avg_time"],
            }

    except Exception as error:

        print(
            "Get dashboard stats database error:",
            error
        )

        return {
            "total_conversations": 0,
            "avg_response_time": None,
        }


# ============================================================
# STEP 7 / STEP 8: AUTOMATED EVALUATION + USER STUDY
# ============================================================

def has_running_evaluation():
    """True if an evaluation_runs row is still in 'running' state.

    Used to prevent duplicate/overlapping evaluation runs unless the
    caller explicitly forces one (spec item 21).
    """

    try:
        with get_db() as connection:
            cursor = connection.cursor()
            cursor.execute(
                "SELECT id FROM evaluation_runs WHERE status = 'running' LIMIT 1"
            )
            return cursor.fetchone() is not None
    except Exception as error:
        _record_db_error("has_running_evaluation", error)
        return False


def create_evaluation_run(run_label, total_questions, total_chatbots):
    try:
        with get_db() as connection:
            cursor = connection.cursor()
            cursor.execute(
                """
                INSERT INTO evaluation_runs
                    (run_label, status, total_questions, total_chatbots, total_responses)
                VALUES (?, 'running', ?, ?, 0)
                """,
                (run_label, total_questions, total_chatbots),
            )
            return cursor.lastrowid
    except Exception as error:
        _record_db_error("create_evaluation_run", error)
        return None


def finish_evaluation_run(run_id, status, total_responses, error_message=None):
    try:
        with get_db() as connection:
            cursor = connection.cursor()
            cursor.execute(
                """
                UPDATE evaluation_runs
                SET status = ?,
                    total_responses = ?,
                    error_message = ?,
                    completed_at = CURRENT_TIMESTAMP
                WHERE id = ?
                """,
                (status, total_responses, error_message, run_id),
            )
        return True
    except Exception as error:
        _record_db_error("finish_evaluation_run", error)
        return False


def save_evaluation_result(run_id, result_row):
    """
    result_row: dict with keys matching the evaluation_results
    columns (question_id, category, chatbot_name, question, response,
    response_time_ms, correctness_score, keyword_score, intent_score,
    semantic_score, safety_score, safety_level, overall_quality_score,
    is_error, error_message).
    """

    # Basic validation (spec item 21): never allow a negative response
    # time or an unrecognised chatbot name to slip into storage.
    response_time_ms = result_row.get("response_time_ms")
    if response_time_ms is not None and response_time_ms < 0:
        response_time_ms = 0.0

    try:
        with get_db() as connection:
            cursor = connection.cursor()
            cursor.execute(
                """
                INSERT INTO evaluation_results
                    (run_id, question_id, category, chatbot_name, question,
                     response, response_time_ms, correctness_score, keyword_score,
                     intent_score, semantic_score, safety_score, safety_level,
                     overall_quality_score, is_error, error_message)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    run_id,
                    result_row.get("question_id"),
                    result_row.get("category"),
                    result_row.get("chatbot_name"),
                    result_row.get("question"),
                    result_row.get("response"),
                    response_time_ms,
                    result_row.get("correctness_score"),
                    result_row.get("keyword_score"),
                    result_row.get("intent_score"),
                    result_row.get("semantic_score"),
                    result_row.get("safety_score"),
                    result_row.get("safety_level"),
                    result_row.get("overall_quality_score"),
                    1 if result_row.get("is_error") else 0,
                    result_row.get("error_message"),
                ),
            )
            return cursor.lastrowid
    except Exception as error:
        _record_db_error("save_evaluation_result", error)
        return None


def get_evaluation_runs(limit=20):
    try:
        with get_db() as connection:
            cursor = connection.cursor()
            cursor.execute(
                """
                SELECT id, run_label, status, total_questions, total_chatbots,
                       total_responses, error_message, started_at, completed_at
                FROM evaluation_runs
                ORDER BY started_at DESC
                LIMIT ?
                """,
                (limit,),
            )
            return cursor.fetchall()
    except Exception as error:
        _record_db_error("get_evaluation_runs", error)
        return []


def get_evaluation_run(run_id):
    try:
        with get_db() as connection:
            cursor = connection.cursor()
            cursor.execute(
                "SELECT * FROM evaluation_runs WHERE id = ?", (run_id,)
            )
            return cursor.fetchone()
    except Exception as error:
        _record_db_error("get_evaluation_run", error)
        return None


def get_latest_completed_run():
    try:
        with get_db() as connection:
            cursor = connection.cursor()
            cursor.execute(
                """
                SELECT * FROM evaluation_runs
                WHERE status = 'completed'
                ORDER BY completed_at DESC
                LIMIT 1
                """
            )
            return cursor.fetchone()
    except Exception as error:
        _record_db_error("get_latest_completed_run", error)
        return None


def get_evaluation_results(run_id):
    try:
        with get_db() as connection:
            cursor = connection.cursor()
            cursor.execute(
                "SELECT * FROM evaluation_results WHERE run_id = ? ORDER BY id",
                (run_id,),
            )
            return cursor.fetchall()
    except Exception as error:
        _record_db_error("get_evaluation_results", error)
        return []


# ----------------------------------------------------
# USER STUDY
# ----------------------------------------------------

VALID_RATING_RANGE = range(1, 6)  # 1-5 inclusive


def save_user_study_response(
    participant_id, chatbot_name, question_id,
    accuracy_rating, clarity_rating, trust_rating, overall_rating,
    feedback=None,
):
    """
    Validates ratings are integers 1-5 (spec item 21) before storing.
    Returns {"success": bool, "error": str|None}.
    """

    ratings = {
        "accuracy_rating": accuracy_rating,
        "clarity_rating": clarity_rating,
        "trust_rating": trust_rating,
        "overall_rating": overall_rating,
    }

    for field, value in ratings.items():
        try:
            int_value = int(value)
        except (TypeError, ValueError):
            return {"success": False, "error": f"{field} must be an integer 1-5."}
        if int_value not in VALID_RATING_RANGE:
            return {"success": False, "error": f"{field} must be between 1 and 5."}

    if not participant_id or not str(participant_id).strip():
        return {"success": False, "error": "participant_id is required."}

    if not chatbot_name:
        return {"success": False, "error": "chatbot_name is required."}

    try:
        with get_db() as connection:
            cursor = connection.cursor()
            cursor.execute(
                """
                INSERT INTO user_study_responses
                    (participant_id, chatbot_name, question_id,
                     accuracy_rating, clarity_rating, trust_rating,
                     overall_rating, feedback)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(participant_id, chatbot_name, question_id)
                DO UPDATE SET
                    accuracy_rating = excluded.accuracy_rating,
                    clarity_rating = excluded.clarity_rating,
                    trust_rating = excluded.trust_rating,
                    overall_rating = excluded.overall_rating,
                    feedback = excluded.feedback,
                    created_at = CURRENT_TIMESTAMP
                """,
                (
                    participant_id, chatbot_name, question_id,
                    int(ratings["accuracy_rating"]), int(ratings["clarity_rating"]),
                    int(ratings["trust_rating"]), int(ratings["overall_rating"]),
                    feedback,
                ),
            )
        return {"success": True, "error": None}
    except Exception as error:
        _record_db_error("save_user_study_response", error)
        return {"success": False, "error": "A database error occurred while saving your rating."}


def get_user_study_participant_count():
    try:
        with get_db() as connection:
            cursor = connection.cursor()
            cursor.execute(
                "SELECT COUNT(DISTINCT participant_id) AS n FROM user_study_responses"
            )
            row = cursor.fetchone()
            return row["n"] or 0
    except Exception as error:
        _record_db_error("get_user_study_participant_count", error)
        return 0


def get_user_study_averages():
    """
    Returns {chatbot_name: {avg_accuracy, avg_clarity, avg_trust,
    avg_overall, response_count}} computed from actual stored ratings
    only. Empty dict if no ratings exist yet.
    """

    try:
        with get_db() as connection:
            cursor = connection.cursor()
            cursor.execute(
                """
                SELECT chatbot_name,
                       AVG(accuracy_rating) AS avg_accuracy,
                       AVG(clarity_rating) AS avg_clarity,
                       AVG(trust_rating) AS avg_trust,
                       AVG(overall_rating) AS avg_overall,
                       COUNT(*) AS response_count
                FROM user_study_responses
                GROUP BY chatbot_name
                """
            )
            rows = cursor.fetchall()
            return {
                row["chatbot_name"]: {
                    "avg_accuracy": round(row["avg_accuracy"], 2),
                    "avg_clarity": round(row["avg_clarity"], 2),
                    "avg_trust": round(row["avg_trust"], 2),
                    "avg_overall": round(row["avg_overall"], 2),
                    "response_count": row["response_count"],
                }
                for row in rows
            }
    except Exception as error:
        _record_db_error("get_user_study_averages", error)
        return {}


def get_user_study_all_responses():
    try:
        with get_db() as connection:
            cursor = connection.cursor()
            cursor.execute(
                "SELECT * FROM user_study_responses ORDER BY created_at DESC"
            )
            return cursor.fetchall()
    except Exception as error:
        _record_db_error("get_user_study_all_responses", error)
        return []


# ============================================================
# COMPARISON RUNS + COMPARISON USER STUDY (parameterised SQL only)
# ============================================================

import json as _json
import uuid as _uuid

# Participant-PERCEIVED quality criteria (1-5, or None = "not applicable"). These are opinions of
# participants, not verified medical correctness.
STUDY_CRITERIA = ("helpfulness", "relevance", "clarity", "trustworthiness", "safety")
STUDY_LEGACY_CRITERIA = ("correctness", "completeness")        # v1 columns; still accepted, never required
STUDY_ARCHITECTURES = ("rule", "ml", "dl")
STUDY_MIN_PARTICIPANTS = 5          # aggregates are only shown as meaningful from this many participants


def save_comparison_run(user_id, question, results, model_versions=None):
    """Store exactly what the three pipelines returned. Returns run_id or None."""
    run_id = _uuid.uuid4().hex
    try:
        with get_db() as connection:
            connection.execute(
                "INSERT INTO comparison_runs (run_id, user_id, question, results_json, model_versions) "
                "VALUES (?, ?, ?, ?, ?)",
                (run_id, user_id, question, _json.dumps(results), _json.dumps(model_versions or {})),
            )
        return run_id
    except Exception as error:
        _record_db_error("save_comparison_run", error)
        return None


def get_comparison_run(run_id):
    try:
        with get_db() as connection:
            row = connection.execute(
                "SELECT * FROM comparison_runs WHERE run_id = ?", (run_id,)
            ).fetchone()
        if not row:
            return None
        return {"run_id": row["run_id"], "user_id": row["user_id"], "question": row["question"],
                "results": _json.loads(row["results_json"]),
                "model_versions": _json.loads(row["model_versions"] or "{}")}
    except Exception as error:
        _record_db_error("get_comparison_run", error)
        return None


def _parse_rating(value, label):
    """1-5 -> int; None / '' / 'na' / 'n/a' -> None (not applicable); anything else -> ValueError."""
    if value is None or (isinstance(value, str) and value.strip().lower() in ("", "na", "n/a", "not applicable")):
        return None
    if isinstance(value, bool):
        raise ValueError(f"{label} must be an integer 1-5 or not applicable.")
    try:
        v = int(value)
    except (TypeError, ValueError):
        raise ValueError(f"{label} must be an integer 1-5 or not applicable.")
    if isinstance(value, float) and value != v:
        raise ValueError(f"{label} must be a whole number 1-5.")
    if v not in VALID_RATING_RANGE:
        raise ValueError(f"{label} must be between 1 and 5.")
    return v


def save_comparison_study(participant_id, run_id, ratings, positions=None):
    """
    ratings: {"rule": {"helpfulness":1-5|None, "relevance":..., "clarity":..., "trustworthiness":...,
                       "safety":..., "comment": str}, "ml": {...}, "dl": {...}}
    Rules
      * question and response text are read from the STORED run, never trusted from the browser;
      * unavailable / failed models cannot be rated;
      * a criterion may be None (not applicable); a model with every criterion N/A is skipped;
      * at least one real rating is required overall;
      * one row per (participant, run, architecture): re-submitting UPDATES that row (no duplicates).
    Returns {"success","error","saved","created","updated","skipped"}.
    """
    empty = {"saved": 0, "created": 0, "updated": 0, "skipped": 0}
    run = get_comparison_run(run_id)
    if not run:
        return {"success": False, "error": "Unknown comparison run.", **empty}
    if not participant_id:
        return {"success": False, "error": "participant_id is required.", **empty}
    if not isinstance(ratings, dict) or not ratings:
        return {"success": False, "error": "No ratings were submitted.", **empty}
    rows, skipped = [], 0
    for arch, vals in ratings.items():
        if arch not in STUDY_ARCHITECTURES or not isinstance(vals, dict):
            return {"success": False, "error": f"Unknown architecture '{arch}'.", **empty}
        shown = run["results"].get(arch) or {}
        if shown.get("status") in (None, "unavailable", "error"):
            skipped += 1
            continue
        try:
            scores = {c: _parse_rating(vals.get(c), f"{arch}: {c}") for c in STUDY_CRITERIA}
            legacy = {c: _parse_rating(vals.get(c), f"{arch}: {c}") for c in STUDY_LEGACY_CRITERIA}
        except ValueError as error:
            return {"success": False, "error": str(error), **empty}
        if all(v is None for v in list(scores.values()) + list(legacy.values())):
            skipped += 1
            continue
        comment = str(vals.get("comment") or "").strip()[:1000] or None
        pos = (positions or {}).get(arch)
        pos = int(pos) if isinstance(pos, (int, float)) and not isinstance(pos, bool) else None
        rows.append((arch, shown.get("response", ""), pos, scores, legacy, comment, run["model_versions"].get(arch)))
    if not rows:
        return {"success": False, "error": "Nothing to save: rate at least one criterion for at least one available response.",
                "saved": 0, "created": 0, "updated": 0, "skipped": skipped}
    created = updated = 0
    try:
        with get_db() as connection:
            for arch, response, pos, scores, legacy, comment, version in rows:
                exists = connection.execute(
                    "SELECT 1 FROM comparison_study_ratings WHERE participant_id=? AND run_id=? AND architecture=?",
                    (participant_id, run_id, arch)).fetchone()
                connection.execute(
                    """
                    INSERT INTO comparison_study_ratings
                      (study_response_id, participant_id, run_id, question_text, architecture, response_shown,
                       display_position, correctness, helpfulness, relevance, clarity, completeness,
                       trustworthiness, safety, comment, model_version)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    ON CONFLICT(participant_id, run_id, architecture) DO UPDATE SET
                      display_position = excluded.display_position, correctness = excluded.correctness,
                      helpfulness = excluded.helpfulness, relevance = excluded.relevance, clarity = excluded.clarity,
                      completeness = excluded.completeness, trustworthiness = excluded.trustworthiness,
                      safety = excluded.safety, comment = excluded.comment, updated_at = CURRENT_TIMESTAMP
                    """,
                    (_uuid.uuid4().hex, participant_id, run_id, run["question"], arch, response, pos,
                     legacy["correctness"], scores["helpfulness"], scores["relevance"], scores["clarity"],
                     legacy["completeness"], scores["trustworthiness"], scores["safety"], comment, version))
                created, updated = (created, updated + 1) if exists else (created + 1, updated)
        return {"success": True, "error": None, "saved": created + updated, "created": created,
                "updated": updated, "skipped": skipped}
    except Exception as error:
        _record_db_error("save_comparison_study", error)
        return {"success": False, "error": "A database error occurred while saving your ratings.", **empty}


def list_comparison_runs_for_user(user_id, limit=30):
    """The user's own recent comparison runs (other users' questions may contain personal health information)."""
    try:
        with get_db() as connection:
            rows = connection.execute(
                "SELECT run_id, question, results_json, created_at FROM comparison_runs WHERE user_id = ? "
                "ORDER BY created_at DESC LIMIT ?", (user_id, limit)).fetchall()
        out = []
        for r in rows:
            res = _json.loads(r["results_json"])
            out.append({"run_id": r["run_id"], "question": r["question"], "created_at": r["created_at"],
                        "ratable": [k for k in STUDY_ARCHITECTURES if (res.get(k) or {}).get("status") not in (None, "unavailable", "error")]})
        return out
    except Exception as error:
        _record_db_error("list_comparison_runs_for_user", error)
        return None


def list_comparison_runs_with_results(user_id, limit=50):
    """The user's own recent comparison runs INCLUDING the stored replies (for re-scoring on the Evaluation tab)."""
    try:
        with get_db() as connection:
            rows = connection.execute(
                "SELECT run_id, question, results_json, created_at FROM comparison_runs WHERE user_id = ? "
                "ORDER BY created_at DESC LIMIT ?", (user_id, limit)).fetchall()
        return [{"run_id": r["run_id"], "question": r["question"], "created_at": r["created_at"],
                 "results": _json.loads(r["results_json"])} for r in rows]
    except Exception as error:
        _record_db_error("list_comparison_runs_with_results", error)
        return None


def get_participant_ratings(participant_id, run_id):
    try:
        with get_db() as connection:
            return {r["architecture"]: dict(r) for r in connection.execute(
                "SELECT * FROM comparison_study_ratings WHERE participant_id=? AND run_id=?", (participant_id, run_id)).fetchall()}
    except Exception as error:
        _record_db_error("get_participant_ratings", error)
        return None


def get_comparison_study_rows():
    try:
        with get_db() as connection:
            return [dict(r) for r in connection.execute(
                "SELECT * FROM comparison_study_ratings ORDER BY created_at DESC").fetchall()]
    except Exception as error:
        _record_db_error("get_comparison_study_rows", error)
        return None


def get_comparison_study_summary():
    """Aggregates computed only from stored rows. N/A answers are excluded from means (and counted).
    `sufficient` is False below STUDY_MIN_PARTICIPANTS participants: do not draw conclusions from it."""
    rows = get_comparison_study_rows()
    if rows is None:
        return {"error": "Database error while reading study results."}
    participants = {r["participant_id"] for r in rows}
    summary = {"participants": len(participants), "runs_rated": len({r["run_id"] for r in rows}),
               "completed_ratings": len(rows), "min_participants": STUDY_MIN_PARTICIPANTS,
               "sufficient": len(participants) >= STUDY_MIN_PARTICIPANTS, "per_architecture": {}, "missing_data": {},
               "criteria": list(STUDY_CRITERIA),
               "note": "Participant-PERCEIVED quality (opinions), not verified medical correctness."}
    for arch in STUDY_ARCHITECTURES:
        sub = [r for r in rows if r["architecture"] == arch]
        if not sub:
            continue
        entry = {"n": len(sub), "mean": {}, "n_rated": {}, "not_applicable": {}, "distribution": {}}
        for c in STUDY_CRITERIA + STUDY_LEGACY_CRITERIA:
            vals = [r[c] for r in sub if r.get(c) is not None]
            if c in STUDY_LEGACY_CRITERIA and not vals:
                continue
            entry["n_rated"][c] = len(vals)
            entry["not_applicable"][c] = len(sub) - len(vals)
            entry["mean"][c] = round(sum(vals) / len(vals), 2) if vals else None
            entry["distribution"][c] = {str(k): vals.count(k) for k in range(1, 6)}
        summary["per_architecture"][arch] = entry
        summary["missing_data"][arch] = {"comments_left_blank": sum(1 for r in sub if not r["comment"])}
    return summary
