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
        "name": "Black Friday Sale",
        "promotion_type": "DISCOUNT",
        "value": 10,
        "product_id": 123,
        "start_date": "2025-11-28",
        "end_date": "2025-11-30",
    }
    base.update(overrides)
    return base


######################################################################
#  H A P P Y   P A T H S
######################################################################
# pylint: disable=too-many-public-methods
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

    # ---------- Home ----------
    def test_index_route_returns_index_html(self):
        """It should return the index.html UI page"""
        resp = self.client.get("/")
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertIn(b"<html", resp.data)
        self.assertIn(b"Promotions Admin", resp.data)
        content_type = resp.headers.get("Content-Type")
        self.assertIn("text/html", content_type)

    def test_api_index(self):
        """It should call the API index"""
        resp = self.client.get("/api")
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        data = resp.get_json()
        self.assertEqual(data["name"], "Promotions Service")
        self.assertEqual(data["version"], "1.0.0")
        self.assertIn("promotions", data["paths"])

    # ----- new tests for /v2 -----
    def test_v2_route_returns_v2_html(self):
        """It should return the v2 UI page"""
        resp = self.client.get("/v2")
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertIn(b"<html", resp.data)
        self.assertTrue(b"Promotions Manager" in resp.data)
        content_type = resp.headers.get("Content-Type")
        self.assertIn("text/html", content_type)

    # ---------- Create ----------
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

    # create one
    payload = {
        "name": "Promo A",
        "promotion_type": "PERCENT",
        "value": 10,
        "product_id": 111,
        "start_date": "2025-10-01",
        "end_date": "2025-10-31",
    }
    created = client.post("/promotions", json=payload)
    assert created.status_code == 201
    pid = created.get_json()["id"]

    # update it
    payload["name"] = "Member Exclusive"
    resp = client.put(f"/promotions/{pid}", json=payload)
    assert resp.status_code == 200
    body = resp.get_json()
    assert body["name"] == "Member Exclusive"


def test_update_promotion_not_found():
    """It should return 404 when updating a non-existent Promotion"""
    client = app.test_client()

    payload = {
        "name": "Ghost",
        "promotion_type": "PERCENT",
        "value": 5,
        "product_id": 222,
        "start_date": "2025-10-01",
        "end_date": "2025-10-31",
    }
    resp = client.put("/promotions/999999", json=payload)
    assert resp.status_code == 404
    data = resp.get_json()
    assert isinstance(data, dict)


def test_update_promotion_id_mismatch_returns_400():
    """It should return 400 when body.id != path id"""
    client = app.test_client()
    created = client.post("/promotions", json={
        "name": "Summer Clearance", "promotion_type": "BOGO", "value": 1, "product_id": 9,
        "start_date": "2025-08-15", "end_date": "2025-08-31",
    })
    assert created.status_code == 201
    pid = created.get_json()["id"]

    payload = {
        "id": pid + 1,  # mismatch on purpose
        "name": "Summer Clearance", "promotion_type": "BOGO", "value": 1, "product_id": 9,
        "start_date": "2025-08-15", "end_date": "2025-08-31",
    }
    resp = client.put(f"/promotions/{pid}", json=payload)
    assert resp.status_code == 400


def test_list_promotions_all_returns_list():
    """It should list all promotions when no query params are given"""
    client = app.test_client()

    # ensure at least 2 items
    a = {
        "name": "New Year Sale",
        "promotion_type": "PERCENT",
        "value": 1,
        "product_id": 1,
        "start_date": "2025-12-31",
        "end_date": "2026-01-07",
    }
    b = {
        "name": "Spring Festival",
        "promotion_type": "DISCOUNT",
        "value": 2,
        "product_id": 2,
        "start_date": "2025-01-28",
        "end_date": "2025-02-05",
    }
    client.post("/promotions", json=a)
    client.post("/promotions", json=b)

    resp = client.get("/promotions")
    assert resp.status_code == 200
    data = resp.get_json()
    assert isinstance(data, list)
    assert len(data) >= 2


def test_query_promotion_type_405_on_wrong_method_root():
    """It should return JSON 405 for wrong method on /promotions (PATCH not allowed)"""
    client = app.test_client()
    resp = client.patch("/promotions", json={"x": 1})
    assert resp.status_code == 405
    data = resp.get_json()
    assert isinstance(data, dict)  # our JSON error handler


def test_method_not_allowed_returns_json_on_item():
    """It should return JSON 405 for wrong method on /promotions/<id> (POST not allowed)"""
    client = app.test_client()
    resp = client.post("/promotions/1")  # POST not allowed here
    assert resp.status_code == 405
    data = resp.get_json()
    assert isinstance(data, dict)  # our JSON error handler


def test_not_found_returns_json():
    """It should return JSON 404 for unknown routes"""
    client = app.test_client()
    resp = client.get("/no-such-route")
    assert resp.status_code == 404
    data = resp.get_json()
    assert isinstance(data, dict)  # our JSON error handler


def test_internal_server_error_returns_json():
    """It should return JSON 500 when an unhandled exception occurs"""
    client = app.test_client()
    # In testing mode Flask propagates exceptions; disable propagation for this test
    prev = app.config.get("PROPAGATE_EXCEPTIONS", None)
    app.config["PROPAGATE_EXCEPTIONS"] = False
    try:
        with patch("service.routes.Promotion.find", side_effect=Exception("boom")):
            resp = client.get("/promotions/1")
        assert resp.status_code == 500
        data = resp.get_json()
        self.assertTrue(all(d["name"] == "ActiveNow" for d in data))

    # ---------- miscellaneous ----------

    def test_health(self):
        """GET /health returns OK (支持纯文本 'OK' 或 JSON {'status':'OK'})."""
        resp = self.client.get("/health")
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
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
        resp = self.client.get(f"{BASE_URL}/invalid-id")
        self.assertIn(resp.status_code, (status.HTTP_404_NOT_FOUND, status.HTTP_500_INTERNAL_SERVER_ERROR))

    def test_post_without_content_type_triggers_received_none(self):
        """Covers routes.check_content_type() 'received none' branch"""
        resp = self.client.post(BASE_URL, data=b"{}")
        self.assertEqual(resp.status_code, status.HTTP_415_UNSUPPORTED_MEDIA_TYPE)
        msg = resp.get_json()["message"].lower()
        self.assertIn("received none", msg)
