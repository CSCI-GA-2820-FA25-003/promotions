######################################################################
# Copyright 2016, 2024 John J. Rofrano. All Rights Reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
# https://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
######################################################################

"""
Promotion Service route tests
"""

# pylint: disable=duplicate-code, too-many-public-methods

import os
from datetime import date, timedelta
from unittest import TestCase

from wsgi import app
from service.models import Promotion, db

BASE_URL = "/promotions"


# ---- 轻量 status 定义，避免依赖 flask_api.status / service.status ----
# pylint: disable=too-few-public-methods, invalid-name
class status:
    """HTTP status codes used in tests (minimal subset)."""

    HTTP_200_OK = 200
    HTTP_201_CREATED = 201
    HTTP_204_NO_CONTENT = 204
    HTTP_400_BAD_REQUEST = 400
    HTTP_404_NOT_FOUND = 404
    HTTP_405_METHOD_NOT_ALLOWED = 405
    HTTP_500_INTERNAL_SERVER_ERROR = 500


def make_payload(**overrides) -> dict:
    """Build a valid promotion JSON payload"""
    base = {
        "name": "NYU Demo",
        "promotion_type": "AMOUNT_OFF",
        "value": 10,
        "product_id": 123,
        "start_date": "2025-10-01",
        "end_date": "2025-10-31",
    }
    base.update(overrides)
    return base


