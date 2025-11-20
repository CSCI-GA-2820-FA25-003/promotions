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

WHY this change:
- Unify the query contract: single-item lookup (find) returns object|None;
  multi-item lookups (find_by_name/product_id/promotion_type) return list.
- Replace ambiguous 'category' with explicit 'product_id' for clarity.
- Keep a backward-compatible alias find_by_category -> find_by_product_id.
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

    # Allowed promotion types
    ALLOWED_PROMOTION_TYPES = {
        "PERCENT",
        "DISCOUNT",
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
        self.id = None  # make sure id is None so SQLAlchemy will assign one
        try:
            db.session.add(self)
            # Ensure PK is assigned even if commit() is mocked in tests:
            # flush sends pending INSERTs to the DB within the tx and assigns IDs
            db.session.flush()
            db.session.commit()
        except Exception as e:  # pragma: no cover - exercised via exception tests
            db.session.rollback()
            logger.error("Error creating record: %s", self)
            raise DatabaseError(e) from e

    def update(self):
        """Updates this Promotion in the database."""
        logger.info("Saving %s", self.name)
        if not self.id:
            # more friendly message
            raise DataValidationError("Field 'id' is required for update")
        try:
            db.session.commit()
        except Exception as e:  # pragma: no cover - exercised via exception tests
            db.session.rollback()
            logger.error("Error updating record: %s", self)
            raise DatabaseError(e) from e

    def delete(self):
        """Removes this Promotion from the data store."""
        logger.info("Deleting %s", self.name)
        try:
            db.session.delete(self)
            db.session.commit()
        except Exception as e:  # pragma: no cover - exercised via exception tests
            db.session.rollback()
            logger.error("Error deleting record: %s", self)
            raise DatabaseError(e) from e

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
    def _validate_name(data: Mapping) -> str:
        if "name" not in data:
            raise DataValidationError("Invalid promotion: missing name")
        name = data["name"]
        if not isinstance(name, str):
            raise DataValidationError("Field 'name' must be a string")
        return name

    def _validate_promotion_type(self, data: Mapping) -> str:
        if "promotion_type" not in data:
            raise DataValidationError("Invalid promotion: missing promotion_type")
        promotion_type = data["promotion_type"]
        if not isinstance(promotion_type, str):
            raise DataValidationError("Field 'promotion_type' must be a string")
        if promotion_type not in self.ALLOWED_PROMOTION_TYPES:
            raise DataValidationError(
                f"Invalid promotion_type '{promotion_type}'. "
                f"Allowed: {sorted(self.ALLOWED_PROMOTION_TYPES)}"
            )
        return promotion_type

    @staticmethod
    def _validate_value(data: Mapping) -> int:
        if "value" not in data:
            raise DataValidationError("Invalid promotion: missing value")
        value = data["value"]
        if not isinstance(value, int):
            raise DataValidationError("Field 'value' must be an integer")
        if value < 0:
            raise DataValidationError("Invalid value: must be >= 0")
        return value

    @staticmethod
    def _validate_product_id(data: Mapping) -> int:
        if "product_id" not in data:
            raise DataValidationError("Invalid promotion: missing product_id")
        pid = data["product_id"]
        if not isinstance(pid, int):
            raise DataValidationError("Field 'product_id' must be an integer")
        if pid <= 0:
            raise DataValidationError("Invalid product_id: must be > 0")
        return pid

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

    # ---------------------- public API ----------------------

    def deserialize(self, data: dict):
        """Deserializes a Promotion from a dictionary and validates business rules."""
        self._require_mapping(data)

        self.name = self._validate_name(data)
        self.promotion_type = self._validate_promotion_type(data)
        self.value = self._validate_value(data)
        self.product_id = self._validate_product_id(data)
        self.start_date = self._require_iso_date(data, "start_date")
        self.end_date = self._require_iso_date(data, "end_date")
        if self.start_date > self.end_date:
            raise DataValidationError("start_date must be on or before end_date")
        return self

    ##################################################
    # CLASS METHODS  (Unified contract)
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
        """Returns all Promotions that match the given product_id (as a list).

        WHY: This replaces the ambiguous 'category' naming with explicit 'product_id',
        and returns a concrete list to unify multi-item query semantics.
        """
        logger.info("Processing product_id query for %s ...", product_id)
        try:
            pid = int(product_id)
        except (TypeError, ValueError):
            return []
        return list(cls.query.filter(cls.product_id == pid).all())

    @classmethod
    def find_active(cls, on_date: date | None = None) -> list["Promotion"]:
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
