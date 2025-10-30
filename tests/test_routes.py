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

"""Promotion Service functional tests"""

# pylint: disable=too-many-public-methods

import os
import logging
from unittest import TestCase
from datetime import date, timedelta

from wsgi import app
from service.models import Promotion, db

# ---- Minimal status shim so we don't rely on flask_api in CI/lint ----
class status:  # noqa: N801 (keep existing naming used in tests)
    HTTP_200_OK = 200
    HTTP_201_CREATED = 201
    HTTP_204_NO_CONTENT = 204
    HTTP_400_BAD_REQUEST = 400
    HTTP_404_NOT_FOUND = 404
    HTTP_405_METHOD_NOT_ALLOWED = 405
    HTTP_500_INTERNAL_SERVER_ERROR = 500


BASE_URL = "/promotions"


######################################################################
# Helpers
######################################################################
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


######################################################################
# Base TestCase
######################################################################
class TestPromotionService(TestCase):
    """Promotion Service functional tests"""

    @classmethod
    def setUpClass(cls):
        """Runs once before the entire test suite"""
        DATABASE_URI = os.getenv(
            "DATABASE_URI",
            "postgresql+psycopg://postgres:postgres@localhost:5432/testdb",
        )
        app.config["TESTING"] = True
        app.config["DEBUG"] = False
        app.config["SQLALCHEMY_DATABASE_URI"] = DATABASE_URI
        app.logger.setLevel(logging.CRITICAL)
        app.app_context().push()

    @classmethod
    def tearDownClass(cls):
        """Runs once after the entire test suite"""
        db.session.close()

    def setUp(self):
        """Runs before each test"""
        self.client = app.test_client()
        db.session.query(Promotion).delete()
        db.session.commit()

    def tearDown(self):
        """Runs after each test"""
        db.session.remove()

    ##################################################################
    # Basic routes
    ##################################################################
    def test_health(self):
        """GET /health returns OK"""
        resp = self.client.get("/health")
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        # 兼容纯文本 "OK" 或 JSON {"status": "OK"}
        data_json = None
        try:
            data_json = resp.get_json(silent=True)
        except Exception:  # pragma: no cover - defensive
            data_json = None
        if data_json is not None and isinstance(data_json, dict):
            self.assertEqual(data_json.get("status"), "OK")
        else:
            self.assertEqual(resp.get_data(as_text=True).strip(), "OK")

    def test_index(self):
        """It should call the home page"""
        resp = self.client.get("/")
        self.assertEqual(resp.status_code, status.HTTP_200_OK)

    def test_not_found(self):
        """Unknown routes return JSON 404"""
        resp = self.client.get("/this-route-does-not-exist")
        self.assertEqual(resp.status_code, status.HTTP_404_NOT_FOUND)

    ##################################################################
    # Create / Read / Update / Delete
    ##################################################################
    def test_create_promotion(self):
        """It should Create a new Promotion"""
        payload = make_payload(name="Create One")
        resp = self.client.post(BASE_URL, json=payload)
        self.assertEqual(resp.status_code, status.HTTP_201_CREATED)
        data = resp.get_json()
        for key in ("id", "name", "promotion_type", "value", "product_id"):
            self.assertIn(key, data)
        self.assertEqual(data["name"], "Create One")

    def test_delete_promotion(self):
        """It should delete an existing Promotion and return 204"""
        r = self.client.post(BASE_URL, json=make_payload(name="Delete Me"))
        self.assertEqual(r.status_code, status.HTTP_201_CREATED)
        pid = r.get_json()["id"]

        resp = self.client.delete(f"{BASE_URL}/{pid}")
        self.assertEqual(resp.status_code, status.HTTP_204_NO_CONTENT)

        check = self.client.get(f"{BASE_URL}?id={pid}")
        self.assertEqual(check.status_code, status.HTTP_200_OK)
        self.assertEqual(check.get_json(), [])

    def test_update_success(self):
        """It should Update an existing Promotion (200)"""
        r = self.client.post(BASE_URL, json=make_payload(name="A"))
        self.assertEqual(r.status_code, status.HTTP_201_CREATED)
        pid = r.get_json()["id"]

        updated = make_payload(name="A-Updated")
        resp = self.client.put(f"{BASE_URL}/{pid}", json=updated)
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertEqual(resp.get_json()["name"], "A-Updated")

    def test_update_not_found(self):
        """It should return 404 when updating a non-existent Promotion"""
        resp = self.client.put(f"{BASE_URL}/999999", json=make_payload(name="Ghost"))
        self.assertEqual(resp.status_code, status.HTTP_404_NOT_FOUND)

    def test_update_conflict_id(self):
        """It should return 400 when body.id != path id"""
        r = self.client.post(BASE_URL, json=make_payload(name="Patch?"))
        self.assertEqual(r.status_code, status.HTTP_201_CREATED)
        pid = r.get_json()["id"]

        wrong = make_payload(name="Wrong", product_id=999)
        wrong["id"] = pid + 1
        resp = self.client.put(f"{BASE_URL}/{pid}", json=wrong)
        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)

    ##################################################################
    # Filtering & query params
    ##################################################################
    def test_list_all_promotions(self):
        """It should list all promotions when no query params are given"""
        a = self.client.post(BASE_URL, json=make_payload(name="ListA"))
        b = self.client.post(BASE_URL, json=make_payload(name="ListB"))
        self.assertEqual(a.status_code, status.HTTP_201_CREATED)
        self.assertEqual(b.status_code, status.HTTP_201_CREATED)

        resp = self.client.get(BASE_URL)
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        data = resp.get_json()
        self.assertTrue(isinstance(data, list))
        self.assertGreaterEqual(len(data), 2)

    def test_filter_by_id(self):
        """It should filter by ?id= returning [one] or []"""
        r = self.client.post(BASE_URL, json=make_payload(name="One"))
        self.assertEqual(r.status_code, status.HTTP_201_CREATED)
        pid = r.get_json()["id"]

        resp = self.client.get(f"{BASE_URL}?id={pid}")
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        data = resp.get_json()
        self.assertTrue(isinstance(data, list))
        self.assertEqual(len(data), 1)
        self.assertEqual(data[0]["id"], pid)

        resp2 = self.client.get(f"{BASE_URL}?id={pid+999}")
        self.assertEqual(resp2.status_code, status.HTTP_200_OK)
        self.assertEqual(resp2.get_json(), [])

    def test_filter_by_name(self):
        """It should filter promotions by ?name="""
        self.client.post(BASE_URL, json=make_payload(name="Same"))
        self.client.post(BASE_URL, json=make_payload(name="Same"))
        self.client.post(BASE_URL, json=make_payload(name="Diff"))

        resp = self.client.get(f"{BASE_URL}?name=Same")
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        names = [p["name"] for p in resp.get_json()]
        self.assertTrue(all(n == "Same" for n in names))

    def test_list_promotions_filter_by_product_id(self):
        """It should filter promotions by ?product_id="""
        self.client.post(BASE_URL, json=make_payload(name="A", product_id=2222))
        self.client.post(BASE_URL, json=make_payload(name="B", product_id=3333))

        resp = self.client.get(f"{BASE_URL}?product_id=2222")
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        data = resp.get_json()
        self.assertEqual(len(data), 1)
        self.assertEqual(data[0]["product_id"], 2222)

    def test_query_by_promotion_type_returns_matches(self):
        """It should return only promotions with the given promotion_type"""
        r1 = self.client.post(
            BASE_URL, json=make_payload(name="A1", promotion_type="AMOUNT_OFF", value=10)
        )
        r2 = self.client.post(
            BASE_URL, json=make_payload(name="B1", promotion_type="BOGO", value=100)
        )
        self.assertEqual(r1.status_code, status.HTTP_201_CREATED)
        self.assertEqual(r2.status_code, status.HTTP_201_CREATED)

        resp = self.client.get(f"{BASE_URL}?promotion_type=BOGO")
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        data = resp.get_json()
        self.assertTrue(isinstance(data, list))
        # 只应该返回 BOGO 的 B1
        self.assertEqual(len(data), 1)
        self.assertEqual(data[0]["promotion_type"], "BOGO")
        self.assertEqual(data[0]["name"], "B1")

    def test_query_promotion_type_blank(self):
        """It should return 200 and [] when ?promotion_type= is blank (only spaces)"""
        r = self.client.post(BASE_URL, json=make_payload(name="X", promotion_type="AMOUNT_OFF"))
        self.assertEqual(r.status_code, status.HTTP_201_CREATED)

        resp = self.client.get(f"{BASE_URL}?promotion_type=   ")
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertEqual(resp.get_json(), [])

    ##################################################################
    # Active/inactive filters
    ##################################################################
    def test_active_truthy_and_falsy_synonyms(self):
        """It should accept yes/no/1/0/true/false (case-insensitive)"""
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
            data = resp.get_json()
            self.assertTrue(all(isinstance(p, dict) for p in data))
            # 都应是“当前活跃”的那条
            self.assertTrue(all(p["name"] == "ActiveNow" for p in data))

        for falsy in ["false", "False", "0", "NO", " no "]:
            resp = self.client.get(f"{BASE_URL}?active={falsy}")
            self.assertEqual(resp.status_code, status.HTTP_200_OK)
            data = resp.get_json()
            # 不包含“ActiveNow”
            self.assertTrue(all(p["name"] != "ActiveNow" for p in data))

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
        names = [p["name"] for p in resp.get_json()]
        self.assertEqual(names, ["ActiveNow"])

    def test_query_no_match(self):
        """It should return 200 and empty list when no promotions match"""
        self.client.post(BASE_URL, json=make_payload(name="A1", promotion_type="AMOUNT_OFF"))
        resp = self.client.get(f"{BASE_URL}?promotion_type=NON_EXISTENT_TYPE")
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertEqual(resp.get_json(), [])

    ##################################################################
    # Method not allowed
    ##################################################################
    def test_method_not_allowed_on_collection(self):
        """It should return JSON 405 for wrong method on /promotions (PATCH not allowed)"""
        resp = self.client.patch(BASE_URL, json={})
        self.assertEqual(resp.status_code, status.HTTP_405_METHOD_NOT_ALLOWED)
        # message 兼容不同实现（Flask/Werkzeug 可能带前缀）
        msg = resp.get_json().get("message", "")
        self.assertTrue(
            msg == "Method Not Allowed" or msg.startswith("405 Method Not Allowed"),
            msg=msg,
        )

    def test_method_not_allowed_on_resource(self):
        """It should return JSON 405 for wrong method on /promotions/<id> (POST not allowed)"""
        r = self.client.post(BASE_URL, json=make_payload(name="Patch?"))
        self.assertEqual(r.status_code, status.HTTP_201_CREATED)
        pid = r.get_json()["id"]

        resp = self.client.post(f"{BASE_URL}/{pid}", json={})
        self.assertEqual(resp.status_code, status.HTTP_405_METHOD_NOT_ALLOWED)
        msg = resp.get_json().get("message", "")
        self.assertTrue(
            msg == "Method Not Allowed" or msg.startswith("405 Method Not Allowed"),
            msg=msg,
        )
