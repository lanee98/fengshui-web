import sys
import tempfile
import unittest
from pathlib import Path

from flask import Flask

sys.path.insert(0, str(Path(__file__).parent / "webapp"))
from accounts import install_accounts
from app import app


class AccountTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(dir=Path(__file__).parent)
        self.app = Flask("account_test", root_path=self.temp.name)
        self.app.config["TESTING"] = True
        install_accounts(self.app)
        self.client = self.app.test_client()
        self.headers = {"X-Requested-With": "ImmerseHome"}
        self.data = dict(username="tester", password="test-password-123", nickname="测试住户", birthday="2000-01-01", country="中国", province="浙江省", city="杭州市", district="西湖区", goal="求职与专注")

    def tearDown(self):
        self.temp.cleanup()

    def send(self, path, data):
        return self.client.post(path, json=data, headers=self.headers)

    def test_registration_login_and_profile_persistence(self):
        self.assertEqual(self.send("/api/account/register", self.data).status_code, 201)
        self.assertEqual(self.client.get("/api/account").json["user"]["profile"]["city"], "杭州市")
        self.assertEqual(self.send("/api/account/logout", {}).status_code, 200)
        self.assertIsNone(self.client.get("/api/account").json["user"])
        self.assertEqual(self.send("/api/account/login", dict(username="tester", password="wrong")).status_code, 401)
        self.assertEqual(self.send("/api/account/login", self.data).status_code, 200)
        profile = {**self.data, "city": "宁波市"}
        self.assertEqual(self.client.put("/api/account", json=profile, headers=self.headers).status_code, 200)
        self.assertEqual(self.client.get("/api/account").json["user"]["profile"]["city"], "宁波市")

    def test_duplicate_and_validation_and_cross_site_guard(self):
        self.assertEqual(self.send("/api/account/register", {**self.data, "birthday": "2999-01-01"}).status_code, 400)
        self.assertEqual(self.send("/api/account/register", self.data).status_code, 201)
        self.assertEqual(self.send("/api/account/register", self.data).status_code, 409)
        self.assertEqual(self.client.post("/api/account/logout", json={}).status_code, 403)
        self.assertEqual(self.client.post("/api/account/logout", json={}, headers={**self.headers, "Origin": "https://other.example"}).status_code, 403)


class ExistingFunctionTests(unittest.TestCase):
    def test_original_audit_and_repair_and_assets(self):
        client = app.test_client()
        self.assertEqual(len(client.get("/api/rules").json), 20)
        scene = client.get("/api/scene/demo_scene").json
        result = client.post("/api/audit", json=scene)
        self.assertEqual(result.status_code, 200)
        self.assertEqual(result.json["rule_count"], 20)
        repair = client.post("/api/repair", json={"scene": scene, "mode": "auto"})
        self.assertEqual(repair.status_code, 200)
        for url in ("/", "/plan", "/3d", "/refresh", "/living.css", "/living.js", "/inspiration/room-0.jpg"):
            response = client.get(url)
            self.assertEqual(response.status_code, 200, url)
            response.close()


if __name__ == "__main__":
    unittest.main()