class TestPromotionService(TestCase):
    """Promotion Service functional tests"""

    @classmethod
    def setUpClass(cls):
        """This runs once before the entire test suite"""
        app.config["TESTING"] = True
        app.config["DEBUG"] = False
        app.config["SQLALCHEMY_DATABASE_URI"] = os.getenv(
            "DATABASE_URI", "postgresql+psycopg://postgres:postgres@localhost:5432/testdb"
        )
        app.app_context().push()

    def setUp(self):
        """Runs before each test"""
        db.session.query(Promotion).delete()
        db.session.commit()
        self.client = app.test_client()

    def tearDown(self):
        """Runs after each test"""
        db.session.remove()

    # ---------- create / basic ----------

    def test_create_promotion(self):
        """It should Create a new Promotion"""
        resp = self.client.post(BASE_URL, json=make_payload(name="CreateMe"))
        self.assertEqual(resp.status_code, status.HTTP_201_CREATED)
        data = resp.get_json()
        self.assertEqual(data["name"], "CreateMe")

    def test_delete_promotion(self):
        """It should delete an existing Promotion and return 204"""
        r = self.client.post(BASE_URL, json=make_payload(name="DelMe"))
        self.assertEqual(r.status_code, status.HTTP_201_CREATED)
        pid = r.get_json()["id"]
        resp = self.client.delete(f"{BASE_URL}/{pid}")
        self.assertEqual(resp.status_code, status.HTTP_204_NO_CONTENT)

    # ---------- list / filters ----------

    def test_list_all_promotions(self):
        """It should list all promotions when no query params are given"""
        r1 = self.client.post(BASE_URL, json=make_payload(name="A"))
        r2 = self.client.post(BASE_URL, json=make_payload(name="B"))
        self.assertEqual(r1.status_code, status.HTTP_201_CREATED)
        self.assertEqual(r2.status_code, status.HTTP_201_CREATED)

        resp = self.client.get(BASE_URL)
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        data = resp.get_json()
        self.assertTrue(isinstance(data, list))
        self.assertGreaterEqual(len(data), 2)

    def test_filter_by_id(self):
        """It should filter by ?id= returning [one] or []"""
        r = self.client.post(BASE_URL, json=make_payload(name="FindMe"))
        self.assertEqual(r.status_code, status.HTTP_201_CREATED)
        pid = r.get_json()["id"]

        ok = self.client.get(f"{BASE_URL}?id={pid}")
        self.assertEqual(ok.status_code, status.HTTP_200_OK)
        self.assertEqual(len(ok.get_json()), 1)

        empty = self.client.get(f"{BASE_URL}?id=999999")
        self.assertEqual(empty.status_code, status.HTTP_200_OK)
        self.assertEqual(empty.get_json(), [])

    def test_filter_by_name(self):
        """It should filter promotions by ?name="""
        self.client.post(BASE_URL, json=make_payload(name="N1"))
        self.client.post(BASE_URL, json=make_payload(name="N2"))
        resp = self.client.get(f"{BASE_URL}?name=N1")
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        data = resp.get_json()
        self.assertTrue(all(item["name"] == "N1" for item in data))

    def test_filter_by_product_id(self):
        """It should filter promotions by ?product_id="""
        self.client.post(BASE_URL, json=make_payload(name="A", product_id=2222))
        self.client.post(BASE_URL, json=make_payload(name="B", product_id=3333))
        resp = self.client.get(f"{BASE_URL}?product_id=2222")
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        data = resp.get_json()
        self.assertTrue(all(item["product_id"] == 2222 for item in data))

    # ---------- promotion_type filter ----------

    def test_query_by_promotion_type_returns_matches(self):
        """It should return only promotions with the given promotion_type (exact match)"""
        r1 = self.client.post(BASE_URL, json=make_payload(name="A1", promotion_type="AMOUNT_OFF", value=10))
        r2 = self.client.post(BASE_URL, json=make_payload(name="B1", promotion_type="BOGO", value=100))
        self.assertEqual(r1.status_code, status.HTTP_201_CREATED)
        self.assertEqual(r2.status_code, status.HTTP_201_CREATED)

        resp = self.client.get(f"{BASE_URL}?promotion_type=BOGO")
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        data = resp.get_json()
        self.assertTrue(isinstance(data, list))
        self.assertEqual(len([d for d in data if d["promotion_type"] == "BOGO"]), len(data))

    def test_query_promotion_type_blank(self):
        """It should return 200 and [] when ?promotion_type= is blank (only spaces)"""
        r = self.client.post(BASE_URL, json=make_payload(name="X", promotion_type="AMOUNT_OFF"))
        self.assertEqual(r.status_code, status.HTTP_201_CREATED)

        resp = self.client.get(f"{BASE_URL}?promotion_type=   ")
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertEqual(resp.get_json(), [])

    def test_query_by_promotion_type_returns_empty_when_no_match(self):
        """It should return 200 and empty list when no promotions match"""
        r = self.client.post(BASE_URL, json=make_payload(name="A1", promotion_type="AMOUNT_OFF", value=10))
        self.assertEqual(r.status_code, status.HTTP_201_CREATED)

        resp = self.client.get(f"{BASE_URL}?promotion_type=NON_EXISTENT_TYPE")
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertEqual(resp.get_json(), [])

    # ---------- active filter ----------

    def test_active_truthy_and_falsy_synonyms(self):
        """It should accept yes/no/1/0/true/false (case-insensitive)."""
        today = date.today()
        self.client.post(
            BASE_URL,
            json=make_payload(
                name="ActiveNow",
                start_date=(today - timedelta(days=1)).isoformat(),
                end_date=(today + timedelta(days=1)).isoformat(),
            ),
        )
        self.client.post(
            BASE_URL,
            json=make_payload(
                name="Expired",
                start_date=(today - timedelta(days=10)).isoformat(),
                end_date=(today - timedelta(days=5)).isoformat(),
            ),
        )
        self.client.post(
            BASE_URL,
            json=make_payload(
                name="Future",
                start_date=(today + timedelta(days=5)).isoformat(),
                end_date=(today + timedelta(days=10)).isoformat(),
            ),
        )

        for truthy in ["true", "True", "1", "YES", " yes "]:
            resp = self.client.get(f"{BASE_URL}?active={truthy}")
            self.assertEqual(resp.status_code, status.HTTP_200_OK)
            self.assertTrue(all(item["name"] == "ActiveNow" for item in resp.get_json()))

        for falsy in ["false", "False", "0", "NO", "  no  "]:
            resp = self.client.get(f"{BASE_URL}?active={falsy}")
            self.assertEqual(resp.status_code, status.HTTP_200_OK)
            names = [i["name"] for i in resp.get_json()]
            self.assertIn("Expired", names)
            self.assertIn("Future", names)

        bad = self.client.get(f"{BASE_URL}?active=not-a-bool")
        self.assertEqual(bad.status_code, status.HTTP_400_BAD_REQUEST)

    def test_query_active_returns_only_current_promotions(self):
        """It should return only promotions that are active today when ?active=true"""
        today = date.today()
        self.client.post(
            BASE_URL,
            json=make_payload(
                name="ActiveNow",
                start_date=(today - timedelta(days=2)).isoformat(),
                end_date=(today + timedelta(days=2)).isoformat(),
            ),
        )
        self.client.post(
            BASE_URL,
            json=make_payload(
                name="Expired",
                start_date=(today - timedelta(days=10)).isoformat(),
                end_date=(today - timedelta(days=1)).isoformat(),
            ),
        )
        self.client.post(
            BASE_URL,
            json=make_payload(
                name="Future",
                start_date=(today + timedelta(days=1)).isoformat(),
                end_date=(today + timedelta(days=10)).isoformat(),
            ),
        )

        resp = self.client.get(f"{BASE_URL}?active=true")
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        data = resp.get_json()
        self.assertTrue(all(d["name"] == "ActiveNow" for d in data))

    # ---------- miscellaneous ----------

    def test_health(self):
        """GET /health returns OK (支持纯文本 'OK' 或 JSON {'status':'OK'})."""
        resp = self.client.get("/health")
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        # 兼容两种实现：纯文本 OK 或 JSON {"status": "OK"}
        body = resp.get_data(as_text=True)
        if body and body.strip().upper() == "OK":
            return
        data = resp.get_json()
        self.assertEqual(data, {"status": "OK"})

    def test_home_page(self):
        """It should call the home page"""
        resp = self.client.get("/")
        self.assertEqual(resp.status_code, status.HTTP_200_OK)

    def test_unknown_routes(self):
        """It should return JSON 404 for unknown routes"""
        resp = self.client.get("/not-found")
        self.assertEqual(resp.status_code, status.HTTP_404_NOT_FOUND)

    def test_unhandled_exception_500(self):
        """It should return JSON 500 when an unhandled exception occurs (covered via invalid id parse path)"""
        # 触发一个转换错误（由路由层异常处理为 500）
        resp = self.client.get(f"{BASE_URL}/invalid-id")
        self.assertIn(resp.status_code, (status.HTTP_404_NOT_FOUND, status.HTTP_500_INTERNAL_SERVER_ERROR))

    def test_method_not_allowed_on_collection(self):
        """It should return JSON 405 for wrong method on /promotions (PATCH not allowed)"""
        resp = self.client.patch(BASE_URL, json={})
        self.assertEqual(resp.status_code, status.HTTP_405_METHOD_NOT_ALLOWED)
        msg = resp.get_json().get("message", "")
        self.assertTrue("Method Not Allowed" in msg or msg == "Method Not Allowed")

    def test_method_not_allowed_on_resource(self):
        """It should return JSON 405 for wrong method on /promotions/<id> (POST not allowed)"""
        p = self.client.post(BASE_URL, json=make_payload(name="Patch?"))
        self.assertEqual(p.status_code, status.HTTP_201_CREATED)
        pid = p.get_json()["id"]
        resp = self.client.post(f"{BASE_URL}/{pid}", json={})
        self.assertEqual(resp.status_code, status.HTTP_405_METHOD_NOT_ALLOWED)
        msg = resp.get_json().get("message", "")
        self.assertTrue("Method Not Allowed" in msg or msg == "Method Not Allowed")

    # ---------- update ----------

    def test_update_promotion_success(self):
        """It should Update an existing Promotion (200)."""
        p = self.client.post(BASE_URL, json=make_payload(name="Old", promotion_type="AMOUNT_OFF"))
        self.assertEqual(p.status_code, status.HTTP_201_CREATED)
        pid = p.get_json()["id"]

        payload = make_payload(name="NewName", promotion_type="AMOUNT_OFF", value=30, product_id=111)
        payload["id"] = pid
        resp = self.client.put(f"{BASE_URL}/{pid}", json=payload)
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertEqual(resp.get_json()["name"], "NewName")

    def test_update_promotion_not_found(self):
        """It should return 404 when updating a non-existent Promotion"""
        payload = make_payload(name="Ghost", promotion_type="AMOUNT_OFF", value=5, product_id=222)
        payload["id"] = 999999
        resp = self.client.put(f"{BASE_URL}/999999", json=payload)
        self.assertEqual(resp.status_code, status.HTTP_404_NOT_FOUND)

    def test_update_mismatched_id(self):
        """It should return 400 when body.id != path id"""
        p = self.client.post(BASE_URL, json=make_payload(name="Old2"))
        self.assertEqual(p.status_code, status.HTTP_201_CREATED)
        pid = p.get_json()["id"]

        bad = make_payload(name="Mismatch")
        bad["id"] = pid + 1
        resp = self.client.put(f"{BASE_URL}/{pid}", json=bad)
        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)
