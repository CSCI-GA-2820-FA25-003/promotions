"""Unit tests for custom API error handlers."""

from unittest.mock import patch

from wsgi import app
from service.common import error_handlers, status
from service.models import DataValidationError, DatabaseError


def test_request_validation_error_returns_json_and_logs():
    """request_validation_error should log and return structured 400 JSON."""
    with app.app_context(), patch.object(app.logger, "error") as mock_log:
        body, code = error_handlers.request_validation_error(DataValidationError("bad input"))

    assert code == status.HTTP_400_BAD_REQUEST
    assert body["status_code"] == status.HTTP_400_BAD_REQUEST
    assert body["error"] == "Bad Request"
    assert "bad input" in body["message"]
    mock_log.assert_called_once()


def test_database_connection_error_returns_json_and_logs():
    """database_connection_error should log and return structured 503 JSON."""
    with app.app_context(), patch.object(app.logger, "critical") as mock_log:
        body, code = error_handlers.database_connection_error(DatabaseError("db down"))

    assert code == status.HTTP_503_SERVICE_UNAVAILABLE
    assert body["status_code"] == status.HTTP_503_SERVICE_UNAVAILABLE
    assert body["error"] == "Service Unavailable"
    assert "db down" in body["message"]
    mock_log.assert_called_once()
