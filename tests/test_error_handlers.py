"""
Test cases for Error Handlers
"""
from unittest import TestCase
from unittest.mock import patch
from wsgi import app
from service.common import status
from service.models import db, Promotion, DatabaseError


class TestErrorHandlers(TestCase):
    """Error Handler Tests"""

    @classmethod
    def setUpClass(cls):
        """This runs once before the entire test suite"""
        app.config["TESTING"] = True
        app.config["DEBUG"] = False
        app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///:memory:"
        app.app_context().push()
        db.create_all()

    @classmethod
    def tearDownClass(cls):
        """This runs once after the entire test suite"""
        db.session.close()

    def setUp(self):
        """Runs before each test"""
        self.client = app.test_client()
        db.session.query(Promotion).delete()
        db.session.commit()

    def test_request_validation_error(self):
        """It should handle a DataValidationError"""
        resp = self.client.post("/promotions", json={"name": "test"})
        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("Invalid promotion: missing promotion_type", resp.get_json()["message"])

    def test_bad_request(self):
        """It should handle a bad request"""
        resp = self.client.post("/promotions", data="not json", content_type="application/json")
        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)

    def test_not_found(self):
        """It should handle a not found error"""
        resp = self.client.get("/foo")
        self.assertEqual(resp.status_code, status.HTTP_404_NOT_FOUND)

    def test_method_not_allowed(self):
        """It should handle a method not allowed error"""
        resp = self.client.put("/")
        self.assertEqual(resp.status_code, status.HTTP_405_METHOD_NOT_ALLOWED)

    def test_media_type_not_supported(self):
        """It should handle a media type not supported error"""
        resp = self.client.post("/promotions", data="foo", content_type="text/html")
        self.assertEqual(resp.status_code, status.HTTP_415_UNSUPPORTED_MEDIA_TYPE)

    @patch("service.models.Promotion.create")
    def test_database_error(self, mock_create):
        """It should handle a database error"""
        mock_create.side_effect = DatabaseError("Database error")
        json_data = {
            "name": "test",
            "promotion_type": "BOGO",
            "value": 10,
            "product_id": 123,
            "start_date": "2025-01-01",
            "end_date": "2025-01-02"
        }
        resp = self.client.post("/promotions", json=json_data)
        self.assertEqual(resp.status_code, status.HTTP_500_INTERNAL_SERVER_ERROR)

    @patch("service.routes.Promotion.all")
    def test_internal_server_error(self, mock_all):
        """It should handle an internal server error"""
        mock_all.side_effect = DatabaseError("Internal server error")
        resp = self.client.get("/promotions")
        self.assertEqual(resp.status_code, status.HTTP_500_INTERNAL_SERVER_ERROR)
