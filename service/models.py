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

Contract (to satisfy tests and routes):
- Single lookup:
    * find(id) -> Promotion | None
    * find_by_id(id) -> [Promotion] or []
- Multi-item lookups:
    * find_by_name(name) -> SQLAlchemy Query     (tests call .count())
    * find_by_category(category==product_id) -> SQLAlchemy Query (tests call .count())
    * find_by_product_id(product_id) -> list[Promotion]          (routes use as list)
    * find_by_promotion_type(ptype) -> list[Promotion]           (routes use as list)
    * find_active(on_date) -> list[Promotion]                    (routes use as list)
"""

import logging
from datetime import date
from collections.abc import Mapping
from typing import List, Optional, Union

from flask_sqlalchemy import SQLAlchemy

logger = logging.getLogger("flask.app")

# Initialized by init_db() in app factory
db = SQLAlchemy()


class DataValidationError(Exception):
    """Used for data validation errors when deserializing or updating."""


class DatabaseError(Exception):
    """Kept for compatibility with error handlers; not used in tests."""


class Promotion(db.Model):
    """Class that represents a Promotion"""

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

    # auditing
    created_at = db.Column(db.DateTime, default=db.func.now(), nullable=False)
    last_updated = db.Column(
        db.DateTime, default=db.func.now(), onupdate=db.func.now(), nullable=False
    )

    # 允许的促销类型（包含项目&测试中出现的写法）
    ALLOWED_PROMOTION_TYPES = {
        "AMOUNT_OFF",
        "PERCENTAGE_OFF",
        "Percentage off",
        "Buy One Get One",
        "BOGO",
        "Fixed amount off",
    }

    ##################################################
    # INSTANCE METHODS
    ##################################################

    def __repr__(self) -> str:  # pragma: no cover (string repr)
        return f"<Promotion {self.name} id=[{self.id}]>"

    def create(self):
        """Creates this Promotion in the database."""
        logger.info("Creating %s", self.name)
        self.id = None  # let SQLAlchemy assign one
        try:
            db.session.add(self)
            # ensure PK exists even if commit is mocked
            db.session.flush()
            db.session.commit()
        except Exception as e:  # pragma: no cover (hit via unit test mocking)
            db.session.rollback()
            logger.error("Error creating record: %s", self)
            # ✅ tests expect DataValidationError
            raise DataValidationError(e) from e

    def update(self):
        """Updates this Promotion in the database."""
        logger.info("Saving %s", self.name)
        if not self.id:
            raise DataValidationError("Field 'id' is required for update")
        try:
            db.session.commit()
        except Exception as e:  # pragma: no cover
            db.session.rollback()
            logger.error("Error updating record: %s", self)
            # ✅ tests expect DataValidationError
            raise DataValidationError(e) from e

    def delete(self):
        """Removes this Promotion from the data store."""
        logger.info("Deleting %s", self.name)
        try:
            db.session.delete(self)
            db.session.commit()
        except Exception as e:  # pragma: no cover
            db.session.rollback()
            logger.error("Error deleting record: %s", self)
            # ✅ tests expect DataValidationError
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

    # ---------------------- helpers ----------------------

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
        """Deserializes a Promotion from a dictionary and validates business rules."""
        self._require_mapping(data)

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

    # ===== Methods expected by tests and routes =====

    @classmethod
    def find_by_name(cls, name: str):
        """Return a SQLAlchemy Query filtered by name (tests call .count())."""
        logger.info("Processing name query for %s ...", name)
        return cls.query.filter(cls.name == name)

    @classmethod
    def find_by_category(cls, category):
        """
        Backward-compatible alias for product_id used by model tests.
        Return a SQLAlchemy Query; invalid input -> empty Query (still .count()==0).
        """
        logger.info("Processing category query for %s ...", category)
        try:
            product_id = int(category)
            return cls.query.filter(cls.product_id == product_id)
        except (ValueError, TypeError):
            return cls.query.filter(False)

    @classmethod
    def find_by_product_id(cls, product_id: Union[int, str]) -> List["Promotion"]:
        """Return a list of Promotions with the given product_id (used by routes)."""
        logger.info("Processing product_id query for %s ...", product_id)
        try:
            pid = int(product_id)
        except (ValueError, TypeError):
            return []
        return list(cls.query.filter(cls.product_id == pid).all())

    @classmethod
    def find_by_promotion_type(cls, promotion_type: str) -> List["Promotion"]:
        """Return a list of Promotions with the given promotion_type (exact match)."""
        logger.info("Processing promotion_type query for %s ...", promotion_type)
        return list(cls.query.filter(cls.promotion_type == promotion_type).all())

    @classmethod
    def find_active(cls, on_date: Optional[date] = None) -> List["Promotion"]:
        """Return a list of Promotions active on the given date (inclusive)."""
        if on_date is None:
            on_date = date.today()
        logger.info("Processing active-on %s query ...", on_date.isoformat())
        return list(
            cls.query.filter(
                cls.start_date <= on_date,
                cls.end_date >= on_date,
            ).all()
        )

    @classmethod
    def find_by_id(cls, promotion_id) -> List["Promotion"]:
        """Return [Promotion] when found else []."""
        logger.info("Processing id query for %s ...", promotion_id)
        try:
            pid = int(promotion_id)
        except (ValueError, TypeError):
            return []
        obj = cls.query.session.get(cls, pid)
        return [obj] if obj else []
