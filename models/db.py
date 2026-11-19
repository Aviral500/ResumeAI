import os, sqlite3
BASE_DIR=os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DB_PATH=os.path.join(BASE_DIR,"database","resume_screening.db")
SCHEMA_PATH=os.path.join(BASE_DIR,"database","schema.sql")
def get_db():
    c=sqlite3.connect(DB_PATH); c.row_factory=sqlite3.Row; c.execute("PRAGMA foreign_keys=ON"); return c
def init_db():
    os.makedirs(os.path.dirname(DB_PATH),exist_ok=True)
    c=get_db()
    with open(SCHEMA_PATH,encoding="utf-8") as f: c.executescript(f.read())
    c.commit(); c.close()
