import json
import os
from contextlib import asynccontextmanager
from pathlib import Path
from urllib.parse import urlsplit

from starlette.applications import Starlette
from starlette.concurrency import run_in_threadpool
from starlette.exceptions import HTTPException
from starlette.middleware import Middleware
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.middleware.trustedhost import TrustedHostMiddleware
from starlette.responses import FileResponse, JSONResponse, Response
from starlette.routing import Mount, Route
from starlette.staticfiles import StaticFiles

from . import auth, ledger
from .db import connection, initialize

ROOT=Path(__file__).parent
ORIGIN=os.getenv("APP_ORIGIN","http://127.0.0.1:8000").rstrip("/")
URL=urlsplit(ORIGIN)
if URL.scheme not in ("http","https") or not URL.hostname or URL.path or URL.query or URL.fragment or URL.username:
    raise RuntimeError("APP_ORIGIN phải là địa chỉ gốc của ứng dụng.")
if URL.scheme!="https" and URL.hostname not in ("localhost","127.0.0.1"):
    raise RuntimeError("Tên miền công khai yêu cầu HTTPS.")

async def read_body(request):
    if (request.headers.get("origin")!=ORIGIN or request.headers.get("x-ledger-request")!="1"
            or request.headers.get("content-type","").split(";")[0]!="application/json"):
        raise HTTPException(403,"Yêu cầu không hợp lệ. Hãy mở đúng địa chỉ APP_ORIGIN.")
    data=bytearray()
    async for part in request.stream():
        if len(data)+len(part)>8192:
            raise HTTPException(413,"Dữ liệu vượt giới hạn.")
        data.extend(part)
    try:
        obj=json.loads(data)
    except (ValueError,UnicodeError,RecursionError):
        raise HTTPException(400,"Dữ liệu không hợp lệ.")
    if not isinstance(obj,dict):
        raise HTTPException(400,"Dữ liệu không hợp lệ.")
    return obj

async def login(request):
    token=await run_in_threadpool(auth.authenticate,request,await read_body(request),request.url.path.endswith("/register"))
    response=JSONResponse({"ok":True})
    response.set_cookie(auth.COOKIE,token,max_age=43200,httponly=True,secure=URL.scheme=="https",samesite="strict")
    return response

def handle(request,body):
    with connection() as db:
        user=auth.account(request,db)
        owner=user["id"]
        path=request.url.path
        if path=="/api/me":
            return JSONResponse({"username":user["username"]})
        if path=="/api/logout":
            db.execute("DELETE FROM sessions WHERE token=?",(auth.fingerprint(request.cookies[auth.COOKIE]),))
            response=JSONResponse({"ok":True})
            response.delete_cookie(auth.COOKIE)
            return response
        if path in ("/api/report","/api/export"):
            q=request.query_params
            try:
                page=int(q.get("page","1"))
            except ValueError:
                raise HTTPException(422,"Trang không hợp lệ.")
            db.execute("BEGIN")
            result=ledger.report(db,owner,q.get("month",""),q.get("kind","all"),page,path.endswith("export"),q.get("q",""))
            if isinstance(result,str):
                return Response(result,media_type="text/csv",headers={"Content-Disposition":f'attachment; filename="thu-chi-{q["month"]}.csv"'})
            return JSONResponse(result)
        if path=="/api/budget":
            month=body.get("month")
            ledger.month_range(month)
            db.execute("""INSERT INTO budgets VALUES(?,?,?) ON CONFLICT(owner,month)
                DO UPDATE SET amount=excluded.amount""",(owner,month,ledger.money(body.get("amount"),0)))
        else:
            entry_id=request.path_params.get("entry_id")
            if entry_id and entry_id>2**63-1:
                raise HTTPException(404,"Không tìm thấy giao dịch.")
            if request.method=="DELETE":
                ledger.check_changed(db.execute("DELETE FROM entries WHERE owner=? AND id=? AND version=?",
                                               (owner,entry_id,ledger.version(body))))
            else:
                ledger.save_entry(db,owner,body,entry_id)
        return JSONResponse({"ok":True})

async def api(request):
    body=await read_body(request) if request.method not in ("GET","HEAD") else {}
    return await run_in_threadpool(handle,request,body)

async def mode(request):
    return JSONResponse({"demo": os.getenv("LEDGER_DEMO") == "1"})

async def index(request):
    return FileResponse(ROOT/"templates/index.html")

async def error(request,exc):
    return JSONResponse({"error":exc.detail},status_code=exc.status_code)

@asynccontextmanager
async def lifespan(app):
    initialize()
    yield

app=Starlette(lifespan=lifespan,exception_handlers={HTTPException:error},middleware=[
    Middleware(TrustedHostMiddleware,allowed_hosts=[URL.hostname])],routes=[
    Route("/",index), Route("/api/mode",mode),Mount("/static",StaticFiles(directory=ROOT/"static")),
    *[Route("/api/"+name,login,methods=["POST"]) for name in ("login","register")],
    *[Route("/api/"+name,api) for name in ("me","report","export")],
    *[Route("/api/"+name,api,methods=["POST"]) for name in ("logout","budget","entries")],
    Route("/api/entries/{entry_id:int}",api,methods=["PUT","DELETE"])])

async def headers(request,call_next):
    response=await call_next(request)
    response.headers.update({"X-Content-Type-Options":"nosniff","X-Frame-Options":"DENY",
        "Referrer-Policy":"no-referrer","Cache-Control":"no-store",
        "Content-Security-Policy":"default-src 'self'; script-src 'self'; style-src 'self'; object-src 'none'; frame-ancestors 'none'; base-uri 'none'; form-action 'self'"})
    if URL.scheme=="https":
        response.headers["Strict-Transport-Security"]="max-age=31536000"
    return response
app.add_middleware(BaseHTTPMiddleware, dispatch=headers)
