"""extensions.py - Flask extensions created once and initialised in app.create_app()."""
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address

limiter = Limiter(key_func=get_remote_address, default_limits=[])
