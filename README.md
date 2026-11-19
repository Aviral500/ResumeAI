# AI Resume Screening & Job Matching System

Admin posts jobs. Candidates register/login, browse jobs, upload a PDF resume, and receive ATS, TF-IDF, skill-match, missing-skill and recommendation results.

## Run
python -m venv venv
Windows PowerShell: .\venv\Scripts\Activate.ps1
pip install -r requirements.txt
python database/seed_admin.py
python app.py

Open http://127.0.0.1:5000

Demo admin: admin@resumeai.local / admin123

The project uses Flask + SQLite + pdfplumber + scikit-learn and does not require a GPU or heavy transformer model.
