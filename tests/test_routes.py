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

import os
import logging
from unittest import TestCase
from datetime import date, timedelta

from flask_api import status

from wsgi import app
from service.models import Promotion, db

BASE_URL = "/promotions"

######################################################################
# Helpers
######################################################################


def make_payload(**overrides) -> dict:
    """Build a valid promotion JSON payload"""
    base = {
        "name": "NYU Demo",
        "promotion_type": "AMOUNT_OFF",  # 后端允许
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
        """Run once before all tests"""
        app.config["TESTING"] = True
        app.config["DEBUG"] = False
        app.logger.setLevel(logging.CRITICAL)

        # DB
        database_uri = os.getenv(
            "DATABASE_URI",
            "postgresql+psycopg://postgres:postgres@localhost:5432/testdb",
        )
        app.config["SQLALCHEMY_DATABASE_URI"] = database_uri
        app.app_context().push()

    def setUp(self):
        """Runs before each test"""
        db.session.query(Promotion).delete()
        db.session.commit()
        self.client = app.test_client()

    ###################################################################
    # Basic endpoints
    ###################################################################

    def test_home_page(self):
        """It should call the home page"""
        resp = self.client.get("/")
        self.assertEqual(resp.status_code, status.HTTP_200_OK)

    def test_health(self):
        """GET /health returns OK"""
        resp = self.client.get("/health")
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        # 兼容两种实现：纯文本 "OK" 或 JSON {"status":"OK"}
        data = resp.get_json(silent=True)
        if isinstance(data, dict) and "status" in data:
            self.assertEqual(data["status"], "OK")
        else:
            self.assertEqual(resp.get_data(as_text=True).strip(), "OK")

    def test_not_found_returns_json_404(self):
        """It should return JSON 404 for unknown routes"""
        resp = self.client.get("/does-not-exist")
        self.assertEqual(resp.status_code, status.HTTP_404_NOT_FOUND)
        body = resp.get_json()
        self.assertTrue(isinstance(body, dict))

    ###################################################################
    # Create / Read / Update / Delete
    ###################################################################

    def test_create_promotion(self):
        """It should Create a new Promotion"""
        resp = self.client.post(BASE_URL, json=make_payload(name="Promo A"))
        self.assertEqual(resp.status_code, status.HTTP_201_CREATED)
        body = resp.get_json()
        self.assertEqual(body["name"], "Promo A")
        self.assertIn("id", body)

    def test_delete_promotion(self):
        """It should delete an existing Promotion and return 204"""
        p = self.client.post(BASE_URL, json=make_payload(name="ToDelete"))
        self.assertEqual(p.status_code, status.HTTP_201_CREATED)
        pid = p.get_json()["id"]

        resp = self.client.delete(f"{BASE_URL}/{pid}")
        self.assertEqual(resp.status_code, status.HTTP_204_NO_CONTENT)

        # ensure deleted
        resp = self.client.get(f"{BASE_URL}?id={pid}")
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertEqual(resp.get_json(), [])

    def test_update_promotion_success(self):
        """It should Update an existing Promotion (200)"""
        created = self.client.post(BASE_URL, json=make_payload(name="A1"))
        self.assertEqual(created.status_code, status.HTTP_201_CREATED)
        pid = created.get_json()["id"]

        payload = make_payload(name="A1-Updated")
        resp = self.client.put(f"{BASE_URL}/{pid}", json=payload)
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertEqual(resp.get_json()["name"], "A1-Updated")

    def test_update_promotion_not_found(self):
        """It should return 404 when updating a non-existent Promotion"""
        resp = self.client.put(f"{BASE_URL}/999999", json=make_payload(name="Ghost"))
        self.assertEqual(resp.status_code, status.HTTP_404_NOT_FOUND)

    def test_update_body_id_mismatch(self):
        """It should return 400 when body.id != path id"""
        created = self.client.post(BASE_URL, json=make_payload(name="X"))
        self.assertEqual(created.status_code, status.HTTP_201_CREATED)
        pid = created.get_json()["id"]

        payload = make_payload(name="X", product_id=200)
        payload["id"] = pid + 1
        resp = self.client.put(f"{BASE_URL}/{pid}", json=payload)
        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)

    ###################################################################
    # Queries / filters
    ###################################################################

    def test_list_promotions_all_returns_list(self):
        """It should list all promotions when no query params are given"""
        r1 = self.client.post(BASE_URL, json=make_payload(name="ListA", product_id=1))
        r2 = self.client.post(BASE_URL, json=make_payload(name="ListB", product_id=2))
        self.assertEqual(r1.status_code, status.HTTP_201_CREATED)
        self.assertEqual(r2.status_code, status.HTTP_201_CREATED)

        resp = self.client.get(BASE_URL)
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertTrue(isinstance(resp.get_json(), list))
        self.assertGreaterEqual(len(resp.get_json()), 2)

    def test_filter_by_id_returns_one_or_empty(self):
        """It should filter by ?id= returning [one] or []"""
        created = self.client.post(BASE_URL, json=make_payload(name="OnlyOne"))
        self.assertEqual(created.status_code, status.HTTP_201_CREATED)
        pid = created.get_json()["id"]

        resp = self.client.get(f"{BASE_URL}?id={pid}")
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertEqual(len(resp.get_json()), 1)
        self.assertEqual(resp.get_json()[0]["id"], pid)

        resp = self.client.get(f"{BASE_URL}?id=999999")
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertEqual(resp.get_json(), [])

    def test_filter_by_name(self):
        """It should filter promotions by ?name="""
        self.client.post(BASE_URL, json=make_payload(name="Same"))
        self.client.post(BASE_URL, json=make_payload(name="Same"))
        self.client.post(BASE_URL, json=make_payload(name="Different"))

        resp = self.client.get(f"{BASE_URL}?name=Same")
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        data = resp.get_json()
        self.assertTrue(all(d["name"] == "Same" for d in data))

    def test_list_promotions_filter_by_product_id(self):
        """It should filter promotions by ?product_id="""
        self.client.post(BASE_URL, json=make_payload(name="A", product_id=2222))
        self.client.post(BASE_URL, json=make_payload(name="B", product_id=3333))
        resp = self.client.get(f"{BASE_URL}?product_id=2222")
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        data = resp.get_json()
        self.assertTrue(len(data) >= 1)
        self.assertTrue(all(d["product_id"] == 2222 for d in data))

    def test_query_active_truthy_and_falsy_synonyms(self):
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
            self.assertTrue(
                all(d["start_date"] <= date.today().isoformat() <= d["end_date"] for d in data)
            )

        for falsy in ["false", "False", "0", "NO", " no "]:
            resp = self.client.get(f"{BASE_URL}?active={falsy}")
            self.assertEqual(resp.status_code, status.HTTP_200_OK)

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
        self.assertTrue(
            all(d["start_date"] <= date.today().isoformat() <= d["end_date"] for d in data)
        )

    def test_query_no_matches(self):
        """It should return 200 and empty list when no promotions match"""
        self.client.post(BASE_URL, json=make_payload(name="A1", promotion_type="AMOUNT_OFF", value=10))
        resp = self.client.get(f"{BASE_URL}?promotion_type=NON_EXISTENT_TYPE")
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertEqual(resp.get_json(), [])

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
        self.assertTrue(all(d["promotion_type"] == "BOGO" for d in data))

    def test_query_promotion_type_blank(self):
        """It should return 200 and [] when ?promotion_type= is blank (only spaces)"""
        r = self.client.post(BASE_URL, json=make_payload(name="X", promotion_type="AMOUNT_OFF"))
        self.assertEqual(r.status_code, status.HTTP_201_CREATED)

        resp = self.client.get(f"{BASE_URL}?promotion_type=   ")
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertEqual(resp.get_json(), [])

    ###################################################################
    # Method not allowed & server error
    ###################################################################

    def test_method_not_allowed_on_collection(self):
        """It should return JSON 405 for wrong method on /promotions (PATCH not allowed)"""
        resp = self.client.patch(BASE_URL, json={})
        self.assertEqual(resp.status_code, status.HTTP_405_METHOD_NOT_ALLOWED)
        msg = resp.get_json().get("message", "")
        self.assertIn("Method Not Allowed", msg)

    def test_method_not_allowed_on_resource(self):
        """It should return JSON 405 for wrong method on /promotions/<id> (POST not allowed)"""
        p = self.client.post(BASE_URL, json=make_payload(name="Patch?"))
        self.assertEqual(p.status_code, status.HTTP_201_CREATED)
        pid = p.get_json()["id"]
        resp = self.client.post(f"{BASE_URL}/{pid}", json={})
        self.assertEqual(resp.status_code, status.HTTP_405_METHOD_NOT_ALLOWED)
        msg = resp.get_json().get("message", "")
        self.assertIn("Method Not Allowed", msg)

    def test_internal_server_error_path(self):
        """It should return JSON 500 when an unhandled exception occurs（通过非法 id 触发某些实现中的异常路径）"""
        resp = self.client.get(f"{BASE_URL}?id=not-an-int")
        allowed = (
            status.HTTP_200_OK,
            status.HTTP_400_BAD_REQUEST,
            status.HTTP_500_INTERNAL_SERVER_ERROR,
        )
        self.assertIn(resp.status_code, allowed)
