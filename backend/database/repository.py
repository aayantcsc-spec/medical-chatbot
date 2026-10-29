"""
repository.py - data access for the /api/v1 layer.

Every query that touches user-owned data is scoped by user_id in SQL, so a guessed id can never
read or change another user's records. Reuses database.py for users/profiles where it already
does the job; adds what the v1 API needs (pagination, message-level fields, hard deletes,
account deletion).

Retention policy (also stated in docs/medical-safety.md):
  * deleting a conversation removes it and its messages permanently;
  * deleting the health profile removes the profile row;
  * deleting the account removes the user, profile, conversations, messages and the user's saved
    comparison runs; evaluation experiments they started are kept but de-linked (user_id = NULL)
    because they contain no personal data and other users' dashboards may reference them;
  * pseudonymous user-study ratings are deleted with the account.
"""
import json

from database import database as db
from database.database import get_db

PROFILE_FIELDS = ("age_range", "height", "weight", "smoking", "activity_level", "health_goal")
LEGACY_PROFILE_FIELDS = ("age", "sex", "allergies", "medical_conditions", "medications", "health_notes", "health_concern")


def _row(r):
    return dict(r) if r is not None else None


# ------------------------------------------------------------------------ users
def get_user(user_id):
    with get_db() as c:
        return _row(c.execute("SELECT id, first_name, last_name, email, created_at, updated_at FROM users WHERE id = ?",
                              (user_id,)).fetchone())


def public_user(u):
    if not u:
        return None
    name = " ".join(p for p in (u.get("first_name"), u.get("last_name")) if p).strip()
    return {"id": u["id"], "name": name, "email": u["email"], "created_at": u.get("created_at")}


def rename_user(user_id, name):
    with get_db() as c:
        c.execute("UPDATE users SET first_name = ?, last_name = '', updated_at = CURRENT_TIMESTAMP WHERE id = ?", (name, user_id))


def delete_account(user_id):
    with get_db() as c:
        conv_ids = [r[0] for r in c.execute("SELECT id FROM conversations WHERE user_id = ?", (user_id,)).fetchall()]
        if conv_ids:
            c.execute(f"DELETE FROM chats WHERE conversation_id IN ({','.join('?' * len(conv_ids))})", conv_ids)
        c.execute("DELETE FROM chats WHERE user_id = ?", (user_id,))
        c.execute("DELETE FROM conversations WHERE user_id = ?", (user_id,))
        c.execute("DELETE FROM health_profiles WHERE user_id = ?", (user_id,))
        run_ids = [r[0] for r in c.execute("SELECT run_id FROM comparison_runs WHERE user_id = ?", (user_id,)).fetchall()]
        if run_ids:
            c.execute(f"DELETE FROM comparison_study_ratings WHERE run_id IN ({','.join('?' * len(run_ids))})", run_ids)
        c.execute("DELETE FROM comparison_runs WHERE user_id = ?", (user_id,))
        c.execute("UPDATE experiments SET user_id = NULL WHERE user_id = ?", (user_id,))
        c.execute("DELETE FROM users WHERE id = ?", (user_id,))


# ---------------------------------------------------------------------- profile
def get_profile(user_id):
    with get_db() as c:
        r = _row(c.execute("SELECT * FROM health_profiles WHERE user_id = ?", (user_id,)).fetchone())
    if not r:
        return None
    out = {k: r.get(k) for k in PROFILE_FIELDS}
    out["consent_at"] = r.get("consent_at")
    out["updated_at"] = r.get("updated_at")
    out["legacy_fields"] = {k: r.get(k) for k in LEGACY_PROFILE_FIELDS if r.get(k)}
    return out


def save_profile(user_id, fields, consent=False, clear_legacy=False):
    vals = {k: (str(fields[k]).strip()[:80] or None) if fields.get(k) not in (None, "") else None for k in PROFILE_FIELDS}
    with get_db() as c:
        exists = c.execute("SELECT 1 FROM health_profiles WHERE user_id = ?", (user_id,)).fetchone()
        if not exists:
            c.execute("INSERT INTO health_profiles (user_id) VALUES (?)", (user_id,))
        sets = ", ".join(f"{k} = ?" for k in PROFILE_FIELDS)
        c.execute(f"UPDATE health_profiles SET {sets}, updated_at = CURRENT_TIMESTAMP WHERE user_id = ?",
                  [vals[k] for k in PROFILE_FIELDS] + [user_id])
        if consent:
            c.execute("UPDATE health_profiles SET consent_at = COALESCE(consent_at, CURRENT_TIMESTAMP) WHERE user_id = ?", (user_id,))
        if clear_legacy:
            c.execute(f"UPDATE health_profiles SET {', '.join(f'{k} = NULL' for k in LEGACY_PROFILE_FIELDS)} WHERE user_id = ?", (user_id,))
    return get_profile(user_id)


def delete_profile(user_id):
    with get_db() as c:
        return c.execute("DELETE FROM health_profiles WHERE user_id = ?", (user_id,)).rowcount > 0


# ---------------------------------------------------------------- conversations
def _conv(r):
    d = dict(r)
    d["pinned"] = bool(d.get("pinned"))
    d["shared"] = bool(d.pop("share_token", None))
    d.pop("context_json", None)
    d.pop("deleted", None)
    d.pop("archived", None)
    return d


def create_conversation(user_id, title, mode, architecture):
    with get_db() as c:
        cur = c.execute("INSERT INTO conversations (user_id, title, mode, architecture) VALUES (?, ?, ?, ?)",
                        (user_id, title[:80] or "New conversation", mode, architecture))
        return cur.lastrowid


def get_conversation(conv_id, user_id):
    with get_db() as c:
        return _row(c.execute("SELECT * FROM conversations WHERE id = ? AND user_id = ? AND deleted = 0",
                              (conv_id, user_id)).fetchone())


