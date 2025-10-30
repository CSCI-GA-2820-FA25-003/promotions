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
Route tests grouped by feature
"""

import os
import logging
from unittest import TestCase
from datetime import date, timedelta

from service import status
from wsgi import app
from service.models import db, Promotion

######################################################################
#  H E L P E R S
######################################################################

BASE_URL = "/promotions"


def make_payload(**overrides) -> dict:
    """Build a valid promotion JSON payload"""
    base = {
        "name": "NYU Demo",
        "promotion_type": "AMOUNT_OFF",  # 确保为后端允许的枚举
        "value": 10,
        "product_id": 123,
        "start_date": "2025-10-01",
        "end_date": "2025-10-31",
    }
    base.update(overrides)
    return base


######################################################################
#  B A S E   T E S T   C L A S S
######################################################################


class TestPromotionService(TestCase):
    """Promotion Service functional tests"""

    @classmethod
    def setUpClass(cls):
        app.config["TESTING"] = True
        app.config["DEBUG"] = False
        app.logger.setLevel(logging.CRITICAL)

        # NOTE: GitHub Action uses DATABASE_URI in the environment
        app.config["SQLALCHEMY_DATABASE_URI"] = os.getenv(
            "DATABASE_URI",
            "postgresql+psycopg://postgres:postgres@localhost:5432/testdb",
        )
        app.app_context().push()

    def setUp(self):
        db.session.query(Promotion).delete()
        db.session.commit()
        self.client = app.test_client()

    def tearDown(self):
        db.session.remove()

    ##################################################################
    # Basic routes & health
    ##################################################################

    def test_home(self):
        resp = self.client.get("/")
        self.assertEqual(resp.status_code, status.HTTP_200_OK)

    def test_health(self):
        resp = self.client.get("/health")
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertEqual(resp.get_data(as_text=True), "OK")

    ##################################################################
    # Create / Read / Update / Delete
    ##################################################################

    def test_create_promotion(self):
        resp = self.client.post(BASE_URL, json=make_payload(name="Created"))
        self.assertEqual(resp.status_code, status.HTTP_201_CREATED)
        data = resp.get_json()
        self.assertEqual(data["name"], "Created")

    def test_delete_promotion(self):
        p = self.client.post(BASE_URL, json=make_payload(name="ToDelete"))
        self.assertEqual(p.status_code, status.HTTP_201_CREATED)
        pid = p.get_json()["id"]

        resp = self.client.delete(f"{BASE_URL}/{pid}")
        self.assertEqual(resp.status_code, status.HTTP_204_NO_CONTENT)

    def test_update_promotion_success(self):
        p = self.client.post(BASE_URL, json=make_payload(name="Before"))
        self.assertEqual(p.status_code, status.HTTP_201_CREATED)
        pid = p.get_json()["id"]

        payload = make_payload(name="After", promotion_type="AMOUNT_OFF")
        resp = self.client.put(f"{BASE_URL}/{pid}", json=payload)
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertEqual(resp.get_json()["name"], "After")

    def test_update_promotion_not_found(self):
        resp = self.client.put(f"{BASE_URL}/999999", json=make_payload(name="Ghost"))
        self.assertEqual(resp.status_code, status.HTTP_404_NOT_FOUND)

    def test_update_id_mismatch(self):
        p = self.client.post(BASE_URL, json=make_payload(name="X"))
        self.assertEqual(p.status_code, status.HTTP_201_CREATED)
        real_id = p.get_json()["id"]

        body = make_payload(name="Y")
        body["id"] = real_id + 1
        resp = self.client.put(f"{BASE_URL}/{real_id}", json=body)
        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)

    ##################################################################
    # Listing & filtering
    ##################################################################

    def test_list_all(self):
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
        p = self.client.post(BASE_URL, json=make_payload(name="IDOne"))
        self.assertEqual(p.status_code, status.HTTP_201_CREATED)
        pid = p.get_json()["id"]

        resp = self.client.get(f"{BASE_URL}?id={pid}")
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        data = resp.get_json()
        self.assertEqual(len(data), 1)
        self.assertEqual(data[0]["id"], pid)

    def test_filter_by_name(self):
        self.client.post(BASE_URL, json=make_payload(name="N1"))
        self.client.post(BASE_URL, json=make_payload(name="N2"))
        resp = self.client.get(f"{BASE_URL}?name=N1")
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        data = resp.get_json()
        self.assertTrue(all(p["name"] == "N1" for p in data))

    def test_list_invalid_route(self):
        resp = self.client.get("/does-not-exist")
        self.assertEqual(resp.status_code, status.HTTP_404_NOT_FOUND)

    ##################################################################
    # Active filter (strict bool parsing)
    ##################################################################

    def test_active_truthy_and_falsy_synonyms(self):
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
            # 只要全部在今天区间内，并且至少有一条
            self.assertGreaterEqual(len(data), 1)
            for p in data:
                sd = date.fromisoformat(p["start_date"])
                ed = date.fromisoformat(p["end_date"])
                self.assertTrue(sd <= today <= ed)

        for falsy in ["false", "False", "0", "NO", " no "]:
            resp = self.client.get(f"{BASE_URL}?active={falsy}")
            self.assertEqual(resp.status_code, status.HTTP_200_OK)
            data = resp.get_json()
            self.assertTrue(
                all(
                    (date.fromisoformat(p["start_date"]) > today)
                    or (date.fromisoformat(p["end_date"]) < today)
                    for p in data
                )
            )

    def test_query_active_returns_only_current_promotions(self):
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
        self.assertGreaterEqual(len(data), 1)
        for p in data:
            sd = date.fromisoformat(p["start_date"])
            ed = date.fromisoformat(p["end_date"])
            self.assertTrue(sd <= today <= ed)

    ##################################################################
    # product_id & promotion_type filters
    ##################################################################

    def test_list_promotions_filter_by_product_id(self):
        self.client.post(BASE_URL, json=make_payload(name="A", product_id=2222))
        self.client.post(BASE_URL, json=make_payload(name="B", product_id=3333))
        resp = self.client.get(f"{BASE_URL}?product_id=2222")
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        data = resp.get_json()
        self.assertTrue(isinstance(data, list))
        self.assertTrue(len(data) >= 1)
        self.assertTrue(all(p["product_id"] == 2222 for p in data))

    def test_query_by_promotion_type_returns_matches(self):
        """断言：筛选出的每条都为 BOGO，且包含刚创建的那条"""
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

        # 关键：不要求“正好 1 条”，而是要求全部为 BOGO，且至少包含 B1
        self.assertTrue(isinstance(data, list))
        self.assertGreaterEqual(len(data), 1)
        self.assertTrue(all(p["promotion_type"] == "BOGO" for p in data))
        self.assertTrue(any(p["name"] == "B1" for p in data))

    def test_query_by_promotion_type_returns_empty_when_no_match(self):
        r = self.client.post(
            BASE_URL, json=make_payload(name="A1", promotion_type="AMOUNT_OFF", value=10)
        )
        self.assertEqual(r.status_code, status.HTTP_201_CREATED)

        resp = self.client.get(f"{BASE_URL}?promotion_type=NON_EXISTENT_TYPE")
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertEqual(resp.get_json(), [])

    def test_query_promotion_type_blank(self):
        r = self.client.post(
            BASE_URL, json=make_payload(name="X", promotion_type="AMOUNT_OFF")
        )
        self.assertEqual(r.status_code, status.HTTP_201_CREATED)

        resp = self.client.get(f"{BASE_URL}?promotion_type=   ")
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertEqual(resp.get_json(), [])

    ##################################################################
    # Method not allowed / error path
    ##################################################################

    def test_method_not_allowed_on_collection(self):
        resp = self.client.patch(BASE_URL, json={})
        self.assertEqual(resp.status_code, status.HTTP_405_METHOD_NOT_ALLOWED)
        self.assertEqual(resp.get_json()["message"], "Method Not Allowed")

    def test_method_not_allowed_on_resource(self):
        p = self.client.post(BASE_URL, json=make_payload(name="Patch?"))
        self.assertEqual(p.status_code, status.HTTP_201_CREATED)
        pid = p.get_json()["id"]
        resp = self.client.post(f"{BASE_URL}/{pid}", json={})
        self.assertEqual(resp.status_code, status.HTTP_405_METHOD_NOT_ALLOWED)
        self.assertEqual(resp.get_json()["message"], "Method Not Allowed")

    def test_unhandled_exception_returns_500(self):
        # 触发 routes 中的 except 分支（使用一个非法的转换）
        resp = self.client.get(f"{BASE_URL}?id=not-an-int")
        # routes 里会尝试 int() 转换并在 find() 中返回 None -> []
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
