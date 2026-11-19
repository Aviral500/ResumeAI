import os,json
from datetime import datetime
from functools import wraps
from flask import Blueprint,render_template,request,redirect,url_for,session,flash,current_app
from werkzeug.utils import secure_filename
from models.db import get_db
from models.resume_analyzer import analyze_resume,match_resume_to_job
candidate_bp=Blueprint("candidate",__name__,url_prefix="/candidate")
def candidate_required(f):
    @wraps(f)
    def w(*a,**k):
        if session.get("role")!="candidate": flash("Candidate login required.","error"); return redirect(url_for("auth.login"))
        return f(*a,**k)
    return w
@candidate_bp.route("/dashboard")
@candidate_required
def dashboard():
    db=get_db(); jobs=db.execute("SELECT * FROM jobs ORDER BY id DESC").fetchall()
    apps=db.execute("""SELECT a.id,a.status,a.applied_at,j.title,j.company,m.overall_score,m.ats_score
                       FROM applications a JOIN jobs j ON a.job_id=j.id LEFT JOIN match_results m ON a.id=m.application_id
                       WHERE a.user_id=? ORDER BY a.id DESC""",(session["user_id"],)).fetchall(); db.close()
    return render_template("candidate/dashboard.html",jobs=jobs,applications=apps)
@candidate_bp.route("/jobs/<int:job_id>")
@candidate_required
def job_detail(job_id):
    db=get_db(); job=db.execute("SELECT * FROM jobs WHERE id=?",(job_id,)).fetchone(); db.close()
    if not job: flash("Job not found.","error"); return redirect(url_for("candidate.dashboard"))
    return render_template("candidate/job_detail.html",job=job)
@candidate_bp.route("/apply/<int:job_id>",methods=["GET","POST"])
@candidate_required
def apply(job_id):
    db=get_db(); job=db.execute("SELECT * FROM jobs WHERE id=?",(job_id,)).fetchone()
    existing=db.execute("SELECT id FROM applications WHERE user_id=? AND job_id=?",(session["user_id"],job_id)).fetchone()
    if not job: db.close(); flash("Job not found.","error"); return redirect(url_for("candidate.dashboard"))
    if existing: db.close(); flash("You have already applied for this job.","error"); return redirect(url_for("candidate.dashboard"))
    if request.method=="POST":
        f=request.files.get("resume")
        if not f or not f.filename.lower().endswith(".pdf"):
            db.close(); flash("Please select a PDF resume.","error"); return redirect(url_for("candidate.apply",job_id=job_id))
        os.makedirs(current_app.config["UPLOAD_FOLDER"],exist_ok=True)
        filename=secure_filename(f.filename); unique=f"{session['user_id']}_{datetime.now().strftime('%Y%m%d%H%M%S')}_{filename}"
        path=os.path.join(current_app.config["UPLOAD_FOLDER"],unique); f.save(path)
        try:
            analysis=analyze_resume(path); match=match_resume_to_job(analysis["clean_text"],job["description"],analysis["skills"],job["required_skills"])
            now=datetime.now().isoformat(timespec="seconds")
            db.execute("INSERT INTO resumes(user_id,filename,extracted_text,skills,ats_score,uploaded_at) VALUES(?,?,?,?,?,?)",
                       (session["user_id"],filename,analysis["clean_text"],json.dumps(analysis["skills"]),analysis["ats_score"],now))
            resume_id=db.execute("SELECT last_insert_rowid()").fetchone()[0]
            db.execute("INSERT INTO applications(user_id,job_id,resume_id,status,applied_at) VALUES(?,?,?,?,?)",(session["user_id"],job_id,resume_id,"Applied",now))
            app_id=db.execute("SELECT last_insert_rowid()").fetchone()[0]
            db.execute("""INSERT INTO match_results(application_id,semantic_score,skill_score,overall_score,matched_skills,
                         missing_skills,suggestions,ats_score,created_at) VALUES(?,?,?,?,?,?,?,?,?)""",
                       (app_id,match["semantic_score"],match["skill_score"],match["overall_score"],json.dumps(match["matched_skills"]),
                        json.dumps(match["missing_skills"]),json.dumps(match["suggestions"]),analysis["ats_score"],now))
            db.commit(); db.close(); return redirect(url_for("candidate.result",application_id=app_id))
        except Exception as e:
            db.close()
            if os.path.exists(path): os.remove(path)
            flash(f"Resume analysis failed: {e}","error")
            return redirect(url_for("candidate.apply",job_id=job_id))
    db.close(); return render_template("candidate/apply.html",job=job)
@candidate_bp.route("/result/<int:application_id>")
@candidate_required
def result(application_id):
    db=get_db(); row=db.execute("""SELECT a.status,j.title job_title,j.company,r.filename,r.skills,r.ats_score,
             m.semantic_score,m.skill_score,m.overall_score,m.matched_skills,m.missing_skills,m.suggestions
             FROM applications a JOIN jobs j ON a.job_id=j.id JOIN resumes r ON a.resume_id=r.id
             JOIN match_results m ON a.id=m.application_id WHERE a.id=? AND a.user_id=?""",(application_id,session["user_id"])).fetchone(); db.close()
    if not row: flash("Result not found.","error"); return redirect(url_for("candidate.dashboard"))
    d=dict(row)
    for k in ["skills","matched_skills","missing_skills","suggestions"]: d[k]=json.loads(d[k] or "[]")
    return render_template("candidate/result.html",data=d)
