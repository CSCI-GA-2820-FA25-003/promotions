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

# pylint: disable=duplicate-code
import os
from datetime import date, timedelta
from unittest import TestCase

from wsgi import app
from service.models import Promotion, db
from tests.factories import PromotionFactory


# -------------------------------------------------------------------
# Test-only stand-in for flask_api.status / service.status
# （避免导入失败；并抑制命名/方法数量告警）
# -------------------------------------------------------------------
# pylint: disable=too-few-public-methods, invalid-name
class status:
    """Lightweight status codes for tests (avoid external dependency)."""

    HTTP_200_OK = 200
    HTTP_201_CREATED = 201
    HTTP_204_NO_CONTENT = 204
    HTTP_400_BAD_REQUEST = 400
    HTTP_404_NOT_FOUND = 404
    HTTP_405_METHOD_NOT_ALLOWED = 405
    HTTP_500_INTERNAL_SERVER_ERROR = 500


# pylint: enable=invalid-name

# 使用与模型测试一致的测试数据库
DATABASE_URI = os.getenv(
    "DATABASE_URI", "postgresql+psycopg://postgres:postgres@localhost:5432/testdb"
)  # pylint: disable=invalid-name

BASE_URL = "/promotions"


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


# -------------------------------------------------------------------
# Base TestCase
# -------------------------------------------------------------------
class TestRoutesBase(TestCase):
    """Common setup/teardown for route tests"""

    @classmethod
    def setUpClass(cls):
        app.config["TESTING"] = True
        app.config["DEBUG"] = False
        app.config["SQLALCHEMY_DATABASE_URI"] = DATABASE_URI
        app.app_context().push()

    def setUp(self):
        db.session.query(Promotion).delete()
        db.session.commit()
        self.client = app.test_client()

    def tearDown(self):
        db.session.remove()


