"""Local administrative operations, available only with database file access."""
import argparse
import getpass
import os
import secrets
import sqlite3
from pathlib import Path

from app.auth import hash_password
from app.db import connection

def main():
    parser=argparse.ArgumentParser()
    commands=parser.add_subparsers(dest="command",required=True)
    commands.add_parser("backup").add_argument("output",type=Path)
    commands.add_parser("reset-password").add_argument("username")
    args=parser.parse_args()
    path=Path(os.getenv("LEDGER_DB","data/ledger.sqlite3"))
    if not path.is_file():
        parser.error("Chưa có cơ sở dữ liệu.")
    with connection() as db:
        if args.command=="backup":
            # Exclusive creation keeps existing snapshots intact.
            fd=os.open(args.output,os.O_CREAT|os.O_EXCL|os.O_WRONLY,0o600)
            os.close(fd)
            try:
                dest=sqlite3.connect(args.output)
                try:
                    db.backup(dest)
                    if dest.execute("PRAGMA integrity_check").fetchone()[0]!="ok":
                        raise RuntimeError("Bản sao chưa toàn vẹn.")
                finally:
                    dest.close()
            except BaseException:
                args.output.unlink(missing_ok=True)
                raise
            print("Đã sao lưu và kiểm tra dữ liệu.")
        else:
            user=db.execute("SELECT id FROM users WHERE username=?",(args.username.lower(),)).fetchone()
            if not user:
                parser.error("Không tìm thấy tài khoản.")
            password=getpass.getpass("Mật khẩu mới: ")
            if not 12<=len(password)<=128 or password!=getpass.getpass("Nhập lại: "):
                parser.error("Mật khẩu phải dài 12–128 ký tự và khớp ở cả hai lần nhập.")
            salt=secrets.token_bytes(16)
            db.execute("UPDATE users SET salt=?,digest=? WHERE id=?",(salt,hash_password(password,salt),user[0]))
            db.execute("DELETE FROM sessions WHERE owner=?",(user[0],))
            db.execute("DELETE FROM attempts WHERE key=?",("account:"+args.username.lower(),))
            print("Đã đổi mật khẩu và đóng các phiên cũ.")

if __name__=="__main__":
    main()
