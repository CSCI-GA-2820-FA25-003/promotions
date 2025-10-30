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
Models for Promotions
"""

import logging
from datetime import date
from collections.abc import Mapping
from typing import List, Optional, Union

from flask_sqlalchemy import SQLAlchemy

logger = logging.getLogger("flask.app")

# SQLAlchemy handle; initialized in init_db()
db = SQLAlchemy()


class DataValidationError(Exception):
    """Used for data validation errors when deserializing or updating."""


class DatabaseError(Exception):
    """Used for database operation failures (commit/connection/constraint errors)."""


class Promotion(db.Model):
    """
    Class that represents a Promotion
    """

    ##################################################
    # Table Schema
    ##################################################
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(63), nullable=False)
    promotion_type = db.Column(db.String(63), nullable=False)
    value = db.Column(db.Integer, nullable=False)
    product_id = db.Column(db.Integer, nullable=False)
    start_date = db.Column(db.Date, nullable=False)
    end_date = db.Column(db.Date, nullable=False)
    # Auditing fields
    created_at = db.Column(db.DateTime, default=db.func.now(), nullable=False)
    last_updated = db.Column(
        db.DateTime, default=db.func.now(), onupdate=db.func.now(), nullable=False
    )

    # 为了兼容测试和工厂数据，允许几种常见写法
    ALLOWED_PROMOTION_TYPES = {
        "AMOUNT_OFF",
        "PERCENTAGE_OFF",
        "Percentage off",
        "Buy One Get One",
        "Fixed amount off",
        "BOGO",
    }

    ##################################################
    # INSTANCE METHODS
    ##################################################

    def __repr__(self):
        return f"<Promotion {self.name} id=[{self.id}]>"

    def create(self):
        """Creates this Promotion in the database."""
        logger.info("Creating %s", self.name)
        self.id = None  # ensure SQLAlchemy assigns one
        try:
            db.session.add(self)
            # flush 以便在 commit 被 mock 时也能拿到 id（单测需要）
            db.session.flush()
            db.session.commit()
        except Exception as e:  # pragma: no cover - exercised via exception tests
            db.session.rollback()
            logger.error("Error creating record: %s", self)
            # 测试期望：模型层抛 DataValidationError（由 error_handlers 统一成 500）
            raise DataValidationError(e) from e

    def update(self):
        """Updates this Promotion in the database."""
        logger.info("Saving %s", self.name)
        if not self.id:
            raise DataValidationError("Field 'id' is required for update")
        try:
            db.session.commit()
        except Exception as e:  # pragma: no cover - exercised via exception tests
            db.session.rollback()
            logger.error("Error updating record: %s", self)
            raise DataValidationError(e) from e

    def delete(self):
        """Removes this Promotion from the data store."""
        logger.info("Deleting %s", self.name)
        try:
            db.session.delete(self)
            db.session.commit()
        except Exception as e:  # pragma: no cover - exercised via exception tests
            db.session.rollback()
            logger.error("Error deleting record: %s", self)
            raise DataValidationError(e) from e

    def serialize(self) -> dict:
        """Serializes a Promotion into a dictionary."""
        return {
            "id": self.id,
            "name": self.name,
            "promotion_type": self.promotion_type,
            "value": self.value,
            "product_id": self.product_id,
            "start_date": self.start_date.isoformat() if self.start_date else None,
            "end_date": self.end_date.isoformat() if self.end_date else None,
        }

    # ---------------------- helpers （降低圈复杂度） ----------------------

    @staticmethod
    def _require_mapping(data):
        if not isinstance(data, Mapping):
            raise DataValidationError("Invalid attribute: data must be a mapping/dict")

    @staticmethod
    def _require_str(data: Mapping, key: str) -> str:
        if key not in data:
            raise DataValidationError(f"Invalid promotion: missing {key}")
        val = data[key]
        if not isinstance(val, str):
            raise DataValidationError(f"Field '{key}' must be a string")
        return val

    @staticmethod
    def _require_int(data: Mapping, key: str) -> int:
        if key not in data:
            raise DataValidationError(f"Invalid promotion: missing {key}")
        val = data[key]
        if not isinstance(val, int):
            raise DataValidationError(f"Invalid type for integer [{key}]: {type(val)}")
        return val

    @staticmethod
    def _require_iso_date(data: Mapping, key: str) -> date:
        if key not in data:
            raise DataValidationError(f"Invalid promotion: missing {key}")
        raw = data[key]
        try:
            return date.fromisoformat(raw)
        except Exception as e:
            raise DataValidationError(
                f"Field '{key}' must be an ISO date (YYYY-MM-DD)"
            ) from e

    def _validate_promotion_type(self, ptype: str) -> str:
        if ptype not in self.ALLOWED_PROMOTION_TYPES:
            raise DataValidationError(
                f"Invalid promotion_type '{ptype}'. "
                f"Allowed: {sorted(self.ALLOWED_PROMOTION_TYPES)}"
            )
        return ptype

    @staticmethod
    def _validate_value(value: int) -> int:
        if value < 0:
            raise DataValidationError("Invalid value: must be >= 0")
        return value

    @staticmethod
    def _validate_product_id(pid: int) -> int:
        if pid <= 0:
            raise DataValidationError("Invalid product_id: must be > 0")
        return pid

    # ---------------------- public API ----------------------

    def deserialize(self, data: dict):
        """
        Deserializes a Promotion from a dictionary and validates business rules.
        """
        self._require_mapping(data)

        # required fields
        self.name = self._require_str(data, "name")
        ptype = self._require_str(data, "promotion_type")
        self.promotion_type = self._validate_promotion_type(ptype)

        value = self._require_int(data, "value")
        self.value = self._validate_value(value)

        pid = self._require_int(data, "product_id")
        self.product_id = self._validate_product_id(pid)

        self.start_date = self._require_iso_date(data, "start_date")
        self.end_date = self._require_iso_date(data, "end_date")

        return self

    ##################################################
    # CLASS METHODS
    ##################################################

    @classmethod
    def all(cls) -> List["Promotion"]:
        """Returns all Promotions in the database (as a list)."""
        logger.info("Processing all Promotions")
        return list(cls.query.all())

    @classmethod
    def find(cls, by_id: Union[int, str]) -> Optional["Promotion"]:
        """Finds a Promotion by its ID (single object or None)."""
        logger.info("Processing lookup for id %s ...", by_id)
        try:
            pid = int(by_id)
        except (TypeError, ValueError):
            return None
        return cls.query.session.get(cls, pid)

    @classmethod
    def find_by_name(cls, name: str) -> List["Promotion"]:
        """Returns all Promotions that match the given name (as a list)."""
        logger.info("Processing name query for %s ...", name)
        return list(cls.query.filter(cls.name == name).all())

    @classmethod
    def find_by_promotion_type(cls, promotion_type: str) -> List["Promotion"]:
        """Returns all Promotions that match the given promotion_type exactly (as a list)."""
        logger.info("Processing promotion_type query for %s ...", promotion_type)
        return list(cls.query.filter(cls.promotion_type == promotion_type).all())

    @classmethod
    def find_by_product_id(cls, product_id: Union[int, str]) -> List["Promotion"]:
        """Returns all Promotions that match the given product_id (as a list)."""
        logger.info("Processing product_id query for %s ...", product_id)
        try:
            pid = int(product_id)
        except (TypeError, ValueError):
            return []
        return list(cls.query.filter(cls.product_id == pid).all())

    @classmethod
    def find_active(cls, on_date: Optional[date] = None) -> List["Promotion"]:
        """
        Returns all Promotions that are active on the given date (inclusive).
        Active means: start_date <= on_date <= end_date.
        """
        if on_date is None:
            on_date = date.today()
        return list(
            cls.query.filter(
                cls.start_date <= on_date,
                cls.end_date >= on_date,
            ).all()
        )
