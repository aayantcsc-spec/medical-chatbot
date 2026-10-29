"""Health profile: optional, minimal fields only. Never used to infer a diagnosis."""
from flask import Blueprint

from api.common import ApiError, body, current_user_id, login_required, ok
from database import repository as repo

bp = Blueprint("profile", __name__, url_prefix="/profile")

CHOICES = {
    "age_range": {"under 18", "18-29", "30-44", "45-59", "60-74", "75+", "prefer not to say"},
    "smoking": {"never", "former", "current", "prefer not to say"},
    "activity_level": {"low", "moderate", "high", "prefer not to say"},
}
FREE_TEXT = {"height": 20, "weight": 20, "health_goal": 120}
PURPOSE = ("Profile fields are optional. They are stored only to show on your profile page and are never used to "
           "diagnose, recommend treatment, or choose a chatbot's answer.")


@bp.get("")
@login_required
def get_profile():
    return ok({"profile": repo.get_profile(current_user_id()), "choices": {k: sorted(v) for k, v in CHOICES.items()},
               "purpose": PURPOSE})


@bp.put("")
@login_required
def put_profile():
    d = body()
    fields = {}
    for k, allowed in CHOICES.items():
        v = d.get(k)
        if v not in (None, ""):
            if v not in allowed:
                raise ApiError("VALIDATION_ERROR", f"'{k}' must be one of: {', '.join(sorted(allowed))}.", extra={"field": k})
            fields[k] = v
    for k, n in FREE_TEXT.items():
        v = d.get(k)
        if v not in (None, ""):
            if not isinstance(v, str) or len(v.strip()) > n:
                raise ApiError("VALIDATION_ERROR", f"'{k}' must be text of at most {n} characters.", extra={"field": k})
            fields[k] = v.strip()
    consent = d.get("acknowledged") is True
    existing = repo.get_profile(current_user_id())
    if not consent and not (existing and existing.get("consent_at")):
        raise ApiError("ACKNOWLEDGEMENT_REQUIRED",
                       "Please confirm you understand HealthBot is for research and education, not medical care.",
                       extra={"field": "acknowledged"})
    profile = repo.save_profile(current_user_id(), fields, consent=consent, clear_legacy=d.get("clear_legacy_fields") is True)
    return ok({"profile": profile})


@bp.delete("")
@login_required
def delete_profile():
    return ok({"deleted": repo.delete_profile(current_user_id())})