def get_context(conv):
    try:
        return json.loads(conv.get("context_json") or "{}")
    except (TypeError, ValueError):
        return {}


def save_turn(user_id, conv_id, user_message, reply, bot, mode, response_ms, safety_status, handled_by, state):
    with get_db() as c:
        c.execute("""INSERT INTO chats (user_id, conversation_id, user_message, bot_response, chatbot_type, response_time,
                                        safety_status, mode, handled_by) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                  (user_id, conv_id, user_message, reply, bot, (response_ms or 0) / 1000.0, safety_status, mode, handled_by))
        c.execute("""UPDATE conversations SET updated_at = CURRENT_TIMESTAMP, architecture = ?, mode = ?, context_json = ?
                     WHERE id = ? AND user_id = ?""", (bot, mode, json.dumps(state), conv_id, user_id))


def list_conversations(user_id, page=1, per_page=20, q=None, mode=None):
    where, args = ["c.user_id = ?", "c.deleted = 0"], [user_id]
    if mode:
        where.append("c.mode = ?")
        args.append(mode)
    if q:
        where.append("(c.title LIKE ? OR EXISTS (SELECT 1 FROM chats m WHERE m.conversation_id = c.id "
                     "AND (m.user_message LIKE ? OR m.bot_response LIKE ?)))")
        like = f"%{q}%"
        args += [like, like, like]
    w = " AND ".join(where)
    with get_db() as c:
        total = c.execute(f"SELECT COUNT(*) FROM conversations c WHERE {w}", args).fetchone()[0]
        rows = c.execute(f"""
            SELECT c.*, (SELECT COUNT(*) FROM chats m WHERE m.conversation_id = c.id) AS message_count,
                   (SELECT m.user_message FROM chats m WHERE m.conversation_id = c.id ORDER BY m.id DESC LIMIT 1) AS last_message
            FROM conversations c WHERE {w} ORDER BY c.pinned DESC, c.updated_at DESC LIMIT ? OFFSET ?""",
                         args + [int(per_page), (int(page) - 1) * int(per_page)]).fetchall()
    return [_conv(r) for r in rows], total


def conversation_detail(conv_id, user_id):
    conv = get_conversation(conv_id, user_id)
    if not conv:
        return None
    with get_db() as c:
        msgs = c.execute("SELECT * FROM chats WHERE conversation_id = ? ORDER BY id", (conv_id,)).fetchall()
    messages = []
    for m in msgs:
        messages.append({"id": f"{m['id']}u", "role": "user", "content": m["user_message"], "created_at": m["created_at"]})
        messages.append({"id": f"{m['id']}a", "role": "assistant", "content": m["bot_response"], "created_at": m["created_at"],
                         "architecture": m["chatbot_type"], "mode": m["mode"], "handled_by": m["handled_by"],
                         "safety_status": m["safety_status"],
                         "response_time_ms": round(m["response_time"] * 1000, 1) if m["response_time"] is not None else None})
    return {**_conv(conv), "messages": messages, "share_token": conv.get("share_token")}


def update_conversation(conv_id, user_id, title=None, pinned=None):
    with get_db() as c:
        if title is not None:
            c.execute("UPDATE conversations SET title = ? WHERE id = ? AND user_id = ?", (title[:80], conv_id, user_id))
        if pinned is not None:
            c.execute("UPDATE conversations SET pinned = ? WHERE id = ? AND user_id = ?", (1 if pinned else 0, conv_id, user_id))


def delete_conversation(conv_id, user_id):
    with get_db() as c:
        if not c.execute("SELECT 1 FROM conversations WHERE id = ? AND user_id = ?", (conv_id, user_id)).fetchone():
            return False
        c.execute("DELETE FROM chats WHERE conversation_id = ?", (conv_id,))
        c.execute("DELETE FROM conversations WHERE id = ? AND user_id = ?", (conv_id, user_id))
        return True


def share(conv_id, user_id, enable=True):
    return db.generate_share_token(conv_id, user_id) if enable else db.revoke_share_token(conv_id, user_id)


def shared_conversation(token):
    conv, msgs = db.get_conversation_by_share_token(token)
    if not conv:
        return None
    return {"title": conv["title"], "created_at": conv["created_at"],
            "messages": [{"role": r, "content": m["user_message"] if r == "user" else m["bot_response"]}
                         for m in msgs for r in ("user", "assistant")]}


# ---------------------------------------------------------------- dashboard
def user_activity(user_id):
    with get_db() as c:
        conv = c.execute("SELECT COUNT(*) FROM conversations WHERE user_id = ? AND deleted = 0", (user_id,)).fetchone()[0]
        msgs = c.execute("SELECT COUNT(*) FROM chats WHERE user_id = ?", (user_id,)).fetchone()[0]
        last = _row(c.execute("SELECT chatbot_type, mode, created_at FROM chats WHERE user_id = ? ORDER BY id DESC LIMIT 1",
                              (user_id,)).fetchone())
        comps = c.execute("SELECT COUNT(*) FROM comparison_runs WHERE user_id = ?", (user_id,)).fetchone()[0]
        by_bot = [dict(r) for r in c.execute("""SELECT chatbot_type AS bot, COUNT(*) AS messages, AVG(response_time) * 1000 AS mean_ms
                                                FROM chats WHERE user_id = ? AND chatbot_type IS NOT NULL
                                                GROUP BY chatbot_type ORDER BY messages DESC""", (user_id,)).fetchall()]
    recent, _ = list_conversations(user_id, 1, 5)
    return {"conversations": conv, "messages": msgs, "last_used": last, "comparisons": comps,
            "messages_by_bot": by_bot, "recent_conversations": recent}
