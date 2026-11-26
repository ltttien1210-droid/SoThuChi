import hashlib
import os
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import patch

from starlette.testclient import TestClient
from app import auth
from app.main import app, ORIGIN
from demo import seed

class PasswordCompatibility(unittest.TestCase):
    def test_demo_without_scrypt(self):
        with TemporaryDirectory() as tmp, patch.dict(os.environ, LEDGER_DB=tmp+"/demo.db"):
            original = getattr(hashlib, "scrypt", None)
            if original:
                delattr(hashlib, "scrypt")
                self.addCleanup(setattr, hashlib, "scrypt", original)
            seed()
            with TestClient(app, base_url=ORIGIN) as client:
                headers={"Origin":ORIGIN,"X-Ledger-Request":"1"}
                for password, status in [("wrong",401),("SoMocDemo123!",200)]:
                    response=client.post("/api/login",headers=headers,json={"username":"demo","password":password})
                    self.assertEqual(response.status_code,status)
                self.assertEqual(client.get("/api/me").json()["username"],"demo")

    @unittest.skipUnless(hasattr(hashlib,"scrypt"),"Legacy scrypt support unavailable")
    def test_existing_scrypt_account(self):
        salt=b"1234567890abcdef"
        old=hashlib.scrypt(b"old-password",salt=salt,n=32768,r=8,p=3,maxmem=64*1024*1024)
        self.assertTrue(auth.password_matches("old-password",salt,old))
        self.assertFalse(auth.password_matches("wrong",salt,old))
