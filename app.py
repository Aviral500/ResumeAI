from flask import Flask, redirect, url_for, session, render_template
from models.db import init_db
from routes.auth import auth_bp
from routes.admin import admin_bp
from routes.candidate import candidate_bp

app = Flask(__name__)
app.config["SECRET_KEY"] = "change-this-secret-key"
app.config["UPLOAD_FOLDER"] = "uploads"
app.config["MAX_CONTENT_LENGTH"] = 8 * 1024 * 1024
init_db()
app.register_blueprint(auth_bp)
app.register_blueprint(admin_bp)
app.register_blueprint(candidate_bp)


@app.template_filter("fromjson")
def fromjson_filter(value):
    import json
    try:
        return json.loads(value or "[]")
    except Exception:
        return []


@app.route("/")
def home():
    if session.get("user_id"):
        return redirect(url_for("admin.dashboard" if session.get("role") == "admin" else "candidate.dashboard"))
    return render_template("home.html")


if __name__ == "__main__":
    app.run(debug=True)