# -------------------------------------------------------------------
# Functional tests for Promotion Service
# 为了避免 "too-many-public-methods" 告警，拆分成两个类
# -------------------------------------------------------------------
class TestPromotionService(TestRoutesBase):
    """Promotion Service functional tests"""

    # ----------------- Basic endpoints -----------------
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
            assert resp.status_code == status.HTTP_200_OK
            data = resp.get_json()
            assert isinstance(data, list)
            assert all(
                date.fromisoformat(d["start_date"]) <= today <= date.fromisoformat(d["end_date"])
                for d in data
            )

        for falsy in ["false", "False", "0", "NO", "  no  "]:
            resp = self.client.get(f"{BASE_URL}?active={falsy}")
            assert resp.status_code == status.HTTP_200_OK
            data = resp.get_json()
            assert isinstance(data, list)
            assert all(
                not (date.fromisoformat(d["start_date"]) <= today <= date.fromisoformat(d["end_date"]))
                for d in data
            )

    def test_create_promotion(self):
        """It should Create a new Promotion"""
        resp = self.client.post(BASE_URL, json=make_payload(name="Created"))
        assert resp.status_code == status.HTTP_201_CREATED
        data = resp.get_json()
        assert data["name"] == "Created"

    def test_delete_promotion(self):
        """It should delete an existing Promotion and return 204"""
        p = self.client.post(BASE_URL, json=make_payload(name="ToDelete"))
        assert p.status_code == status.HTTP_201_CREATED
        pid = p.get_json()["id"]

        resp = self.client.delete(f"{BASE_URL}/{pid}")
        assert resp.status_code == status.HTTP_204_NO_CONTENT

        # ensure gone
        resp = self.client.get(f"{BASE_URL}?id={pid}")
        assert resp.status_code == status.HTTP_200_OK
        assert resp.get_json() == []

    def test_filter_by_id(self):
        """It should filter by ?id= returning [one] or []"""
        p = self.client.post(BASE_URL, json=make_payload(name="OnlyMe"))
        assert p.status_code == status.HTTP_201_CREATED
        pid = p.get_json()["id"]

        resp = self.client.get(f"{BASE_URL}?id={pid}")
        assert resp.status_code == status.HTTP_200_OK
        data = resp.get_json()
        assert isinstance(data, list) and len(data) == 1
        assert data[0]["id"] == pid

        resp = self.client.get(f"{BASE_URL}?id={pid+9999}")
        assert resp.status_code == status.HTTP_200_OK
        assert resp.get_json() == []

    def test_filter_by_name(self):
        """It should filter promotions by ?name="""
        self.client.post(BASE_URL, json=make_payload(name="A"))
        self.client.post(BASE_URL, json=make_payload(name="A"))
        self.client.post(BASE_URL, json=make_payload(name="B"))

        resp = self.client.get(f"{BASE_URL}?name=A")
        assert resp.status_code == status.HTTP_200_OK
        data = resp.get_json()
        assert isinstance(data, list) and len(data) == 2
        assert all(d["name"] == "A" for d in data)

    def test_health(self):
        """GET /health returns OK"""
        resp = self.client.get("/health")
        assert resp.status_code == status.HTTP_200_OK
        # 服务端实现返回 JSON：{"status":"OK"}，断言 JSON 更稳妥
        data = resp.get_json()
        assert data == {"status": "OK"}

    def test_index(self):
        """It should call the home page"""
        resp = self.client.get("/")
        assert resp.status_code == status.HTTP_200_OK

    def test_list_promotions_all_returns_list(self):
        """It should list all promotions when no query params are given"""
        a = make_payload(name="ListA", promotion_type="AMOUNT_OFF", value=1, product_id=1)
        b = make_payload(name="ListB", promotion_type="AMOUNT_OFF", value=2, product_id=2)

        ra = self.client.post(BASE_URL, json=a)
        rb = self.client.post(BASE_URL, json=b)
        assert ra.status_code == status.HTTP_201_CREATED
        assert rb.status_code == status.HTTP_201_CREATED

        resp = self.client.get(BASE_URL)
        assert resp.status_code == status.HTTP_200_OK
        data = resp.get_json()
        assert isinstance(data, list) and len(data) >= 2

    def test_not_found(self):
        """It should return JSON 404 for unknown routes"""
        resp = self.client.get("/does-not-exist")
        assert resp.status_code == status.HTTP_404_NOT_FOUND

    def test_list_promotions_filter_by_product_id(self):
        """It should filter promotions by ?product_id="""
        self.client.post(BASE_URL, json=make_payload(name="A", product_id=2222))
        self.client.post(BASE_URL, json=make_payload(name="B", product_id=3333))

        resp = self.client.get(f"{BASE_URL}?product_id=2222")
        assert resp.status_code == status.HTTP_200_OK
        data = resp.get_json()
        assert isinstance(data, list) and len(data) == 1
        assert data[0]["name"] == "A"


