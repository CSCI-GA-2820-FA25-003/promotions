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
Promotion API Server Tests
"""

from datetime import date, timedelta

from wsgi import app
from service.common import status
from tests.factories import PromotionFactory

BASE_URL = "/promotions"


def make_payload(**overrides) -> dict:
    """Build a valid promotion JSON payload"""
    base = {
        "name": "NYU Demo",
        "promotion_type": "AMOUNT_OFF",  # ✅ allowed by backend
        "value": 10,
        "product_id": 123,
        "start_date": "2025-10-01",
        "end_date": "2025-10-31",
    }
    base.update(overrides)
    return base


######################################################################
#  P O S T   T E S T S
######################################################################


class TestPromotionService:
    """Promotion API Server Tests"""

    def setup_method(self, _method):
        self.client = app.test_client()

    ##################################################################
    # CREATE
    ##################################################################

    def test_create_promotion(self):
        """It should Create a new Promotion"""
        test_promotion = PromotionFactory()
        resp = self.client.post(BASE_URL, json=test_promotion.serialize())
        self.assert201(resp)
        new_json = resp.get_json()
        self.assertFields(new_json, required=True)

    ##################################################################
    # LIST / QUERY
    ##################################################################

    def test_query_by_promotion_type_returns_matches(self):
        """It should return only promotions with the given promotion_type (exact match)"""
        # Arrange: 一条 AMOUNT_OFF 和一条 BOGO
        r1 = self.client.post(
            BASE_URL, json=make_payload(name="A1", promotion_type="AMOUNT_OFF", value=10)
        )
        r2 = self.client.post(
            BASE_URL, json=make_payload(name="B1", promotion_type="BOGO", value=100)
        )
        assert r1.status_code == status.HTTP_201_CREATED
        assert r2.status_code == status.HTTP_201_CREATED

        # Act: 查 BOGO
        resp = self.client.get(f"{BASE_URL}?promotion_type=BOGO")
        assert resp.status_code == status.HTTP_200_OK
        data = resp.get_json()

        # Assert: 只有 B1
        assert isinstance(data, list)
        assert len(data) == 1
        assert data[0]["promotion_type"] == "BOGO"
        assert data[0]["name"] == "B1"

    def test_query_by_promotion_type_returns_empty_when_no_match(self):
        """It should return 200 and empty list when no promotions match"""
        # Arrange: 存一条 AMOUNT_OFF
        r = self.client.post(
            BASE_URL, json=make_payload(name="A1", promotion_type="AMOUNT_OFF", value=10)
        )
        assert r.status_code == status.HTTP_201_CREATED

        # Act: 查一个不存在的类型
        resp = self.client.get(f"{BASE_URL}?promotion_type=NON_EXISTENT_TYPE")
        assert resp.status_code == status.HTTP_200_OK
        assert resp.get_json() == []

    def test_query_promotion_type_blank(self):
        """It should return 200 and [] when ?promotion_type= is blank (only spaces)"""
        # Arrange: 放一条
        r = self.client.post(
            BASE_URL, json=make_payload(name="X", promotion_type="AMOUNT_OFF")
        )
        assert r.status_code == status.HTTP_201_CREATED

        # Act: blank param (spaces)
        resp = self.client.get(f"{BASE_URL}?promotion_type=   ")
        # Assert
        assert resp.status_code == status.HTTP_200_OK
        assert resp.get_json() == []

    def test_list_promotions_filter_by_product_id(self):
        """It should filter promotions by ?product_id=..."""
        self.client.post(BASE_URL, json=make_payload(name="A", product_id=2222))
        self.client.post(BASE_URL, json=make_payload(name="B", product_id=3333))
        resp = self.client.get(f"{BASE_URL}?product_id=2222")
        assert resp.status_code == status.HTTP_200_OK
        data = resp.get_json()
        assert isinstance(data, list)
        assert len(data) == 1
        assert data[0]["product_id"] == 2222

    def test_filter_by_id_returns_one_or_empty(self):
        """It should filter by ?id=... returning [one] or []"""
        r = self.client.post(BASE_URL, json=make_payload(name="OnlyOne"))
        assert r.status_code == status.HTTP_201_CREATED
        pid = r.get_json()["id"]

        resp = self.client.get(f"{BASE_URL}?id={pid}")
        assert resp.status_code == status.HTTP_200_OK
        data = resp.get_json()
        assert isinstance(data, list) and len(data) == 1 and data[0]["id"] == pid

        resp2 = self.client.get(f"{BASE_URL}?id=999999")
        assert resp2.status_code == status.HTTP_200_OK
        assert resp2.get_json() == []

    def test_list_promotions_all_returns_list(self):
        """It should list all promotions when no query params are given"""
        client = app.test_client()

        # ensure at least 2 items — 使用允许的枚举类型
        a = make_payload(name="ListA", promotion_type="AMOUNT_OFF", value=1, product_id=1)
        b = make_payload(name="ListB", promotion_type="AMOUNT_OFF", value=2, product_id=2)

        ra = client.post("/promotions", json=a)
        rb = client.post("/promotions", json=b)
        assert ra.status_code == 201
        assert rb.status_code == 201

        resp = client.get("/promotions")
        assert resp.status_code == 200
        data = resp.get_json()
        assert isinstance(data, list)
        assert len(data) >= 2

    ##################################################################
    # ACTIVE FILTER
    ##################################################################

    def test_active_query_invalid_values(self):
        """It should return 400 for invalid ?active= values"""
        for bad in ["", "maybe", "ok?", "  truthy  "]:
            resp = self.client.get(f"{BASE_URL}?active={bad}")
            assert resp.status_code == status.HTTP_400_BAD_REQUEST

    def test_query_active_returns_only_current_promotions(self):
        """It should return only promotions that are active today when ?active=true"""
        today = date.today()

        # Active: past -> future
        self.client.post(
            BASE_URL,
            json=make_payload(
                name="ActiveNow",
                start_date=(today - timedelta(days=2)).isoformat(),
                end_date=(today + timedelta(days=2)).isoformat(),
            ),
        )

        # Expired: past -> yesterday
        self.client.post(
            BASE_URL,
            json=make_payload(
                name="Expired",
                start_date=(today - timedelta(days=10)).isoformat(),
                end_date=(today - timedelta(days=1)).isoformat(),
            ),
        )

        # Future: tomorrow -> future
        self.client.post(
            BASE_URL,
            json=make_payload(
                name="Future",
                start_date=(today + timedelta(days=1)).isoformat(),
                end_date=(today + timedelta(days=10)).isoformat(),
            ),
        )

        resp = self.client.get(f"{BASE_URL}?active=true")
        assert resp.status_code == status.HTTP_200_OK
        names = {p["name"] for p in resp.get_json()}
        assert "ActiveNow" in names
        assert "Expired" not in names
        assert "Future" not in names

    def test_active_truthy_and_falsy_synonyms(self):
        """It should accept yes/no/1/0/true/false (case-insensitive)"""
        today = date.today()

        # Prepare 3 states
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

        # Truthy set -> only active
        for truthy in ["true", "True", "1", "YES", " yes "]:
            resp = self.client.get(f"{BASE_URL}?active={truthy}")
            assert resp.status_code == status.HTTP_200_OK
            data = resp.get_json()
            assert all(d["name"] == "ActiveNow" for d in data)

        # Falsy set -> only NOT active
        for falsy in ["false", "False", "0", "NO", " no "]:
            resp = self.client.get(f"{BASE_URL}?active={falsy}")
            assert resp.status_code == status.HTTP_200_OK
            names = {p["name"] for p in resp.get_json()}
            assert "ActiveNow" not in names
            assert "Expired" in names
            assert "Future" in names

    def test_deactivate_promotion_sets_end_date_to_yesterday_and_excludes_from_active(self):
        """Deactivating twice does not push end date forward; deactivating an already expired promo won't extend it"""
        today = date.today()
        yesterday = today - timedelta(days=1)

        created = self.client.post(
            BASE_URL,
            json=make_payload(
                name="ToDeactivate",
                start_date=(today - timedelta(days=5)).isoformat(),
                end_date=(today + timedelta(days=5)).isoformat(),
            ),
        )
        assert created.status_code == status.HTTP_201_CREATED
        pid = created.get_json()["id"]

        # First deactivate -> set to yesterday
        resp = self.client.put(f"{BASE_URL}/{pid}/deactivate")
        assert resp.status_code == status.HTTP_200_OK
        body = resp.get_json()
        assert body["id"] == pid
        assert body["end_date"] == yesterday.isoformat()

        # No longer in active list
        active_resp = self.client.get(f"{BASE_URL}?active=true")
        assert active_resp.status_code == status.HTTP_200_OK
        names = {p["name"] for p in active_resp.get_json()}
        assert "ToDeactivate" not in names

        # Deactivate again (idempotent/effective but not extend)
        resp2 = self.client.put(f"{BASE_URL}/{pid}/deactivate")
        assert resp2.status_code == status.HTTP_200_OK
        assert resp2.get_json()["end_date"] == yesterday.isoformat()

    ##################################################################
    # UPDATE
    ##################################################################

    def test_update_promotion_success(self):
        """It should Update an existing Promotion (200)"""
        created = self.client.post(
            BASE_URL,
            json={
                "name": "Promo A",
                "promotion_type": "AMOUNT_OFF",
                "value": 10,
                "product_id": 111,
                "start_date": "2025-10-01",
                "end_date": "2025-10-31",
            },
        )
        assert created.status_code == status.HTTP_201_CREATED
        pid = created.get_json()["id"]

        updated = {
            "id": pid,
            "name": "Promo A+",
            "promotion_type": "AMOUNT_OFF",
            "value": 15,
            "product_id": 111,
            "start_date": "2025-10-01",
            "end_date": "2025-10-31",
        }
        resp = self.client.put(f"{BASE_URL}/{pid}", json=updated)
        assert resp.status_code == status.HTTP_200_OK
        body = resp.get_json()
        assert body["name"] == "Promo A+"
        assert body["value"] == 15

    def test_update_promotion_not_found(self):
        """It should return 404 when updating a non-existent Promotion"""
        payload = {
            "name": "Ghost",
            "promotion_type": "AMOUNT_OFF",
            "value": 5,
            "product_id": 222,
            "start_date": "2025-10-01",
            "end_date": "2025-10-31",
        }
        resp = self.client.put(f"{BASE_URL}/99999999", json=payload)
        assert resp.status_code == status.HTTP_404_NOT_FOUND

    def test_update_promotion_id_mismatch_returns_400(self):
        """It should return 400 when body.id != path id"""
        created = self.client.post(
            BASE_URL,
            json={
                "name": "Mismatch",
                "promotion_type": "AMOUNT_OFF",
                "value": 1,
                "product_id": 9,
                "start_date": "2025-10-01",
                "end_date": "2025-10-31",
            },
        )
        assert created.status_code == status.HTTP_201_CREATED
        pid = created.get_json()["id"]

        # Body id != path id
        bad = make_payload(name="Mismatch+", value=2)
        bad["id"] = pid + 1
        resp = self.client.put(f"{BASE_URL}/{pid}", json=bad)
        assert resp.status_code == status.HTTP_400_BAD_REQUEST

    ##################################################################
    # DELETE / HOME / MISC
    ##################################################################

    def test_delete_existing(self):
        """It should delete an existing Promotion and return 204"""
        created = self.client.post(BASE_URL, json=make_payload(name="ToDelete"))
        assert created.status_code == status.HTTP_201_CREATED
        pid = created.get_json()["id"]

        resp = self.client.delete(f"{BASE_URL}/{pid}")
        assert resp.status_code == status.HTTP_204_NO_CONTENT

    def test_health(self):
        """It should return 200 OK with {'status':'OK'} on GET /health"""
        resp = self.client.get("/health")
        assert resp.status_code == status.HTTP_200_OK
        assert resp.get_json() == {"status": "OK"}

    def test_home(self):
        """It should call the home page"""
        resp = self.client.get("/")
        assert resp.status_code == status.HTTP_200_OK

    def test_unknown_route_404(self):
        """It should return JSON 404 for unknown routes"""
        resp = self.client.get("/no/such/route")
        assert resp.status_code == status.HTTP_404_NOT_FOUND

    def test_method_not_allowed_json(self):
        """405 responses should be JSON"""
        # PATCH on /promotions is not allowed
        resp = self.client.patch(BASE_URL, json={})
        assert resp.status_code == status.HTTP_405_METHOD_NOT_ALLOWED
        assert resp.is_json
        # POST on /promotions/<id> is not allowed
        resp2 = self.client.post(f"{BASE_URL}/1", json={})
        assert resp2.status_code == status.HTTP_405_METHOD_NOT_ALLOWED
        assert resp2.is_json

    ##################################################################
    # HELPERS
    ##################################################################

    def assert201(self, resp):
        assert resp.status_code == status.HTTP_201_CREATED

    def assertFields(self, data, required=False):
        for key in ("id", "name", "promotion_type", "value", "product_id", "start_date", "end_date"):
            if required:
                assert key in data
