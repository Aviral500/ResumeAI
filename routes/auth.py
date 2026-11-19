from datetime import datetime
from flask import Blueprint, render_template, request, redirect, url_for, session, flash
from werkzeug.security import generate_password_hash, check_password_hash
from models.db import get_db

auth_bp = Blueprint("auth", __name__, url_prefix="/auth")


@auth_bp.route("/register", methods=["GET", "POST"])
def register():
    if session.get("user_id"):
        return redirect(url_for("candidate.dashboard"))
    if request.method == "POST":
        name = request.form.get("name", "").strip()
        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")
        confirm = request.form.get("confirm_password", "")
        if not name or not email or not password:
            flash("All fields are required.", "error")
        elif password != confirm:
            flash("Passwords do not match.", "error")
        elif len(password) < 6:
            flash("Password must contain at least 6 characters.", "error")
        else:
            db = get_db()
            exists = db.execute("SELECT id FROM users WHERE email=?", (email,)).fetchone()
            if exists:
                db.close()
                flash("Account already exists.", "error")
            else:
                db.execute(
                    "INSERT INTO users(name,email,password_hash,role,created_at) VALUES(?,?,?,?,?)",
                    (name, email, generate_password_hash(password), "candidate", datetime.now().isoformat(timespec="seconds")),
                )
                db.commit()
                db.close()
                flash("Candidate registration successful. Please log in.", "success")
                return redirect(url_for("auth.login"))
        return redirect(url_for("auth.register"))
    return render_template("auth/register.html")


@auth_bp.route("/login", methods=["GET", "POST"])
def login():
    if session.get("user_id"):
        return redirect(url_for("candidate.dashboard" if session.get("role") == "candidate" else "admin.dashboard"))
    if request.method == "POST":
        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")
        db = get_db()
        u = db.execute("SELECT * FROM users WHERE email=?", (email,)).fetchone()
        db.close()
        if not u or not check_password_hash(u["password_hash"], password):
            flash("Invalid candidate email or password.", "error")
            return redirect(url_for("auth.login"))
        if u["role"] != "candidate":
            flash("This is an admin account. Please use Admin Login.", "error")
            return redirect(url_for("admin.admin_login"))
        session.clear()
        session["user_id"] = u["id"]
        session["name"] = u["name"]
        session["role"] = u["role"]
        return redirect(url_for("candidate.dashboard"))
    return render_template("auth/login.html")


@auth_bp.route("/logout")
def logout():
    session.clear()
    flash("Logged out successfully.", "success")
    return redirect(url_for("home"))
