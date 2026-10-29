import os, sys, tempfile, json
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
os.environ["TRANSFORMERS_VERBOSITY"] = "error"
from database import database as db
db.DATABASE_PATH = os.path.join(tempfile.mkdtemp(), "ui.db")
import evaluation_service as E
E.RUN_DIR = tempfile.mkdtemp()
import legacy_app as A
db.create_database()
db.create_user("Ui", "Tester", "ui@example.com", "Passw0rd!x")
uid = db.get_user_by_email("ui@example.com")["id"]
db.save_user_profile(uid, 30, "female", "none", "none", "none", "ui test")
ser = A.app.session_interface.get_signing_serializer(A.app)
open(os.path.join(os.path.dirname(os.path.abspath(__file__)), "cookie.txt"), "w").write(ser.dumps({"user_id": uid, "user_name": "Ui", "user_email": "ui@example.com"}))
print("ready", flush=True)
A.app.run(port=5057, use_reloader=False, threaded=True)
