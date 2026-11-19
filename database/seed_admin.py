from datetime import datetime
from werkzeug.security import generate_password_hash
from models.db import init_db,get_db
init_db(); db=get_db(); email="admin@resumeai.local"; password="admin123"
if not db.execute("SELECT id FROM users WHERE email=?",(email,)).fetchone():
    db.execute("INSERT INTO users(name,email,password_hash,role,created_at) VALUES(?,?,?,?,?)",
               ("System Admin",email,generate_password_hash(password),"admin",datetime.now().isoformat(timespec="seconds"))); db.commit()
print("Admin login:",email,"/","admin123"); db.close()
