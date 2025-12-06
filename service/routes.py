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
Promotions Service

This service implements a REST API that allows you to Create, Read, Update,
Delete and List Promotions
"""

# Standard library
from datetime import date, timedelta

# Third-party
from flask import current_app as app, jsonify, request
from sqlalchemy import or_
from flask_restx import Api, Resource, fields, reqparse

# First-party
from service.common import status  # HTTP status codes
from service.models import DataValidationError, Promotion


######################################################################
# Utility Functions
######################################################################
def abort(error_code: int, message: str):
    """Logs errors before aborting"""
    app.logger.error(message)
    api.abort(error_code, message)


def _parse_bool_strict(value: str):
    """
    Strictly parse query-string boolean.
    Accepted (case-insensitive, trimmed):
      True:  'true', '1', 'yes'
      False: 'false', '0', 'no'
    Others: return None (caller should raise 400)
    """
    v = str(value).strip().lower()
    if v in {"true", "1", "yes"}:
        return True
    if v in {"false", "0", "no"}:
        return False
    return None


######################################################################
# Configure Swagger before initializing it
######################################################################
api = Api(
    app,
    version="1.0.0",
    title="Promotions REST API Service",
    description="This is a Promotions service for managing promotional campaigns.",
    default="promotions",
    default_label="Promotions operations",
    doc="/apidocs",
    prefix="/api",
)


######################################################################
# Define Swagger models
######################################################################
# Model for creating a promotion (no id field)
create_promotion_model = api.model(
    "Promotion",
    {
        "name": fields.String(required=True, description="The name of the promotion"),
        "promotion_type": fields.String(
            required=True,
            description="The type of promotion",
            enum=["BOGO", "DISCOUNT", "PERCENT"],
        ),
        "value": fields.Integer(required=True, description="The value of the promotion"),
        "product_id": fields.Integer(required=True, description="The product ID this promotion applies to"),
        "start_date": fields.Date(required=True, description="The start date of the promotion"),
        "end_date": fields.Date(required=True, description="The end date of the promotion"),
        "img_url": fields.String(
            required=False,
            description="Optional image URL for displaying the promotion",
        ),
    },
)

# Model for promotion responses (includes id)
promotion_model = api.inherit(
    "PromotionModel",
    create_promotion_model,
    {
        "id": fields.Integer(readOnly=True, description="The unique id assigned by the service"),
    },
)

# Query string arguments for list/filter
promotion_args = reqparse.RequestParser()
promotion_args.add_argument("id", type=int, location="args", required=False, help="Filter by promotion ID")
promotion_args.add_argument("name", type=str, location="args", required=False, help="Filter by name")
promotion_args.add_argument("product_id", type=int, location="args", required=False, help="Filter by product ID")
promotion_args.add_argument("promotion_type", type=str, location="args", required=False, help="Filter by promotion type")
promotion_args.add_argument("active", type=str, location="args", required=False, help="Filter by active status (true/false)")


######################################################################
# Configure the Root route before OpenAPI
######################################################################
@app.route("/")
def index():
    """Index page"""
    return app.send_static_file("index.html")


######################################################################
# API Root endpoint (Flask-RESTX Resource)
######################################################################
@api.route("/", strict_slashes=False)
class ApiIndex(Resource):
    """Root URL for the API"""
    def get(self):
        """Return API information"""
        return {
            "name": "Promotions Service",
            "version": "1.0.0",
            "description": "RESTful service for managing promotions",
            "paths": {
                "promotions": "/promotions",
            },
        }, status.HTTP_200_OK


######################################################################
# Promotion Collection Resource
######################################################################
@api.route("/promotions", strict_slashes=False)
class PromotionCollection(Resource):
    """Handles all interactions with collections of Promotions"""

    @api.doc("list_promotions")
    @api.expect(promotion_args, validate=False)
    @api.marshal_list_with(promotion_model)
    def get(self):
        """
        List Promotions
        Returns a list of Promotions based on query parameters
        """
        app.logger.info("Request to list Promotions")

        filters = {
            "id": lambda: [Promotion.find(request.args.get("id"))] if Promotion.find(request.args.get("id")) else [],
            "active": lambda: _get_active_promotions(request.args.get("active")),
            "name": lambda: Promotion.find_by_name(request.args.get("name").strip()),
            "product_id": lambda: _get_promotions_by_product_id(request.args.get("product_id")),
            "promotion_type": lambda: Promotion.find_by_promotion_type(request.args.get("promotion_type").strip()),
        }

        for param, filter_func in filters.items():
            if request.args.get(param):
                promotions = filter_func()
                break
        else:
            promotions = Promotion.all()

        results = [p.serialize() for p in promotions]
        return results, status.HTTP_200_OK

    @api.doc("create_promotion")
    @api.response(400, "Bad Request")
    @api.expect(create_promotion_model)
    @api.marshal_with(promotion_model, code=201)
    def post(self):
        """
        Create a Promotion
        Creates a new Promotion from the request payload
        """
        app.logger.info("Request to Create a Promotion")
        check_content_type("application/json")

        promotion = Promotion()
        try:
            data = request.get_json()
            app.logger.info("Processing: %s", data)
            promotion.deserialize(data)
            promotion.create()
        except DataValidationError as error:
            abort(status.HTTP_400_BAD_REQUEST, str(error))

        location_url = api.url_for(PromotionResource, promotion_id=promotion.id, _external=True)
        return (
            promotion.serialize(),
            status.HTTP_201_CREATED,
            {"Location": location_url},
        )


def _get_active_promotions(active_raw):
    active = _parse_bool_strict(active_raw)
    if active is None:
        abort(
            status.HTTP_400_BAD_REQUEST,
            (
                "Invalid value for query parameter 'active'. "
                "Accepted: true, false, 1, 0, yes, no (case-insensitive). "
                f"Received: {active_raw!r}"
            ),
        )

    today = date.today()
    if active is True:
        app.logger.info("Filtering by active promotions (inclusive)")
        return Promotion.find_active()
    app.logger.info("Filtering by inactive promotions (not active today)")
    return list(
        Promotion.query.filter(
            or_(Promotion.start_date > today, Promotion.end_date < today)
        ).all()
    )


def _get_promotions_by_product_id(product_id):
    """Get promotions by product_id, validating the input"""
    try:
        pid = int(product_id)
    except ValueError:
        abort(status.HTTP_400_BAD_REQUEST, f"Invalid value for query parameter 'product_id': {product_id}")
    return Promotion.find_by_product_id(pid)


######################################################################
# Promotion Resource
######################################################################
@api.route("/promotions/<int:promotion_id>")
@api.param("promotion_id", "The Promotion identifier")
class PromotionResource(Resource):
    """Handles interactions with a single Promotion"""

    @api.doc("get_promotion")
    @api.response(404, "Promotion not found")
    @api.marshal_with(promotion_model)
    def get(self, promotion_id):
        """
        Get a Promotion
        Returns a single Promotion by ID
        """
        app.logger.info("Request to get Promotion with id [%s]", promotion_id)
        promotion = Promotion.find(promotion_id)
        if not promotion:
            abort(
                status.HTTP_404_NOT_FOUND,
                f"Promotion with id '{promotion_id}' was not found.",
            )
        return promotion.serialize(), status.HTTP_200_OK

    @api.doc("update_promotion")
    @api.response(404, "Promotion not found")
    @api.response(400, "Bad Request")
    @api.expect(create_promotion_model)
    @api.marshal_with(promotion_model)
    def put(self, promotion_id):
        """
        Update a Promotion
        Updates an existing Promotion with the provided data
        """
        app.logger.info("Request to update Promotion with id [%s]", promotion_id)
        check_content_type("application/json")

        promotion = Promotion.find(promotion_id)
        if not promotion:
            abort(
                status.HTTP_404_NOT_FOUND,
                f"Promotion with id '{promotion_id}' was not found.",
            )

        try:
            data = request.get_json()
            app.logger.info("Processing: %s", data)
            # Optional strictness: if client provides id and it disagrees with path
            if "id" in data and str(data["id"]) != str(promotion_id):
                abort(status.HTTP_400_BAD_REQUEST, "ID in body must match resource path")
            promotion.deserialize(data)
            promotion.id = promotion_id  # ensure path id takes precedence
            promotion.update()
        except DataValidationError as error:
            abort(status.HTTP_400_BAD_REQUEST, str(error))

        return promotion.serialize(), status.HTTP_200_OK

    @api.doc("delete_promotion")
    @api.response(204, "Promotion deleted")
    @api.response(404, "Promotion not found")
    def delete(self, promotion_id):
        """
        Delete a Promotion
        Deletes a Promotion by ID
        """
        app.logger.info("Request to delete Promotion with id [%s]", promotion_id)
        promotion = Promotion.find(promotion_id)
        if not promotion:
            abort(
                status.HTTP_404_NOT_FOUND,
                f"Promotion with id '{promotion_id}' was not found.",
            )

        promotion.delete()
        return "", status.HTTP_204_NO_CONTENT


######################################################################
# Deactivate Action Resource
######################################################################
@api.route("/promotions/<int:promotion_id>/deactivate")
@api.param("promotion_id", "The Promotion identifier")
class DeactivateResource(Resource):
    """Deactivate action on a Promotion"""

    @api.doc("deactivate_promotion")
    @api.response(404, "Promotion not found")
    @api.response(400, "Bad Request")
    @api.marshal_with(promotion_model)
    def put(self, promotion_id):
        """
        Deactivate a Promotion
        Sets the end_date to yesterday to make it inactive
        """
        app.logger.info("Request to deactivate Promotion with id [%s]", promotion_id)
        promotion = Promotion.find(promotion_id)
        if not promotion:
            abort(
                status.HTTP_404_NOT_FOUND,
                f"Promotion with id '{promotion_id}' was not found.",
            )

        try:
            yesterday = date.today() - timedelta(days=1)
            # never extend a promotion that already ended earlier than yesterday
            promotion.end_date = min(promotion.end_date, yesterday)
            promotion.update()
        except DataValidationError as error:
            abort(status.HTTP_400_BAD_REQUEST, str(error))

        return promotion.serialize(), status.HTTP_200_OK


######################################################################
# Utility: Content-Type guard
######################################################################
def check_content_type(content_type: str):
    """Checks that the media type is correct (tolerates charset etc.)"""
    # Werkzeug exposes parsed mimetype; if header missing, this is None
    if request.mimetype != content_type:
        got = request.content_type or "none"
        abort(
            status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
            f"Content-Type must be {content_type}; received {got}",
        )


######################################################################
# Endpoint: /health (K8s liveness/readiness)
######################################################################
@app.route("/health", methods=["GET"])
def health():
    """
    K8s health check endpoint
    Returns:
        JSON: {"status": "OK"} with HTTP 200
    Notes:
        - Keep this endpoint lightweight and independent of external deps (e.g., DB)
          so that liveness/readiness probes are stable .
    """
    app.logger.info("Health check requested")
    return jsonify(status="OK"), status.HTTP_200_OK
