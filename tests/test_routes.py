######################################################################
# Copyright 2016, 2024 John J. Rofrano
######################################################################

import os
import logging
from datetime import date, timedelta
from unittest import TestCase

from wsgi import app
from service.common import status

######################################################################
#  H E L P E R S
######################################################################

BASE_URL = "/promotions"


def make_payload(**overrides) -> dict:
    """Build a valid promotion JSON payload"""
    base = {
        "name": "NYU Demo",
        "promotion_type": "AMOUNT_OFF",  # ✅ allowed
        "value": 10,
        "product_id": 123,
        "start_date": "2025-10-01",
        "end_date": "2025-10-31",
    }
    base.update(overrides)
    return base


######################################################################
#  T E S T   C A S E S
######################################################################
class TestPromotionService(TestCase):  # pylint: disable=too-many-public-methods
    """Promotion API Server Tests"""

    @classmethod
    def setUpClass(cls):
        app.config["TESTING"] = True
        app.config["DEBUG"] = False
        app.logger.setLevel(logging.CRITICAL)

    def setUp(self):
        self.client = app.test_client()

    ##################################################################
    # CREATE
    ##################################################################
    def test_create_promotion(self):
        """It should Create a new Promotion"""
        resp = self.client.post(BASE_URL, json=make_payload())
        self.assertEqual(resp.status_code, status.HTTP_201_CREATED)
        data = resp.get_json()
        self.assertIn("id", data)
        self.assertEqual(data["promotion_type"], "AMOUNT_OFF")

    ##################################################################
    # LIST & FILTERS
    ##################################################################
    def test_list_all_promotions_when_no_query(self):
        """It should list all promotions when no query params are given"""
        a = make_payload(name="ListA", promotion_type="AMOUNT_OFF", value=1, product_id=1)
        b = make_payload(name="ListB", promotion_type="AMOUNT_OFF", value=2, product_id=2)
        ra = self.client.post(BASE_URL, json=a)
        rb = self.client.post(BASE_URL, json=b)
        self.assertEqual(ra.status_code, status.HTTP_201_CREATED)
        self.assertEqual(rb.status_code, status.HTTP_201_CREATED)

        resp = self.client.get(BASE_URL)
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        data = resp.get_json()
        self.assertTrue(isinstance(data, list))
        self.assertGreaterEqual(len(data), 2)

    def test_filter_by_id_exact(self):
        """It should filter by ?id=... returning [one] or []"""
        created = self.client.post(BASE_URL, json=make_payload(name="IDOne"))
        self.assertEqual(created.status_code, status.HTTP_201_CREATED)
        pid = created.get_json()["id"]

        found = self.client.get(f"{BASE_URL}?id={pid}")
        self.assertEqual(found.status_code, status.HTTP_200_OK)
        body = found.get_json()
        self.assertTrue(isinstance(body, list))
        self.assertEqual(len(body), 1)
        self.assertEqual(body[0]["id"], pid)

    def test_filter_by_name(self):
        """It should filter promotions by ?name=..."""
        self.client.post(BASE_URL, json=make_payload(name="A"))
        self.client.post(BASE_URL, json=make_payload(name="B"))
        resp = self.client.get(f"{BASE_URL}?name=A")
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        data = resp.get_json()
        self.assertTrue(all(p["name"] == "A" for p in data))

    def test_list_promotions_filter_by_product_id(self):
        """It should filter promotions by ?product_id=..."""
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

    ##################################################################
    # ACTIVE TRUE/FALSE
    ##################################################################
    def test_query_active_returns_only_current_promotions(self):
        """It should return only promotions that are active today when ?active=true"""
        today = date.today()
        self.client.post(BASE_URL, json=make_payload(
            name="ActiveNow",
            start_date=(today - timedelta(days=2)).isoformat(),
            end_date=(today + timedelta(days=2)).isoformat(),
        ))
        self.client.post(BASE_URL, json=make_payload(
            name="Expired",
            start_date=(today - timedelta(days=10)).isoformat(),
            end_date=(today - timedelta(days=1)).isoformat(),
        ))
        self.client.post(BASE_URL, json=make_payload(
            name="Future",
            start_date=(today + timedelta(days=1)).isoformat(),
            end_date=(today + timedelta(days=10)).isoformat(),
        ))
        resp = self.client.get(f"{BASE_URL}?active=true")
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        data = resp.get_json()
        self.assertTrue(all(
            (date.fromisoformat(p["start_date"]) <= today <= date.fromisoformat(p["end_date"]))
            for p in data
        ))

    def test_active_truthy_and_falsy_synonyms(self):
        """It should accept yes/no/1/0/true/false (case-insensitive)"""
        today = date.today()
        self.client.post(BASE_URL, json=make_payload(
            name="ActiveNow",
            start_date=(today - timedelta(days=1)).isoformat(),
            end_date=(today + timedelta(days=1)).isoformat(),
        ))
        self.client.post(BASE_URL, json=make_payload(
            name="Expired",
            start_date=(today - timedelta(days=10)).isoformat(),
            end_date=(today - timedelta(days=5)).isoformat(),
        ))
        self.client.post(BASE_URL, json=make_payload(
            name="Future",
            start_date=(today + timedelta(days=5)).isoformat(),
            end_date=(today + timedelta(days=10)).isoformat(),
        ))

        # Truthy -> only active
        for truthy in ["true", "True", "1", "YES", " yes "]:
            resp = self.client.get(f"{BASE_URL}?active={truthy}")
            self.assertEqual(resp.status_code, status.HTTP_200_OK)
            data = resp.get_json()
            self.assertTrue(all(
                (date.fromisoformat(p["start_date"]) <= today <= date.fromisoformat(p["end_date"]))
                for p in data
            ))

        # Falsy -> only NOT active today
        for falsy in ["false", "False", "0", "NO", " no "]:
            resp = self.client.get(f"{BASE_URL}?active={falsy}")
            self.assertEqual(resp.status_code, status.HTTP_200_OK)
            data = resp.get_json()
            self.assertTrue(all(
                (today < date.fromisoformat(p["start_date"])) or (today > date.fromisoformat(p["end_date"]))
                for p in data
            ))

    def test_active_invalid_values(self):
        """It should return 400 for invalid ?active= values"""
        for bad in ["maybe", "y", "t", "2", ""]:
            resp = self.client.get(f"{BASE_URL}?active={bad}")
            self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)

    ##################################################################
    # UPDATE
    ##################################################################
    def test_update_promotion_success(self):
        """It should Update an existing Promotion (200)"""
        created = self.client.post(BASE_URL, json=make_payload(name="Promo A", promotion_type="AMOUNT_OFF"))
        self.assertEqual(created.status_code, status.HTTP_201_CREATED)
        pid = created.get_json()["id"]

        payload = make_payload(name="Updated", promotion_type="AMOUNT_OFF", value=50, product_id=111)
        resp = self.client.put(f"{BASE_URL}/{pid}", json=payload)
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        body = resp.get_json()
        self.assertEqual(body["name"], "Updated")
        self.assertEqual(body["value"], 50)

    def test_update_promotion_not_found(self):
        """It should return 404 when updating a non-existent Promotion"""
        payload = make_payload(name="Ghost", promotion_type="AMOUNT_OFF", value=5, product_id=222)
        resp = self.client.put(f"{BASE_URL}/99999999", json=payload)
        self.assertEqual(resp.status_code, status.HTTP_404_NOT_FOUND)

    def test_update_promotion_id_mismatch_returns_400(self):
        """It should return 400 when body.id != path id"""
        created = self.client.post(BASE_URL, json=make_payload(name="Mismatch", promotion_type="AMOUNT_OFF"))
        self.assertEqual(created.status_code, status.HTTP_201_CREATED)
        pid = created.get_json()["id"]
        payload = make_payload(name="Mismatch", promotion_type="AMOUNT_OFF")
        payload["id"] = pid + 123  # intentionally different
        resp = self.client.put(f"{BASE_URL}/{pid}", json=payload)
        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)

    ##################################################################
    # DELETE
    ##################################################################
    def test_delete_promotion(self):
        """It should delete an existing Promotion and return 204"""
        created = self.client.post(BASE_URL, json=make_payload(name="ToDelete"))
        self.assertEqual(created.status_code, status.HTTP_201_CREATED)
        pid = created.get_json()["id"]
        resp = self.client.delete(f"{BASE_URL}/{pid}")
        self.assertEqual(resp.status_code, status.HTTP_204_NO_CONTENT)
        # deleting again -> 404
        resp2 = self.client.delete(f"{BASE_URL}/{pid}")
        self.assertEqual(resp2.status_code, status.HTTP_404_NOT_FOUND)

    ##################################################################
    # MISC
    ##################################################################
    def test_home_page(self):
        """It should call the home page"""
        resp = self.client.get("/")
        self.assertEqual(resp.status_code, status.HTTP_200_OK)

    def test_method_not_allowed_json(self):
        """It should return JSON 405 for wrong method on /promotions/<id> (POST not allowed)"""
        created = self.client.post(BASE_URL, json=make_payload())
        pid = created.get_json()["id"]
        resp = self.client.post(f"{BASE_URL}/{pid}", json={})
        self.assertEqual(resp.status_code, status.HTTP_405_METHOD_NOT_ALLOWED)

    def test_method_not_allowed_json_collection(self):
        """It should return JSON 405 for wrong method on /promotions (PATCH not allowed)"""
        resp = self.client.patch(BASE_URL, json={})
        self.assertEqual(resp.status_code, status.HTTP_405_METHOD_NOT_ALLOWED)

    def test_unknown_route(self):
        """It should return JSON 404 for unknown routes"""
        resp = self.client.get("/does-not-exist")
        self.assertEqual(resp.status_code, status.HTTP_404_NOT_FOUND)

    def test_health(self):
        """It should return 200 OK with {'status':'OK'} on GET /health"""
        resp = self.client.get("/health")
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertEqual(resp.get_json(), {"status": "OK"})
