import re, pdfplumber
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

SKILL_ALIASES={
"python":["python"],"java":["java"],"c++":["c++","cpp"],"javascript":["javascript","js"],
"html":["html","html5"],"css":["css","css3"],"flask":["flask"],"django":["django"],
"fastapi":["fastapi"],"sql":["sql","mysql","postgresql","postgres","sqlite","sql server"],
"mysql":["mysql"],"postgresql":["postgresql","postgres"],"sqlite":["sqlite"],
"mongodb":["mongodb","mongo db"],"pandas":["pandas"],"numpy":["numpy"],
"scikit-learn":["scikit-learn","sklearn","scikit learn"],"tensorflow":["tensorflow"],
"pytorch":["pytorch","torch"],"machine learning":["machine learning","machine-learning"],
"deep learning":["deep learning"],"nlp":["nlp","natural language processing"],
"data analysis":["data analysis","data analytics"],"git":["git"],"github":["github"],
"docker":["docker"],"aws":["aws","amazon web services"],"azure":["azure"],
"rest api":["rest api","restful api","restful apis","restful"],
"api":["api","apis"],"power bi":["power bi"],"tableau":["tableau"],"excel":["excel"],
"linux":["linux"],"oop":["oop","oops","object oriented programming"],
"dsa":["dsa","data structures","data structures and algorithms"]
}
def clean_text(t):
    t=(t or "").lower().replace("–","-").replace("—","-")
    return re.sub(r"\s+"," ",t).strip()
def extract_text_from_pdf(path):
    pages=[]
    with pdfplumber.open(path) as pdf:
        for p in pdf.pages:
            x=p.extract_text()
            if x: pages.append(x)
    text="\n".join(pages).strip()
    if not text: raise ValueError("No selectable text was found. Please upload a text-based PDF.")
    return text
def contains_skill(text,alias):
    return bool(re.search(rf"(?<![a-z0-9+#]){re.escape(alias.lower().strip())}(?![a-z0-9+#])",text))
def extract_skills(text):
    src=clean_text(text); found=set()
    for canonical,aliases in SKILL_ALIASES.items():
        if any(contains_skill(src,a) for a in aliases): found.add(canonical)
    return sorted(found)
def ats_score(text,skills):
    t=clean_text(text); w=len(t.split()); s=0
    s+=20 if w>=300 else 15 if w>=180 else 10 if w>=100 else 0
    s+=15 if re.search(r"\b(skills|technical skills)\b",t) else 0
    s+=15 if re.search(r"\b(experience|work experience|internship)\b",t) else 0
    s+=15 if re.search(r"\b(education|b\.?tech|bachelor|degree|college|university)\b",t) else 0
    s+=15 if re.search(r"\b(project|projects)\b",t) else 0
    s+=5 if re.search(r"\b[\w.+-]+@[\w-]+\.[\w.-]+\b",t) else 0
    s+=5 if re.search(r"\b\d{10}\b",t) else 0
    s+=10 if len(skills)>=8 else 7 if len(skills)>=5 else 4 if len(skills)>=3 else 0
    return min(100,s)
def analyze_resume(path):
    raw=extract_text_from_pdf(path); cleaned=clean_text(raw); skills=extract_skills(raw)
    return {"raw_text":raw,"clean_text":cleaned,"skills":skills,"ats_score":ats_score(raw,skills)}
def normalize_required_skills(text):
    if not text:return []
    detected=extract_skills(text); result=set(detected)
    for p in re.split(r"[,;\n|]+",text.lower()):
        p=re.sub(r"\s+"," ",p).strip()
        if not p: continue
        matched=False
        for c,a in SKILL_ALIASES.items():
            if p==c or p in [x.lower() for x in a]: result.add(c); matched=True; break
        if not matched: result.add(p)
    return sorted(result)
def expand(skills):
    x={s.lower() for s in skills}
    if x & {"mysql","postgresql","sqlite"}: x.add("sql")
    return x
def match_resume_to_job(resume_text,job_text,resume_skills,required_text):
    r=clean_text(resume_text); j=clean_text(job_text); semantic=0
    if r and j:
        try:
            v=TfidfVectorizer(stop_words="english",ngram_range=(1,2),max_features=5000)
            m=v.fit_transform([r,j]); semantic=float(cosine_similarity(m[0:1],m[1:2])[0][0]*100)
        except ValueError: pass
    req=normalize_required_skills(required_text) or extract_skills(job_text)
    rs,qs=expand(resume_skills),expand(req)
    if "rest api" in qs: qs.discard("api")
    matched=sorted(rs&qs); missing=sorted(qs-rs)
    skill=(len(matched)/len(qs)*100) if qs else 0
    relevance=min(100,len(matched)*15+semantic*.25)
    overall=round(min(100,semantic*.40+skill*.40+relevance*.20),1)
    suggestions=[]
    if missing:suggestions.append("Consider adding or strengthening evidence for: "+", ".join(missing[:8]))
    if semantic<35:suggestions.append("Tailor the resume summary, projects and experience descriptions to the job description.")
    elif semantic<55:suggestions.append("Add more job-specific keywords naturally within projects and experience.")
    if skill<50:suggestions.append("The resume covers fewer than half of the detected required skills for this role.")
    if len(r.split())<180:suggestions.append("Consider adding measurable project or experience details.")
    if not suggestions:suggestions.append("The resume is well aligned with this role. Continue tailoring achievements to the job description.")
    return {"semantic_score":round(semantic,1),"skill_score":round(skill,1),"overall_score":overall,
            "matched_skills":matched,"missing_skills":missing,"suggestions":suggestions}
