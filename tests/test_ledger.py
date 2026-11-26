import os
import tempfile
import unittest
from uuid import uuid4
from unittest.mock import patch

from starlette.testclient import TestClient
from app.main import app

BASE="http://127.0.0.1:8000"
HEAD={"Origin":BASE,"X-Ledger-Request":"1"}
PASS="a-long-test-password"

class LedgerTests(unittest.TestCase):
    def setUp(self):
        folder=tempfile.TemporaryDirectory()
        self.addCleanup(folder.cleanup)
        config=patch.dict(os.environ,LEDGER_DB=folder.name+"/db")
        config.start()
        self.addCleanup(config.stop)
        self.client=TestClient(app,base_url=BASE)
        self.client.__enter__()
        self.addCleanup(self.client.__exit__,None,None,None)
        self.register("owner")

    def register(self,name):
        response=self.post("register",{"username":name,"password":PASS})
        self.assertEqual(response.status_code,200,response.text)

    def post(self,path,body):
        return self.client.post("/api/"+path,json=body,headers=HEAD)

    def entry(self,kind="out",day="2026-11-20",amount=20000):
        return dict(kind=kind,day=day,amount=amount,category="Ăn uống" if kind=="out" else "Lương",
                    note="=1+1",request_id=str(uuid4()))

    def report(self,extra=""):
        return self.client.get("/api/report?month=2026-11"+extra).json()

    def test_monthly_report_and_budget(self):
        for body in [self.entry(),self.entry("in",amount=100000),self.entry(day="2026-12-01"),self.entry("in",day="2026-10-31",amount=9000)]:
            self.assertEqual(self.post("entries",body).status_code,200)
        self.post("budget",dict(amount=50000,month="2026-11"))
        r=self.report("&kind=in")
        self.assertEqual((r["count"],r["budget"],r["totals"]),(1,50000,{"in":100000,"out":20000}))
        self.assertEqual((r["opening"],r["closing"]),(9000,89000))
        self.assertEqual(r["breakdown"][0]["total"],20000)
        self.assertIn("'=1+1",self.client.get("/api/export?month=2026-11").text)

    def test_retry_and_conflict(self):
        item=self.entry()
        for _ in range(2): self.post("entries",item)
        self.assertEqual(self.report()["count"],1)
        row=self.report()["rows"][0]
        url="/api/entries/"+str(row["id"])
        row["amount"]=30000
        self.assertEqual(self.client.put(url,json=row,headers=HEAD).status_code,200)
        self.assertEqual(self.client.put(url,json=row,headers=HEAD).status_code,409)
        self.assertEqual(self.client.request("DELETE",url,json={"version":2},headers=HEAD).status_code,200)
        self.assertEqual(self.report()["count"],0)

    def test_owner_isolation(self):
        self.post("entries",self.entry())
        row=self.report()["rows"][0]
        self.register("another")
        self.assertEqual(self.report()["count"],0)
        url="/api/entries/"+str(row["id"])
        self.assertEqual(self.client.put(url,json=row,headers=HEAD).status_code,409)
        self.assertEqual(self.client.request("DELETE",url,json=row,headers=HEAD).status_code,409)

    def test_auth_and_origin(self):
        cookie=self.client.cookies.get("ledger_session")
        self.assertEqual(self.client.post("/api/logout",json={}).status_code,403)
        self.assertEqual(self.post("logout",{}).status_code,200)
        self.client.cookies.set("ledger_session",cookie)
        self.assertEqual(self.client.get("/api/me").status_code,401)
        self.assertEqual(self.post("login",dict(username="owner",password=PASS)).status_code,200)

    def test_input_validation(self):
        for body in [self.entry(amount=-2),self.entry(amount=2.3),self.entry(day="2026-02-31")]:
            self.assertEqual(self.post("entries",body).status_code,422)
        self.assertEqual(self.client.get("/api/report?month=2026-13").status_code,422)

    def test_rate_limit(self):
        for _ in range(12):
            self.assertEqual(self.post("login",dict(username="owner",password="wrong")).status_code,401)
        self.assertEqual(self.post("login",dict(username="owner",password=PASS)).status_code,429)

    def test_pagination(self):
        for _ in range(21):self.post("entries",self.entry())
        self.assertEqual(len(self.report()["rows"]),20)
        self.assertEqual(len(self.report("&page=2")["rows"]),1)

    def test_search_matches_vietnamese_and_export(self):
        self.post("entries", self.entry())
        self.post("entries", self.entry("in",amount=200000))
        result = self.report("&q=an%20uong")
        self.assertEqual(result["count"], 1)
        self.assertEqual(result["totals"]["in"], 200000)
        csv = self.client.get("/api/export?month=2026-11&q=an%20uong").text
        self.assertIn("Ăn uống", csv)
        self.assertNotIn("Lương", csv)
