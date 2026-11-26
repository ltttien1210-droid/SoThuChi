import calendar
import csv
import io
import re
from datetime import date
from uuid import UUID

from starlette.exceptions import HTTPException

GROUPS = {"in": ["Lương","Freelance","Quà tặng","Thu khác"],
          "out": ["Ăn uống","Di chuyển","Mua sắm","Nhà ở","Học tập","Sức khỏe","Giải trí","Chi khác"]}

def month_range(month):
    if not isinstance(month,str) or not re.fullmatch(r"[0-9]{4}-(0[1-9]|1[0-2])",month) or month.startswith("0000"):
        raise HTTPException(422,"Tháng không hợp lệ.")
    year,number = map(int,month.split("-"))
    return month+"-01", f"{month}-{calendar.monthrange(year,number)[1]}"

def money(value, minimum=1):
    if type(value) is not int or not minimum<=value<=999999999999:
        raise HTTPException(422,"Số tiền phải là số nguyên VND trong giới hạn cho phép.")
    return value

def save_entry(db, owner, body, entry_id=None):
    day,kind,cat,note = (body.get(k) for k in ("day","kind","category","note"))
    try:
        if date.fromisoformat(day).isoformat()!=day:
            raise ValueError()
    except (TypeError,ValueError):
        raise HTTPException(422,"Ngày giao dịch không hợp lệ.")
    if not isinstance(kind,str) or cat not in GROUPS.get(kind,[]) or not isinstance(note,str) or len(note)>200:
        raise HTTPException(422,"Kiểm tra danh mục và ghi chú (tối đa 200 ký tự).")
    values = (day,kind,cat,money(body.get("amount")),note.strip())
    if entry_id is None:
        try:
            key = str(UUID(str(body.get("request_id"))))
        except ValueError:
            raise HTTPException(422,"Mã giao dịch không hợp lệ.")
        db.execute("""INSERT INTO entries(day,kind,category,amount,note,owner,request_id)
            VALUES(?,?,?,?,?,?,?) ON CONFLICT(owner,request_id) DO NOTHING""", (*values,owner,key))
    else:
        updated = db.execute("""UPDATE entries SET day=?,kind=?,category=?,amount=?,note=?,version=version+1
            WHERE owner=? AND id=? AND version=?""", (*values,owner,entry_id,version(body)))
        check_changed(updated)

def version(body):
    value=body.get("version")
    if type(value) is not int or not 1<=value<=2147483647:
        raise HTTPException(422,"Phiên bản giao dịch không hợp lệ.")
    return value

def check_changed(cursor):
    if not cursor.rowcount:
        raise HTTPException(409,"Giao dịch đã thay đổi hoặc không còn khả dụng. Hãy tải lại sổ.")

def report(db,owner,month,kind,page,export=False,query=""):
    start,end=month_range(month)
    if kind not in ("all","in","out") or not 1<=page<=10000000:
        raise HTTPException(422,"Bộ lọc không hợp lệ.")
    base=" FROM entries WHERE owner=? AND day BETWEEN ? AND ?"
    params=(owner,start,end)
    where=base if kind=="all" else base+" AND kind=?"
    args=params if kind=="all" else (*params,kind)
    if len(query)>100:
        raise HTTPException(422,"Từ khóa tối đa 100 ký tự.")
    if query.strip():
        where+=" AND instr(search_text(category || ' ' || note), search_text(?)) > 0"
        args=(*args,query.strip())
    columns="SELECT id,day,kind,category,amount,note,version"
    order=" ORDER BY day DESC,id DESC"
    if export:
        stream=io.StringIO()
        writer=csv.writer(stream)
        writer.writerow(["Ngày","Loại","Danh mục","Số tiền (VND)","Ghi chú"])
        for row in db.execute(columns+where+order,args):
            note=row["note"]
            if note.lstrip().startswith(("=","+","-","@")) or note.startswith(("\t","\r","\n")):
                note="'"+note
            writer.writerow([row["day"],"Thu" if row["kind"]=="in" else "Chi",row["category"],row["amount"],note])
        return "\ufeff"+stream.getvalue()
    grouped=db.execute("SELECT kind,category,SUM(amount) AS total"+base+" GROUP BY kind,category ORDER BY total DESC",params).fetchall()
    totals={k:sum(r["total"] for r in grouped if r["kind"]==k) for k in GROUPS}
    budget=db.execute("SELECT amount FROM budgets WHERE owner=? AND month=?",(owner,month)).fetchone()
    count=db.execute("SELECT COUNT(*)"+where,args).fetchone()[0]
    page=min(page,max(1,(count+19)//20))
    opening=db.execute("""SELECT COALESCE(SUM(CASE WHEN kind='in' THEN amount ELSE -amount END),0)
        FROM entries WHERE owner=? AND day<?""",(owner,start)).fetchone()[0]
    return dict(opening=opening,closing=opening+totals["in"]-totals["out"],totals=totals,budget=budget[0] if budget else 0,
                breakdown=[dict(r) for r in grouped if r["kind"]=="out"],
                count=count,page=page,groups=GROUPS,
                rows=[dict(r) for r in db.execute(columns+where+order+" LIMIT 20 OFFSET ?",(*args,(page-1)*20))])
