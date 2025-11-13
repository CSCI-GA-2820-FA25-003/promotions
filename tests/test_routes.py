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
from unittest.mock import patch

from wsgi import app
from service.models import Promotion, db, DataValidationError
from service.common import status

BASE_URL = "/promotions"


def make_payload(**overrides) -> dict:
    """Build a valid promotion JSON payload"""
    base = {
        "name": "Black Friday Sale",
        "promotion_type": "BOGO",
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
        self.assertTrue(b"Promotions Manager v2" in resp.data)
        content_type = resp.headers.get("Content-Type")
        self.assertIn("text/html", content_type)

    def test_health_check(self):
        """It should return health status"""
        resp = self.client.get("/health")
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        data = resp.get_json()
        self.assertEqual(data["status"], "OK")

    # ---------- Read ----------
    def test_get_promotion(self):
        """It should Get a single promotion"""
        promo = self.client.post(BASE_URL, json=make_payload(name="GetTest"))
        self.assertEqual(promo.status_code, status.HTTP_201_CREATED)
        promotion_id = promo.get_json()["id"]
        resp = self.client.get(f"{BASE_URL}/{promotion_id}")
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        data = resp.get_json()
        self.assertEqual(data["name"], "GetTest")

    def test_get_promotion_not_found(self):
        """It should return 404 when promotion not found"""
        resp = self.client.get(f"{BASE_URL}/999999")
        self.assertEqual(resp.status_code, status.HTTP_404_NOT_FOUND)

    # ---------- Create ----------
    def test_create_promotion(self):
        """It should Create a new Promotion"""
        resp = self.client.post(BASE_URL, json=make_payload(name="CreateMe"))
        self.assertEqual(resp.status_code, status.HTTP_201_CREATED)
        data = resp.get_json()
        self.assertEqual(data["name"], "CreateMe")

    def test_create_promotion_invalid_value(self):
        """It should not create a promotion with invalid value"""
        payload = make_payload(value=-10)
        resp = self.client.post(BASE_URL, json=payload)
        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)

    def test_create_promotion_invalid_type(self):
        """It should not create a promotion with invalid type"""
        payload = make_payload(promotion_type="INVALID_TYPE")
        resp = self.client.post(BASE_URL, json=payload)
        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)

    def test_create_promotion_bad_product_id(self):
        """It should not create a promotion with bad product id"""
        payload = make_payload(product_id=0)
        resp = self.client.post(BASE_URL, json=payload)
        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)

    def test_update_promotion_bad_data(self):
        """It should not update a promotion with bad data"""
        # create a promotion
        payload = make_payload()
        resp = self.client.post(BASE_URL, json=payload)
        self.assertEqual(resp.status_code, status.HTTP_201_CREATED)
        data = resp.get_json()
        pid = data["id"]

        # update the promotion with bad data
        payload["promotion_type"] = "INVALID_TYPE"
        resp = self.client.put(f"{BASE_URL}/{pid}", json=payload)
        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)

    @patch("service.models.Promotion.update")
    def test_deactivate_update_fails(self, mock_update):
        """It should not deactivate a promotion if update fails"""
        mock_update.side_effect = DataValidationError("Update failed")
        # create a promotion
        payload = make_payload()
        resp = self.client.post(BASE_URL, json=payload)
        self.assertEqual(resp.status_code, status.HTTP_201_CREATED)
        data = resp.get_json()
        pid = data["id"]

        resp = self.client.put(f"{BASE_URL}/{pid}/deactivate")
        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)

    def test_create_wrong_content_type(self):
        """It should not create a promotion with wrong content type"""
        resp = self.client.post(BASE_URL, data="{}", content_type="text/html")
        self.assertEqual(resp.status_code, status.HTTP_415_UNSUPPORTED_MEDIA_TYPE)

    @patch("service.models.Promotion.deserialize")
    def test_create_promotion_deserialize_error(self, mock_deserialize):
        """It should not create a promotion if deserialize fails"""
        mock_deserialize.side_effect = DataValidationError("Deserialize error")
        payload = make_payload()
        resp = self.client.post(BASE_URL, json=payload)
        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)

    def test_delete_promotion(self):
        """It should delete an existing Promotion and return 204"""
        r = self.client.post(BASE_URL, json=make_payload(name="DelMe"))
        self.assertEqual(r.status_code, status.HTTP_201_CREATED)
        pid = r.get_json()["id"]
        resp = self.client.delete(f"{BASE_URL}/{pid}")
        self.assertEqual(resp.status_code, status.HTTP_204_NO_CONTENT)

    def test_delete_promotion_not_found(self):
        """It should not Delete a promotion that does not exist"""
        resp = self.client.delete(f"{BASE_URL}/0")
        self.assertEqual(resp.status_code, status.HTTP_404_NOT_FOUND)

    def test_deactivate_promotion_not_found(self):
        """It should not Deactivate a promotion that does not exist"""
        resp = self.client.put(f"{BASE_URL}/0/deactivate")
        self.assertEqual(resp.status_code, status.HTTP_404_NOT_FOUND)

    def test_deactivate_already_inactive_promotion(self):
        """It should not change an already inactive promotion"""
        today = date.today()
        payload = make_payload(
            name="Inactive",
            start_date=(today - timedelta(days=10)).isoformat(),
            end_date=(today - timedelta(days=5)).isoformat(),
        )
        created = self.client.post(BASE_URL, json=payload)
        self.assertEqual(created.status_code, status.HTTP_201_CREATED)
        pid = created.get_json()["id"]

        resp = self.client.put(f"{BASE_URL}/{pid}/deactivate")
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertEqual(resp.get_json()["end_date"], (today - timedelta(days=5)).isoformat())

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

    def test_list_promotions_bad_query_param(self):
        """It should return a 400 error for bad query parameters"""
        resp = self.client.get(BASE_URL, query_string="product_id=foo")
        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)

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
        r1 = self.client.post(BASE_URL, json=make_payload(name="A1", promotion_type="DISCOUNT", value=10))
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
        r = self.client.post(BASE_URL, json=make_payload(name="X", promotion_type="DISCOUNT"))
        self.assertEqual(r.status_code, status.HTTP_201_CREATED)

        resp = self.client.get(f"{BASE_URL}?promotion_type=   ")
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertEqual(resp.get_json(), [])

    def test_query_by_promotion_type_returns_empty_when_no_match(self):
        """It should return 200 and empty list when no promotions match"""
        r = self.client.post(BASE_URL, json=make_payload(name="A1", promotion_type="DISCOUNT", value=10))
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

    def test_active_invalid_value(self):
        """It should return 400 for invalid active parameter"""
        resp = self.client.get(f"{BASE_URL}?active=invalid")
        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)

    def test_update_promotion(self):
        """It should Update an existing Promotion"""
        # create one
        payload = {
            "name": "Promo A",
            "promotion_type": "BOGO",
            "value": 10,
            "product_id": 111,
            "start_date": "2025-10-01",
            "end_date": "2025-10-31",
        }
        created = self.client.post("/promotions", json=payload)
        self.assertEqual(created.status_code, 201)
        pid = created.get_json()["id"]

        # update it
        payload["name"] = "Member Exclusive"
        resp = self.client.put(f"/promotions/{pid}", json=payload)
        self.assertEqual(resp.status_code, 200)
        body = resp.get_json()
        self.assertEqual(body["name"], "Member Exclusive")

    def test_update_promotion_not_found(self):
        """It should not Update a promotion that does not exist"""
        payload = make_payload()
        resp = self.client.put(f"{BASE_URL}/0", json=payload)
        self.assertEqual(resp.status_code, status.HTTP_404_NOT_FOUND)

    def test_update_promotion_id_mismatch_returns_400(self):
        """It should return 400 when body.id != path id"""
        created = self.client.post("/promotions", json={
            "name": "Summer Clearance", "promotion_type": "BOGO", "value": 1, "product_id": 9,
            "start_date": "2025-08-15", "end_date": "2025-08-31",
        })
        self.assertEqual(created.status_code, 201)
        pid = created.get_json()["id"]

        payload = {
            "id": pid + 1,  # mismatch on purpose
            "name": "Summer Clearance", "promotion_type": "BOGO", "value": 1, "product_id": 9,
            "start_date": "2025-08-15", "end_date": "2025-08-31",
        }
        resp = self.client.put(f"/promotions/{pid}", json=payload)
        self.assertEqual(resp.status_code, 400)

    def test_internal_server_error_returns_json(self):
        """It should return JSON 500 when an unhandled exception occurs"""
        # In testing mode Flask propagates exceptions; disable propagation for this test
        prev = app.config.get("PROPAGATE_EXCEPTIONS", None)
        app.config["PROPAGATE_EXCEPTIONS"] = False
        try:
            with patch("service.routes.Promotion.find", side_effect=Exception("boom")):
                resp = self.client.get("/promotions/1")
            self.assertEqual(resp.status_code, 500)
            data = resp.get_json()
            self.assertIsInstance(data, dict)
        finally:
            # restore previous config
            if prev is None:
                app.config.pop("PROPAGATE_EXCEPTIONS", None)
            else:
                app.config["PROPAGATE_EXCEPTIONS"] = prev
