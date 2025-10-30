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
Route tests for the Promotions Service
"""

import unittest
from datetime import date, timedelta

from wsgi import app
from service.common import status

BASE_URL = "/promotions"


def make_payload(**overrides) -> dict:
    """Build a valid promotion JSON payload"""
    base = {
        "name": "NYU Demo",
        "promotion_type": "AMOUNT_OFF",  # use an allowed type
        "value": 10,
        "product_id": 123,
        "start_date": "2025-10-01",
        "end_date": "2025-10-31",
    }
    base.update(overrides)
    return base


class TestPromotionService(unittest.TestCase):
    """Route tests grouped by feature"""

    @classmethod
    def setUpClass(cls):
        app.config["TESTING"] = True
        app.config["DEBUG"] = False

    def setUp(self):
        self.client = app.test_client()

    # ---------- basic endpoints ----------

    def test_home(self):
        """It should call the home page"""
        resp = self.client.get("/")
        self.assertEqual(resp.status_code, status.HTTP_200_OK)

    def test_health(self):
        """GET /health returns OK"""
        resp = self.client.get("/health")
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertEqual(resp.get_json(), {"status": "OK"})

    # ---------- create / delete ----------

    def test_create_promotion(self):
        """It should Create a new Promotion"""
        resp = self.client.post(BASE_URL, json=make_payload(name="First"))
        self.assertEqual(resp.status_code, status.HTTP_201_CREATED)
        data = resp.get_json()
        self.assertEqual(data["name"], "First")
        self.assertIn("id", data)

    def test_delete_promotion(self):
        """It should delete an existing Promotion and return 204"""
        created = self.client.post(BASE_URL, json=make_payload(name="ToDelete"))
        pid = created.get_json()["id"]
        resp = self.client.delete(f"{BASE_URL}/{pid}")
        self.assertEqual(resp.status_code, status.HTTP_204_NO_CONTENT)

    # ---------- filters: id / name / product_id / type ----------

    def test_filter_by_id(self):
        """It should filter by ?id= returning [one] or []"""
        created = self.client.post(BASE_URL, json=make_payload(name="OnlyOne"))
        pid = created.get_json()["id"]

        resp = self.client.get(f"{BASE_URL}?id={pid}")
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        data = resp.get_json()
        self.assertEqual(len(data), 1)
        self.assertEqual(data[0]["id"], pid)

        resp2 = self.client.get(f"{BASE_URL}?id=999999")
        self.assertEqual(resp2.status_code, status.HTTP_200_OK)
        self.assertEqual(resp2.get_json(), [])

    def test_filter_by_name(self):
        """It should filter promotions by ?name="""
        self.client.post(BASE_URL, json=make_payload(name="A"))
        self.client.post(BASE_URL, json=make_payload(name="B"))
        resp = self.client.get(f"{BASE_URL}?name=A")
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        data = resp.get_json()
        self.assertTrue(all(p["name"] == "A" for p in data))

    def test_list_promotions_filter_by_product_id(self):
        """It should filter promotions by ?product_id="""
        self.client.post(BASE_URL, json=make_payload(name="A", product_id=2222))
        self.client.post(BASE_URL, json=make_payload(name="B", product_id=3333))
        resp = self.client.get(f"{BASE_URL}?product_id=2222")
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        data = resp.get_json()
        self.assertTrue(len(data) >= 1)
        self.assertTrue(all(p["product_id"] == 2222 for p in data))

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
        self.assertEqual(len(data), 1)
        self.assertEqual(data[0]["promotion_type"], "BOGO")
        self.assertEqual(data[0]["name"], "B1")

    def test_query_by_promotion_type_returns_empty_when_no_match(self):
        """It should return 200 and empty list when no promotions match"""
        r = self.client.post(BASE_URL, json=make_payload(name="A1", promotion_type="AMOUNT_OFF", value=10))
        self.assertEqual(r.status_code, status.HTTP_201_CREATED)
        resp = self.client.get(f"{BASE_URL}?promotion_type=NON_EXISTENT_TYPE")
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertEqual(resp.get_json(), [])

    def test_query_promotion_type_blank(self):
        """It should return 200 and [] when ?promotion_type= is blank (only spaces)"""
        r = self.client.post(BASE_URL, json=make_payload(name="X", promotion_type="AMOUNT_OFF"))
        self.assertEqual(r.status_code, status.HTTP_201_CREATED)
        resp = self.client.get(f"{BASE_URL}?promotion_type=   ")
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertEqual(resp.get_json(), [])

    # ---------- active filter (strict bool parsing) ----------

    def test_invalid_active_values_400(self):
        """It should return 400 for invalid ?active= values"""
        resp = self.client.get(f"{BASE_URL}?active=maybe")
        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)

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
            self.assertTrue(all(p["start_date"] <= today.isoformat() <= p["end_date"] for p in data))

        for falsy in ["false", "False", "0", "NO", " no "]:
            resp = self.client.get(f"{BASE_URL}?active={falsy}")
            self.assertEqual(resp.status_code, status.HTTP_200_OK)
            data = resp.get_json()
            self.assertTrue(all(not (p["start_date"] <= today.isoformat() <= p["end_date"]) for p in data))

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
        self.assertTrue(all(p["start_date"] <= today.isoformat() <= p["end_date"] for p in data))

    def test_query_active_false_returns_only_inactive(self):
        """It should return only promotions NOT active today when ?active=false"""
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
        resp = self.client.get(f"{BASE_URL}?active=false")
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        data = resp.get_json()
        self.assertTrue(all(not (p["start_date"] <= today.isoformat() <= p["end_date"]) for p in data))

    # ---------- method / error handling ----------

    def test_method_not_allowed_promotions(self):
        """It should return JSON 405 for wrong method on /promotions (PATCH not allowed)"""
        resp = self.client.patch(BASE_URL, json={})
        self.assertEqual(resp.status_code, status.HTTP_405_METHOD_NOT_ALLOWED)

    def test_method_not_allowed_promotions_id(self):
        """It should return JSON 405 for wrong method on /promotions/<id> (POST not allowed)"""
        created = self.client.post(BASE_URL, json=make_payload(name="WrongMethod"))
        pid = created.get_json()["id"]
        resp = self.client.post(f"{BASE_URL}/{pid}", json={})
        self.assertEqual(resp.status_code, status.HTTP_405_METHOD_NOT_ALLOWED)

    def test_unknown_route_404(self):
        """It should return JSON 404 for unknown routes"""
        resp = self.client.get("/not-a-route")
        self.assertEqual(resp.status_code, status.HTTP_404_NOT_FOUND)

    def test_unhandled_exception_500(self):
        """It should return JSON 500 when an unhandled exception occurs"""
        resp = self.client.get(f"{BASE_URL}?active=__force_500__")
        self.assertIn(resp.status_code, (status.HTTP_500_INTERNAL_SERVER_ERROR, status.HTTP_400_BAD_REQUEST))


# ---------- function-style tests (keep class method count reasonable) ----------

def test_update_promotion_success():
    """It should Update an existing Promotion (200)"""
    client = app.test_client()
    created = client.post(BASE_URL, json=make_payload(name="Promo A", promotion_type="AMOUNT_OFF"))
    assert created.status_code == status.HTTP_201_CREATED
    pid = created.get_json()["id"]

    update = client.put(
        f"{BASE_URL}/{pid}",
        json=make_payload(name="Updated", promotion_type="AMOUNT_OFF", value=20),
    )
    assert update.status_code == status.HTTP_200_OK
    assert update.get_json()["name"] == "Updated"


def test_update_promotion_not_found():
    """It should return 404 when updating a non-existent Promotion"""
    client = app.test_client()
    resp = client.put(
        f"{BASE_URL}/999999",
        json=make_payload(name="Ghost", promotion_type="AMOUNT_OFF"),
    )
    assert resp.status_code == status.HTTP_404_NOT_FOUND


def test_update_promotion_id_mismatch_returns_400():
    """It should return 400 when body.id != path id"""
    client = app.test_client()
    created = client.post(BASE_URL, json=make_payload(name="Mismatch", promotion_type="AMOUNT_OFF"))
    assert created.status_code == status.HTTP_201_CREATED
    pid = created.get_json()["id"]

    bad = make_payload(name="Mismatch", promotion_type="AMOUNT_OFF")
    bad["id"] = pid + 1
    resp = client.put(f"{BASE_URL}/{pid}", json=bad)
    assert resp.status_code == status.HTTP_400_BAD_REQUEST


def test_list_promotions_all_returns_list():
    """It should list all promotions when no query params are given"""
    client = app.test_client()

    a = make_payload(name="ListA", promotion_type="AMOUNT_OFF", value=1, product_id=1)
    b = make_payload(name="ListB", promotion_type="AMOUNT_OFF", value=2, product_id=2)

    ra = client.post(BASE_URL, json=a)
    rb = client.post(BASE_URL, json=b)
    assert ra.status_code == status.HTTP_201_CREATED
    assert rb.status_code == status.HTTP_201_CREATED

    resp = client.get(BASE_URL)
    assert resp.status_code == status.HTTP_200_OK
    data = resp.get_json()
    assert isinstance(data, list)
    assert len(data) >= 2
