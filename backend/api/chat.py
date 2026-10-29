"""Chat with one of the three MediChat chatbots + chat history."""
from flask import Blueprint, request

from api.common import ApiError, body, current_user_id, int_arg, login_required, ok, page_meta, text_field
from chatbot.orchestrator.conversation_manager import BOTS, MAX_CHARS, ConversationManager
from database import repository as repo

bp = Blueprint("chat", __name__)

EXAMPLES = ["I have a fever and headache. What should I do?",
            "Which doctor should I consult for frequent headaches?",
            "Can I take two different medicines together?",
            "What is a balanced diet?"]


def bot_list():
    import comparison_service as cs
    out = []
    for k in BOTS:
        try:
            info = cs.get_pipeline(k).info()
        except Exception as exc:
            info = {"available": False, "error": f"{type(exc).__name__}: {exc}"}
        out.append({"key": k, "name": cs.BOT_NAMES[k], "architecture": info.get("architecture"),
                    "available": bool(info.get("available")), "error": info.get("error"), "version": info.get("version")})
    return out


@bp.get("/chat/options")
def options():
    return ok({"bots": bot_list(), "examples": EXAMPLES,
               "notice": "MediChat provides general health information. It cannot diagnose conditions or replace a doctor."})


@bp.post("/chat")
def chat():
    d = body()
    message = text_field(d, "message", max_len=MAX_CHARS)
    bot = d.get("bot") or "rule"
    uid = current_user_id()
    conv_id = d.get("conversation_id")
    save = bool(d.get("save", True)) and uid is not None
    state = d.get("state") if isinstance(d.get("state"), dict) else None

    conv = None
    if conv_id is not None:
        if uid is None:
            raise ApiError("AUTH_REQUIRED", "Sign in to continue a saved conversation.", 401)
        try:
            conv = repo.get_conversation(int(conv_id), uid)
        except (TypeError, ValueError):
            conv = None
        if not conv:
            raise ApiError("NOT_FOUND", "Conversation not found.", 404)
        state = repo.get_context(conv)
    try:
        out = ConversationManager(bot, state).process(message)
    except ValueError as exc:
        raise ApiError("VALIDATION_ERROR", str(exc))

    if save:
        if conv is None:
            conv_id = repo.create_conversation(uid, message[:60], "health_qa", bot)
        repo.save_turn(uid, int(conv_id), message, out["reply"], bot, "health_qa", out["response_time_ms"],
                       out["safety_status"], out["handled_by"], out["state"])
    r = out.get("result") or {}
    return ok({"conversation_id": int(conv_id) if save else None, "saved": save, "reply": out["reply"],
               "handled_by": out["handled_by"], "bot": bot, "safety_status": out["safety_status"],
               "response_time_ms": out["response_time_ms"], "language": out["language"],
               "state": None if save else out["state"],
               "details": {"status": r.get("status"), "intent": r.get("intent"), "confidence": r.get("confidence"),
                           "confidence_kind": r.get("confidence_kind"), "inference_ms": r.get("inference_ms")}})


@bp.get("/chats")
@login_required
def list_chats():
    page, per = int_arg("page", 1, 1, 10000), int_arg("per_page", 20, 1, 100)
    q = (request.args.get("q") or "").strip()[:100] or None
    rows, total = repo.list_conversations(current_user_id(), page, per, q)
    return ok(rows, meta=page_meta(page, per, total))


@bp.get("/chats/<int:conv_id>")
@login_required
def get_chat(conv_id):
    detail = repo.conversation_detail(conv_id, current_user_id())
    if not detail:
        raise ApiError("NOT_FOUND", "Conversation not found.", 404)
    return ok(detail)


@bp.patch("/chats/<int:conv_id>")
@login_required
def patch_chat(conv_id):
    if not repo.get_conversation(conv_id, current_user_id()):
        raise ApiError("NOT_FOUND", "Conversation not found.", 404)
    d = body()
    title = text_field(d, "title", required=False, max_len=80)
    pinned = d.get("pinned") if isinstance(d.get("pinned"), bool) else None
    repo.update_conversation(conv_id, current_user_id(), title, pinned)
    return ok(repo.conversation_detail(conv_id, current_user_id()))


@bp.delete("/chats/<int:conv_id>")
@login_required
def delete_chat(conv_id):
    if not repo.delete_conversation(conv_id, current_user_id()):
        raise ApiError("NOT_FOUND", "Conversation not found.", 404)
    return ok({"deleted": True})


@bp.post("/chats/<int:conv_id>/share")
@login_required
def share_chat(conv_id):
    token = repo.share(conv_id, current_user_id(), True)
    if not token:
        raise ApiError("NOT_FOUND", "Conversation not found.", 404)
    return ok({"share_token": token, "path": f"/shared/{token}"})


@bp.delete("/chats/<int:conv_id>/share")
@login_required
def unshare_chat(conv_id):
    if not repo.share(conv_id, current_user_id(), False):
        raise ApiError("NOT_FOUND", "Conversation not found.", 404)
    return ok({"shared": False})


@bp.get("/shared/<token>")
def shared(token):
    if not token.replace("-", "").replace("_", "").isalnum() or len(token) > 64:
        raise ApiError("NOT_FOUND", "This shared conversation does not exist or is no longer shared.", 404)
    conv = repo.shared_conversation(token)
    if not conv:
        raise ApiError("NOT_FOUND", "This shared conversation does not exist or is no longer shared.", 404)
    return ok(conv)
