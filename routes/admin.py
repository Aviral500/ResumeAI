from datetime import datetime
from functools import wraps
from flask import Blueprint, render_template, request, redirect, url_for, session, flash
from werkzeug.security import generate_password_hash, check_password_hash
from models.db import get_db

admin_bp = Blueprint("admin", __name__, url_prefix="/admin")


def admin_required(f):
    @wraps(f)
    def w(*a, **k):
        if session.get("role") != "admin":
            flash("Admin access required.", "error")
            return redirect(url_for("admin.admin_login"))
        return f(*a, **k)
    return w


@admin_bp.route("/login", methods=["GET", "POST"])
def admin_login():
    if session.get("user_id"):
        return redirect(url_for("admin.dashboard" if session.get("role") == "admin" else "candidate.dashboard"))
    if request.method == "POST":
        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")
        db = get_db()
        u = db.execute("SELECT * FROM users WHERE email=?", (email,)).fetchone()
        db.close()
        if not u or u["role"] != "admin" or not check_password_hash(u["password_hash"], password):
            flash("Invalid admin email or password.", "error")
            return redirect(url_for("admin.admin_login"))
        session.clear()
        session["user_id"] = u["id"]
        session["name"] = u["name"]
        session["role"] = "admin"
        return redirect(url_for("admin.dashboard"))
    return render_template("admin/login.html")


@admin_bp.route("/register", methods=["GET", "POST"])
def admin_register():
    if session.get("user_id"):
        return redirect(url_for("admin.dashboard" if session.get("role") == "admin" else "candidate.dashboard"))
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
                flash("An account with this email already exists.", "error")
            else:
                db.execute(
                    "INSERT INTO users(name,email,password_hash,role,created_at) VALUES(?,?,?,?,?)",
                    (name, email, generate_password_hash(password), "admin", datetime.now().isoformat(timespec="seconds")),
                )
                db.commit()
                db.close()
                flash("Admin registration successful. Please log in.", "success")
                return redirect(url_for("admin.admin_login"))
        return redirect(url_for("admin.admin_register"))
    return render_template("admin/register.html")


@admin_bp.route("/dashboard")
@admin_required
def dashboard():
    db = get_db()
    jobs = db.execute("SELECT COUNT(*) FROM jobs WHERE created_by=?", (session["user_id"],)).fetchone()[0]
    candidates = db.execute("SELECT COUNT(*) FROM users WHERE role='candidate'").fetchone()[0]
    apps = db.execute("SELECT COUNT(*) FROM applications a JOIN jobs j ON a.job_id=j.id WHERE j.created_by=?", (session["user_id"],)).fetchone()[0]
    recent = db.execute("""SELECT u.name,u.email,j.title,m.overall_score,a.status,a.applied_at
                         FROM applications a JOIN users u ON a.user_id=u.id JOIN jobs j ON a.job_id=j.id
                         LEFT JOIN match_results m ON a.id=m.application_id WHERE j.created_by=?
                         ORDER BY a.id DESC LIMIT 10""", (session["user_id"],)).fetchall()
    db.close()
    return render_template("admin/dashboard.html", jobs_count=jobs, candidates_count=candidates, applications_count=apps, recent=recent)


@admin_bp.route("/jobs")
@admin_required
def jobs():
    db = get_db()
    rows = db.execute("""SELECT j.*,(SELECT COUNT(*) FROM applications a WHERE a.job_id=j.id) applicants
                                    FROM jobs j WHERE j.created_by=? ORDER BY j.id DESC""", (session["user_id"],)).fetchall()
    db.close()
    return render_template("admin/jobs.html", jobs=rows)


@admin_bp.route("/jobs/add", methods=["GET", "POST"])
@admin_required
def add_job():
    if request.method == "POST":
        title = request.form.get("title", "").strip()
        company = request.form.get("company", "").strip()
        desc = request.form.get("description", "").strip()
        skills = request.form.get("required_skills", "").strip()
        if not title or not desc or not skills:
            flash("Job title, description and required skills are required.", "error")
        else:
            db = get_db()
            db.execute("""INSERT INTO jobs(title,company,description,required_skills,created_by,created_at)
                                       VALUES(?,?,?,?,?,?)""", (title, company, desc, skills, session["user_id"], datetime.now().isoformat(timespec="seconds")))
            db.commit()
            db.close()
            flash("Job posted successfully.", "success")
            return redirect(url_for("admin.jobs"))
        return redirect(url_for("admin.add_job"))
    return render_template("admin/add_job.html")


@admin_bp.route("/jobs/delete/<int:job_id>", methods=["POST"])
@admin_required
def delete_job(job_id):
    db = get_db()
    db.execute("DELETE FROM jobs WHERE id=? AND created_by=?", (job_id, session["user_id"]))
    db.commit()
    db.close()
    flash("Job deleted.", "success")
    return redirect(url_for("admin.jobs"))


@admin_bp.route("/jobs/<int:job_id>/applications")
@admin_required
def applications(job_id):
    db = get_db()
    job = db.execute("SELECT * FROM jobs WHERE id=? AND created_by=?", (job_id, session["user_id"])).fetchone()
    if not job:
        db.close()
        flash("Job not found.", "error")
        return redirect(url_for("admin.jobs"))
    rows = db.execute("""SELECT u.name,u.email,r.filename,m.overall_score,m.ats_score,m.semantic_score,m.skill_score,
                      m.matched_skills,m.missing_skills,a.status FROM applications a JOIN users u ON a.user_id=u.id
                      JOIN resumes r ON a.resume_id=r.id JOIN match_results m ON a.id=m.application_id
                      WHERE a.job_id=? ORDER BY m.overall_score DESC""", (job_id,)).fetchall()
    db.close()
    return render_template("admin/applications.html", job=job, applications=rows)
