"""
migrations.py - versioned, additive schema migrations on top of database.create_database().

Each migration runs once and is recorded in schema_migrations. Migrations only ADD columns, tables
and indexes; nothing is dropped or rewritten, so an existing healthbot.db keeps all its data.
They run inside one transaction per migration (rolled back on error).

Why not Flask-Migrate/SQLAlchemy? The project already has a working sqlite3 data layer
(database.py, ~2,000 lines, used by the tests and the legacy UI). Re-implementing it on an ORM
would risk breaking working code for no functional gain; this runner gives the same guarantees
(ordered, recorded, non-destructive, automatic at startup).
"""
from database.database import get_db, create_database


def _cols(cur, table):
    return {r[1] for r in cur.execute(f"PRAGMA table_info({table})").fetchall()}


def _add(cur, table, column, decl):
    if column not in _cols(cur, table):
        cur.execute(f"ALTER TABLE {table} ADD COLUMN {column} {decl}")


def m001_message_and_profile_fields(cur):
    _add(cur, "users", "updated_at", "TIMESTAMP")
    _add(cur, "health_profiles", "consent_at", "TIMESTAMP")
    _add(cur, "health_profiles", "age_range", "TEXT")
    _add(cur, "chats", "safety_status", "TEXT")
    _add(cur, "chats", "mode", "TEXT")                 # 'symptom' | 'health_qa'
    _add(cur, "chats", "handled_by", "TEXT")           # which layer answered (model / small talk / safety ...)
    _add(cur, "conversations", "architecture", "TEXT")
    _add(cur, "conversations", "mode", "TEXT")


def m002_experiments(cur):
    cur.execute("""
        CREATE TABLE IF NOT EXISTS experiments (
            id TEXT PRIMARY KEY,                       -- run id, also the JSON file name
            name TEXT NOT NULL,
            suite TEXT NOT NULL,                       -- 'symptom' | 'health_qa'
            dataset_name TEXT NOT NULL,
            dataset_version TEXT,
            split TEXT,
            sample_size INTEGER,
            random_seed INTEGER,
            evaluation_method TEXT,
            in_sample INTEGER NOT NULL DEFAULT 0,
            status TEXT NOT NULL,
            user_id INTEGER,
            warnings_json TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            finished_at TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE SET NULL
        )""")
    cur.execute("""
        CREATE TABLE IF NOT EXISTS performance_results (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            experiment_id TEXT NOT NULL,
            architecture TEXT NOT NULL,
            accuracy REAL,
            precision REAL,
            recall REAL,
            f1_score REAL,
            legacy_mention_accuracy REAL,
            coverage REAL,
            safety_pass_rate REAL,
            mean_response_time REAL,                   -- milliseconds
            median_response_time REAL,                 -- milliseconds
            cpu_usage REAL,                            -- percent of one core
            memory_usage REAL,                         -- MB change in process RSS
            successful_requests INTEGER,
            failed_requests INTEGER,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            UNIQUE(experiment_id, architecture),
            FOREIGN KEY (experiment_id) REFERENCES experiments(id) ON DELETE CASCADE
        )""")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_experiments_created ON experiments(created_at)")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_perf_experiment ON performance_results(experiment_id)")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_chats_user_created ON chats(user_id, created_at)")


def m003_conversation_context(cur):
    _add(cur, "conversations", "context_json", "TEXT")   # ConversationManager state (pending question, duration, topic)


def m004_three_chatbots_only(cur):
    """Scope fixed to the three MediChat chatbots (rule, ml, dl). Rows for the removed six-architecture
    suite and the LogReg/MLP bots are dropped here; their full run files are kept under archive/."""
    cur.execute("DELETE FROM performance_results WHERE experiment_id IN (SELECT id FROM experiments WHERE suite = 'symptom')")
    cur.execute("DELETE FROM experiments WHERE suite = 'symptom'")
    cur.execute("UPDATE performance_results SET architecture = substr(architecture, 5) WHERE architecture LIKE 'hqa:%'")
    cur.execute("DELETE FROM performance_results WHERE architecture NOT IN ('rule', 'ml', 'dl')")
    cur.execute("DELETE FROM comparison_study_ratings WHERE architecture NOT IN ('rule', 'ml', 'dl')")


MIGRATIONS = [("001_message_and_profile_fields", m001_message_and_profile_fields),
              ("002_experiments", m002_experiments),
              ("003_conversation_context", m003_conversation_context),
              ("004_three_chatbots_only", m004_three_chatbots_only)]


def migrate():
    """Create the base schema, then apply pending migrations in order. Returns the names applied."""
    create_database()
    applied = []
    with get_db() as conn:
        conn.execute("CREATE TABLE IF NOT EXISTS schema_migrations (name TEXT PRIMARY KEY, applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP)")
        done = {r[0] for r in conn.execute("SELECT name FROM schema_migrations").fetchall()}
    for name, fn in MIGRATIONS:
        if name in done:
            continue
        with get_db() as conn:
            cur = conn.cursor()
            fn(cur)
            cur.execute("INSERT INTO schema_migrations (name) VALUES (?)", (name,))
        applied.append(name)
    return applied


def status():
    with get_db() as conn:
        rows = conn.execute("SELECT name, applied_at FROM schema_migrations ORDER BY name").fetchall()
    done = {r["name"]: r["applied_at"] for r in rows}
    return [{"name": n, "applied": n in done, "applied_at": done.get(n)} for n, _ in MIGRATIONS]