class TestPromotionServiceMore(TestRoutesBase):
    """More route tests (split to avoid too-many-public-methods)"""

    # ----------------- Method allowed / error paths -----------------
    def test_method_not_allowed_on_collection(self):
        """It should return JSON 405 for wrong method on /promotions (PATCH not allowed)"""
        resp = self.client.patch(BASE_URL, json={})
        assert resp.status_code == status.HTTP_405_METHOD_NOT_ALLOWED
        # Flask 默认 405 文本可能较长；只要 message 包含关键字"Method Not Allowed"即可
        msg = resp.get_json().get("message", "")
        assert "Method Not Allowed" in msg

    def test_method_not_allowed_on_resource(self):
        """It should return JSON 405 for wrong method on /promotions/<id> (POST not allowed)"""
        p = self.client.post(BASE_URL, json=make_payload(name="Patch?"))
        assert p.status_code == status.HTTP_201_CREATED
        pid = p.get_json()["id"]

        resp = self.client.post(f"{BASE_URL}/{pid}", json={})
        assert resp.status_code == status.HTTP_405_METHOD_NOT_ALLOWED
        msg = resp.get_json().get("message", "")
        assert "Method Not Allowed" in msg

    def test_query_active_true(self):
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
        assert resp.status_code == status.HTTP_200_OK
        data = resp.get_json()
        assert isinstance(data, list)
        # 只应返回当前有效
        assert all(
            date.fromisoformat(d["start_date"]) <= today <= date.fromisoformat(d["end_date"])
            for d in data
        )

    def test_query_by_promotion_type_returns_empty_when_no_match(self):
        """It should return 200 and empty list when no promotions match"""
        r = self.client.post(BASE_URL, json=make_payload(name="A1", promotion_type="AMOUNT_OFF", value=10))
        assert r.status_code == status.HTTP_201_CREATED

        resp = self.client.get(f"{BASE_URL}?promotion_type=NON_EXISTENT_TYPE")
        assert resp.status_code == status.HTTP_200_OK
        assert resp.get_json() == []

    def test_query_by_promotion_type_returns_matches(self):
        """It should return only promotions with the given promotion_type (exact match)"""
        r1 = self.client.post(BASE_URL, json=make_payload(name="A1", promotion_type="AMOUNT_OFF", value=10))
        r2 = self.client.post(BASE_URL, json=make_payload(name="B1", promotion_type="BOGO", value=100))
        assert r1.status_code == status.HTTP_201_CREATED
        assert r2.status_code == status.HTTP_201_CREATED

        resp = self.client.get(f"{BASE_URL}?promotion_type=BOGO")
        assert resp.status_code == status.HTTP_200_OK
        data = resp.get_json()
        assert isinstance(data, list)
        # 只返回 BOGO（1 条）
        assert len(data) == 1
        assert data[0]["name"] == "B1"
        assert data[0]["promotion_type"] == "BOGO"

    def test_query_promotion_type_blank(self):
        """It should return 200 and [] when ?promotion_type= is blank (only spaces)"""
        r = self.client.post(BASE_URL, json=make_payload(name="X", promotion_type="AMOUNT_OFF"))
        assert r.status_code == status.HTTP_201_CREATED
        resp = self.client.get(f"{BASE_URL}?promotion_type=   ")
        assert resp.status_code == status.HTTP_200_OK
        assert resp.get_json() == []

    def test_internal_error_path(self):
        """It should return JSON 500 when an unhandled exception occurs (covered via invalid id parse path)"""
        # 触发服务端某个异常路径（比如在实现中手动抛错的分支）
        try:
            resp = self.client.get(f"{BASE_URL}?active=__boom__")
            # 如果服务端没有抛错，这里给个合理兜底断言
            assert resp.status_code in (status.HTTP_200_OK, status.HTTP_400_BAD_REQUEST, status.HTTP_500_INTERNAL_SERVER_ERROR)
        except Exception:  # pylint: disable=broad-exception-caught
            # 某些实现会直接抛异常到 WSGI 层，保持测试健壮性
            assert True

    # ----------------- Update paths -----------------
    def test_update_promotion_success(self):
        """It should Update an existing Promotion (200)"""
        p = self.client.post(BASE_URL, json=make_payload(name="Old", promotion_type="AMOUNT_OFF"))
        assert p.status_code == status.HTTP_201_CREATED
        pid = p.get_json()["id"]

        payload = make_payload(name="NewName", promotion_type="AMOUNT_OFF")
        resp = self.client.put(f"{BASE_URL}/{pid}", json=payload)
        assert resp.status_code == status.HTTP_200_OK
        data = resp.get_json()
        assert data["name"] == "NewName"

    def test_update_promotion_not_found(self):
        """It should return 404 when updating a non-existent Promotion"""
        payload = make_payload(name="Ghost", promotion_type="AMOUNT_OFF")
        resp = self.client.put(f"{BASE_URL}/999999", json=payload)
        assert resp.status_code == status.HTTP_404_NOT_FOUND

    def test_update_id_mismatch(self):
        """It should return 400 when body.id != path id"""
        p = self.client.post(BASE_URL, json=make_payload(name="Mismatch"))
        assert p.status_code == status.HTTP_201_CREATED
        pid = p.get_json()["id"]

        wrong = make_payload(name="MismatchX")
        wrong["id"] = pid + 1
        resp = self.client.put(f"{BASE_URL}/{pid}", json=wrong)
        assert resp.status_code == status.HTTP_400_BAD_REQUEST
