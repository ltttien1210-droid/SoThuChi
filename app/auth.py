import hashlib
import hmac
import os
import re
import secrets
import time

from starlette.exceptions import HTTPException

from .db import connection

COOKIE = "ledger_demo_session" if os.getenv("LEDGER_DEMO") == "1" else "ledger_session"

def fingerprint(value):
    return hashlib.sha256(value.encode()).hexdigest()

PBKDF2_PREFIX = b"pbkdf2-sha256:600000:"

def hash_password(password, salt):
    digest = hashlib.pbkdf2_hmac("sha256", password.encode(), salt, 600_000)
    return PBKDF2_PREFIX + digest

def password_matches(password, salt, stored):
    # Legacy records contain exactly 64 raw scrypt bytes.
    if len(stored) == 64 and hasattr(hashlib, "scrypt"):
        derived = hashlib.scrypt(password.encode(), salt=salt, n=2**15, r=8, p=3, maxmem=64*1024*1024)
    else:
        derived = hash_password(password, salt)
    return hmac.compare_digest(derived, stored)

def account(request, db):
    token = request.cookies.get(COOKIE, "")
    row = db.execute("""SELECT u.id,u.username FROM sessions s JOIN users u ON s.owner=u.id
        WHERE s.token=? AND expires>?""", (fingerprint(token), int(time.time()))).fetchone()
    if not row:
        raise HTTPException(401, "Hãy đăng nhập để mở sổ.")
    return row

def credentials(body, registering):
    name, password = body.get("username"), body.get("password")
    if not isinstance(name, str) or not isinstance(password, str) or len(password)>128:
        raise HTTPException(422, "Thông tin tài khoản không hợp lệ.")
    name = name.strip().lower()
    if not re.fullmatch(r"[a-z0-9_.-]{3,40}", name):
        raise HTTPException(422, "Tên đăng nhập dài 3–40 ký tự, dùng chữ không dấu, số, dấu chấm, gạch ngang hoặc gạch dưới.")
    if registering and len(password)<12:
        raise HTTPException(422, "Mật khẩu cần ít nhất 12 ký tự.")
    return name, password

def throttle(key, limit):
    now = int(time.time())
    with connection() as db:
        db.execute("DELETE FROM attempts WHERE expires<=?", (now,))
        db.execute("""INSERT INTO attempts VALUES (?,1,?) ON CONFLICT(key)
            DO UPDATE SET count=count+1""", (key, now+600))
        row = db.execute("SELECT count FROM attempts WHERE key=?", (key,)).fetchone()
    if row[0]>limit:
        raise HTTPException(429, "Bạn thao tác quá nhiều lần. Vui lòng thử lại sau 10 phút.")

def authenticate(request, body, registering):
    name, password = credentials(body, registering)
    addr = request.client.host if request.client else "local"
    throttle(("new:" if registering else "login:")+addr, 8 if registering else 40)
    if not registering:
        throttle("account:"+name, 12)
    with connection() as db:
        if registering:
            salt = secrets.token_bytes(16)
            insert = db.execute("""INSERT INTO users(username,salt,digest) VALUES(?,?,?)
                ON CONFLICT(username) DO NOTHING""", (name,salt,hash_password(password,salt)))
            if not insert.rowcount:
                raise HTTPException(409, "Tên đăng nhập đã được sử dụng.")
            owner = insert.lastrowid
        else:
            row = db.execute("SELECT * FROM users WHERE username=?", (name,)).fetchone()
            matched = password_matches(password, row["salt"] if row else bytes(16), row["digest"] if row else b"")
            if not row or not matched:
                raise HTTPException(401, "Tên đăng nhập hoặc mật khẩu chưa đúng.")
            owner = row["id"]
            db.execute("DELETE FROM attempts WHERE key=?", ("account:"+name,))
        token = secrets.token_urlsafe(32)
        db.execute("DELETE FROM sessions WHERE expires<=? OR token=?", (int(time.time()),fingerprint(request.cookies.get(COOKIE,""))))
        db.execute("INSERT INTO sessions VALUES(?,?,?)", (fingerprint(token),owner,int(time.time())+43200))
        return token
