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

# Create the SQLAlchemy object to be initialized later in init_db()
db = SQLAlchemy()


class DataValidationError(Exception):
    """Used for an data validation errors when deserializing"""


class Promotion(db.Model):
    """
    Class that represents a promotion
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
    # Database auditing fields
    created_at = db.Column(db.DateTime, default=db.func.now(), nullable=False)
    last_updated = db.Column(
        db.DateTime, default=db.func.now(), onupdate=db.func.now(), nullable=False
    )

    ##################################################
    # INSTANCE METHODS
    ##################################################

    def __repr__(self):
        return f"<Promotion {self.name} id=[{self.id}]>"

    def create(self):
        """Creates a Promotion in the database"""
        logger.info("Creating %s", self.name)
        self.id = None  # pylint: disable=invalid-name
        try:
            db.session.add(self)
            db.session.commit()
        except Exception as e:
            db.session.rollback()
            logger.error("Error creating record: %s", self)
            raise DataValidationError(e) from e

    def update(self):
        """Updates a Promotion in the database"""
        logger.info("Saving %s", self.name)
        if not self.id:
            raise DataValidationError("Update called with empty ID field")
        try:
            db.session.commit()
        except Exception as e:
            db.session.rollback()
            logger.error("Error updating record: %s", self)
            raise DataValidationError(e) from e

    def delete(self):
        """Removes a Promotion from the data store"""
        logger.info("Deleting %s", self.name)
        try:
            db.session.delete(self)
            db.session.commit()
        except Exception as e:
            db.session.rollback()
            logger.error("Error deleting record: %s", self)
            raise DataValidationError(e) from e

    def serialize(self):
        """Serializes a promotion into a dictionary"""
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
        Deserializes a promotion from a dictionary
        Args:
            data (dict): A dictionary containing the promotion data
        """
        try:
            self.name = data["name"]
            self.promotion_type = data["promotion_type"]
            if isinstance(data["value"], int):
                self.value = data["value"]
            else:
                raise DataValidationError(
                    "Invalid type for integer [value]: " + str(type(data["value"]))
                )
            if isinstance(data["product_id"], int):
                self.product_id = data["product_id"]
            else:
                raise DataValidationError(
                    "Invalid type for integer [product_id]: "
                    + str(type(data["product_id"]))
                )
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
        """Returns all of the Promotions in the database"""
        logger.info("Processing all Promotions")
        return cls.query.all()

    @classmethod
    def find(cls, by_id):
        """Finds a Promotion by it's ID"""
        logger.info("Processing lookup for id %s ...", by_id)
        return cls.query.session.get(cls, by_id)

    @classmethod
    def find_by_name(cls, name):
        """Returns all Promotions with the given name"""
        logger.info("Processing name query for %s ...", name)
        return cls.query.filter(cls.name == name).all()

    @classmethod
    def find_by_promotion_type(cls, promotion_type: str):
        """Returns all Promotions that match the given promotion_type exactly"""
        logger.info("Processing promotion_type query for %s ...", promotion_type)
        return cls.query.filter(cls.promotion_type == promotion_type).all()

    @classmethod
    def find_by_category(cls, category):
        """Returns all Promotions in a category (using product_id as category)
        Args:
            category: the product_id/category of the Promotions you want to match
        """
        logger.info("Processing category query for %s ...", category)
        try:
            product_id = int(category)
            return cls.query.filter(cls.product_id == product_id)
        except ValueError:
            return cls.query.filter(False)  # Return empty result for invalid product_id

    @classmethod
    def find_by_id(cls, promotion_id):
        """Returns all Promotions with the given id (single result in list)
        Args:
            promotion_id: the id of the Promotion you want to match
        """
        logger.info("Processing id query for %s ...", promotion_id)
        try:
            pid = int(promotion_id)
            promotion = cls.query.session.get(cls, pid)
            return [promotion] if promotion else []
        except (ValueError, TypeError):
            return []

