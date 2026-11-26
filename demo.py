"""Launch an isolated local demo without touching the user's ledger."""
import os
import secrets
from datetime import datetime, timedelta, timezone
from pathlib import Path
from uuid import uuid4

BASE = Path(__file__).resolve().parent
SAMPLE = [
    (1, "in", "Lương", 9500000, "Lương tháng"),
    (2, "out", "Nhà ở", 2200000, "Tiền thuê phòng"),
    (4, "out", "Ăn uống", 345000, "Đi siêu thị"),
    (6, "out", "Di chuyển", 90000, "Đổ xăng"),
    (9, "in", "Freelance", 1800000, "Bàn giao landing page"),
    (12, "out", "Học tập", 249000, "Sách lập trình"),
    (15, "out", "Giải trí", 120000, "Vé xem phim"),
    (18, "out", "Ăn uống", 65000, "Cơm trưa"),
]

def seed():
    from app.auth import hash_password
    from app.db import initialize, connection
    initialize()
    today = datetime.now(timezone(timedelta(hours=7))).date()
    previous = today.replace(day=1) - timedelta(days=1)
    with connection() as db:
        db.execute("BEGIN IMMEDIATE")
        account = db.execute("SELECT id FROM users WHERE username='demo'").fetchone()
        if account:
            owner = account["id"]
        else:
            salt = secrets.token_bytes(16)
            owner = db.execute("INSERT INTO users(username,salt,digest) VALUES (?,?,?)",
                ("demo", salt, hash_password("SoMocDemo123!", salt))).lastrowid
        db.execute("CREATE TABLE IF NOT EXISTS demo_months (month TEXT PRIMARY KEY)")
        for last_day in (previous, today):
            month = last_day.strftime("%Y-%m")
            if not db.execute("INSERT OR IGNORE INTO demo_months VALUES (?)", (month,)).rowcount:
                continue
            for day, kind, category, amount, note in SAMPLE:
                when = last_day.replace(day=min(day,last_day.day))
                db.execute("""INSERT INTO entries(owner,day,kind,category,amount,note,request_id)
                    VALUES (?,?,?,?,?,?,?)""",(owner,when.isoformat(),kind,category,amount,note,str(uuid4())))
            db.execute("INSERT INTO budgets VALUES(?,?,?)",(owner,month,5000000))

if __name__ == "__main__":
    from run import serve
    serve("demo")
