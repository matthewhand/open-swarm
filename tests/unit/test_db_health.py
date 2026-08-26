"""
Tests for database health check utilities.
"""

import os
from unittest.mock import MagicMock, patch

import pytest

from swarm.utils.db_health import check_database_health, enforce_database_health_on_startup


class TestDatabaseHealthCheck:
    """Test database health check functionality."""

    def test_no_database_url_returns_healthy(self):
        """When DATABASE_URL is not set, SQLite fallback is assumed healthy."""
        with patch.dict(os.environ, {}, clear=True):
            is_healthy, error = check_database_health()
            assert is_healthy is True
            assert error == ""

    def test_non_postgres_url_returns_healthy(self):
        """Non-Postgres URLs (e.g., mysql://) are not validated."""
        with patch.dict(os.environ, {"DATABASE_URL": "mysql://user:pass@localhost/db"}):
            is_healthy, error = check_database_health()
            assert is_healthy is True
            assert error == ""

    @patch("swarm.utils.db_health.psycopg2")
    def test_healthy_postgres_connection(self, mock_psycopg2):
        """A successful Postgres connection returns healthy."""
        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_conn.cursor.return_value = mock_cursor
        mock_psycopg2.connect.return_value = mock_conn

        with patch.dict(
            os.environ, {"DATABASE_URL": "postgresql://user:pass@localhost:5432/db"}
        ):
            is_healthy, error = check_database_health()

        assert is_healthy is True
        assert error == ""
        mock_cursor.execute.assert_called_once_with("SELECT 1")
        mock_cursor.close.assert_called_once()
        mock_conn.close.assert_called_once()

    @patch("swarm.utils.db_health.psycopg2")
    def test_quota_exceeded_error_detected(self, mock_psycopg2):
        """Neon quota-exceeded errors are detected and reported."""
        import psycopg2

        mock_psycopg2.connect.side_effect = psycopg2.OperationalError(
            "compute time quota exceeded"
        )

        with patch.dict(
            os.environ, {"DATABASE_URL": "postgresql://user:pass@neon.tech:5432/db"}
        ):
            is_healthy, error = check_database_health()

        assert is_healthy is False
        assert "quota-exceeded" in error.lower()
        assert "IMMEDIATE ACTION REQUIRED" in error
        assert "systemctl" in error

    @patch("swarm.utils.db_health.psycopg2")
    def test_generic_connection_error(self, mock_psycopg2):
        """Generic connection errors are reported with helpful message."""
        import psycopg2

        mock_psycopg2.connect.side_effect = psycopg2.OperationalError(
            "could not connect to server"
        )

        with patch.dict(
            os.environ, {"DATABASE_URL": "postgresql://user:pass@localhost:5432/db"}
        ):
            is_healthy, error = check_database_health()

        assert is_healthy is False
        assert "Database connection failed" in error
        assert "could not connect to server" in error

    @patch("swarm.utils.db_health.psycopg2", None)
    def test_psycopg2_not_installed(self):
        """If psycopg2 is not available, health check is skipped."""
        with patch.dict(
            os.environ, {"DATABASE_URL": "postgresql://user:pass@localhost:5432/db"}
        ):
            with patch("swarm.utils.db_health.logger") as mock_logger:
                is_healthy, error = check_database_health()

        assert is_healthy is True
        assert error == ""
        mock_logger.warning.assert_called_once()

    @patch("swarm.utils.db_health.check_database_health")
    def test_enforce_exits_on_unhealthy(self, mock_check):
        """enforce_database_health_on_startup exits with code 78 on failure."""
        mock_check.return_value = (False, "Database is down")

        with pytest.raises(SystemExit) as exc_info:
            enforce_database_health_on_startup()

        assert exc_info.value.code == 78
        mock_check.assert_called_once()

    @patch("swarm.utils.db_health.check_database_health")
    def test_enforce_passes_on_healthy(self, mock_check):
        """enforce_database_health_on_startup does not exit when healthy."""
        mock_check.return_value = (True, "")

        # Should not raise
        enforce_database_health_on_startup()
        mock_check.assert_called_once()

    @patch("swarm.utils.db_health.check_database_health")
    def test_enforce_skipped_when_env_var_set(self, mock_check):
        """SKIP_DB_HEALTH_CHECK=true bypasses the check."""
        with patch.dict(os.environ, {"SKIP_DB_HEALTH_CHECK": "true"}):
            enforce_database_health_on_startup()

        # Should not have called the check
        mock_check.assert_not_called()
