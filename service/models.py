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
from flask_sqlalchemy import SQLAlchemy

logger = logging.getLogger("flask.app")

# SQLAlchemy handle; initialized in init_db()
db = SQLAlchemy()


class DataValidationError(Exception):
    """Used for data validation errors when deserializing or updating."""


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

    # ---- Allowed promotion types ----
    # 为了兼容现有测试/工厂数据，这里同时允许同义写法：
    # - 固定金额/百分比的人类可读写法（"Percentage off", "Buy One Get One", "Fixed amount off"）
    # - 以及简写/枚举风格（"AMOUNT_OFF", "BOGO"）
    ALLOWED_PROMOTION_TYPES = {
        "AMOUNT_OFF",
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
        self.id = None  # make sure id is None so SQLAlchemy will assign one
        try:
            db.session.add(self)
            db.session.commit()
        except Exception as e:  # pragma: no cover - exercised via exception tests
            db.session.rollback()
            logger.error("Error creating record: %s", self)
            raise DataValidationError(e) from e

    def update(self):
        """Updates this Promotion in the database."""
        logger.info("Saving %s", self.name)
        if not self.id:
            raise DataValidationError("Update called with empty ID field")
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

    def deserialize(self, data: dict):
        """
        Deserializes a Promotion from a dictionary and validates business rules.

        Business constraints enforced:
          - value must be non-negative (>= 0)
          - product_id must be a positive integer (> 0)
          - promotion_type must be one of ALLOWED_PROMOTION_TYPES
        """
        try:
            # --- Required simple fields ---
            self.name = data["name"]

            # --- promotion_type: enumerated allowed values (保持原样，不做大小写/规范化转换) ---
            ptype = data["promotion_type"]
            if not isinstance(ptype, str):
                raise DataValidationError(
                    "Invalid type for string [promotion_type]: " + str(type(ptype))
                )
            if ptype not in self.ALLOWED_PROMOTION_TYPES:
                raise DataValidationError(
                    f"Invalid promotion_type '{ptype}'. "
                    f"Allowed: {sorted(self.ALLOWED_PROMOTION_TYPES)}"
                )
            self.promotion_type = ptype

            # --- value: must be integer and >= 0 ---
            if not isinstance(data["value"], int):
                raise DataValidationError(
                    "Invalid type for integer [value]: " + str(type(data["value"]))
                )
            if data["value"] < 0:
                raise DataValidationError("Invalid value: must be >= 0")
            self.value = data["value"]

            # --- product_id: must be integer and > 0 ---
            if not isinstance(data["product_id"], int):
                raise DataValidationError(
                    "Invalid type for integer [product_id]: "
                    + str(type(data["product_id"]))
                )
            if data["product_id"] <= 0:
                raise DataValidationError("Invalid product_id: must be > 0")
            self.product_id = data["product_id"]

            # --- dates: ISO-8601 strings -> date ---
            self.start_date = date.fromisoformat(data["start_date"])
            self.end_date = date.fromisoformat(data["end_date"])

        except AttributeError as error:
            raise DataValidationError("Invalid attribute: " + error.args[0]) from error
        except KeyError as error:
            raise DataValidationError(
                "Invalid promotion: missing " + error.args[0]
            ) from error
        except (TypeError, ValueError) as error:
            raise DataValidationError(
                "Invalid promotion: body of request contained bad or no data "
                + str(error)
            ) from error

        return self

    ##################################################
    # CLASS METHODS
    ##################################################

    @classmethod
    def all(cls):
        """Returns all Promotions in the database (as a list)."""
        logger.info("Processing all Promotions")
        return cls.query.all()

    @classmethod
    def find(cls, by_id):
        """Finds a Promotion by its ID (single object or None)."""
        logger.info("Processing lookup for id %s ...", by_id)
        return cls.query.session.get(cls, by_id)

    @classmethod
    def find_by_name(cls, name):
        """
        Returns a SQLAlchemy Query filtered by name.

        Tests call `.count()` on the result, so we must return a Query,
        not a list.
        """
        logger.info("Processing name query for %s ...", name)
        return cls.query.filter(cls.name == name)

    @classmethod
    def find_by_promotion_type(cls, promotion_type: str):
        """Returns all Promotions that match the given promotion_type exactly (as a list)."""
        logger.info("Processing promotion_type query for %s ...", promotion_type)
        return cls.query.filter(cls.promotion_type == promotion_type).all()

    @classmethod
    def find_by_category(cls, category):
        """
        Returns a SQLAlchemy Query filtered by product_id (used as category).

        The test suite calls `.count()` on the returned value, so we must
        return a Query, not a list. For invalid input, return an empty Query.
        """
        logger.info("Processing category query for %s ...", category)
        try:
            product_id = int(category)
            return cls.query.filter(cls.product_id == product_id)
        except (ValueError, TypeError):
            # empty Query (still supports .count() -> 0)
            return cls.query.filter(False)

    @classmethod
    def find_by_id(cls, promotion_id):
        """
        Returns a single-element list containing the Promotion with the given id,
        or an empty list if not found or invalid.
        """
        logger.info("Processing id query for %s ...", promotion_id)
        try:
            pid = int(promotion_id)
            promotion = cls.query.session.get(cls, pid)
            return [promotion] if promotion else []
        except (ValueError, TypeError):
            return []
