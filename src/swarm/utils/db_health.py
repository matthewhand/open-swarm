"""
Database health check utilities.

Provides pre-startup database connectivity validation to prevent crash-looping
when DATABASE_URL points to a quota-exceeded or unavailable Postgres instance.
"""

import logging
import os
import sys
from typing import Optional

logger = logging.getLogger(__name__)


def check_database_health(database_url: Optional[str] = None) -> tuple[bool, str]:
    """Check database connectivity and quota status before Django starts.
    
    Args:
        database_url: Database URL to check. If None, reads from DATABASE_URL env var.
        
    Returns:
        Tuple of (is_healthy, error_message). is_healthy=True means DB is accessible,
        False means it's not and error_message contains the reason.
        
    Common Neon quota-exceeded error indicators:
    - OperationalError with "compute time quota"
    - "Your compute endpoint exceeded its quota"
    - Connection refused after quota exhaustion
    """
    database_url = database_url or os.environ.get('DATABASE_URL')
    
    # No DATABASE_URL means SQLite fallback, which is always fine
    if not database_url:
        return True, ""
    
    # Only validate Postgres connections (Neon uses postgres:// scheme)
    if not database_url.startswith(('postgres://', 'postgresql://')):
        return True, ""
        
    try:
        import psycopg2
        from urllib.parse import urlparse
        
        parsed = urlparse(database_url)
        
        # Extract connection parameters
        conn_params = {
            'host': parsed.hostname,
            'port': parsed.port or 5432,
            'dbname': parsed.path.lstrip('/') if parsed.path else 'postgres',
            'user': parsed.username,
            'password': parsed.password,
            'connect_timeout': 10,
        }
        
        logger.info(
            "Checking database health: %s@%s:%s/%s",
            conn_params['user'],
            conn_params['host'],
            conn_params['port'],
            conn_params['dbname'],
        )
        
        # Attempt connection
        conn = psycopg2.connect(**conn_params)
        cursor = conn.cursor()
        cursor.execute("SELECT 1")
        cursor.close()
        conn.close()
        
        logger.info("Database health check passed")
        return True, ""
        
    except ImportError:
        # psycopg2 not installed (should not happen in production but be defensive)
        logger.warning("psycopg2 not available, skipping database health check")
        return True, ""
        
    except Exception as e:
        error_msg = str(e).lower()
        
        # Check for Neon-specific quota errors
        if any(indicator in error_msg for indicator in [
            'quota',
            'compute time',
            'compute endpoint',
            'suspended',
            'exceeded',
        ]):
            msg = (
                f"DATABASE_URL points to a quota-exceeded Neon Postgres instance: {e}\n\n"
                "IMMEDIATE ACTION REQUIRED:\n"
                "1. Stop this service to prevent crash-looping:\n"
                "   systemctl --user stop open-swarm-oracle.service\n"
                "   systemctl --user disable open-swarm-oracle.service\n\n"
                "2. Either:\n"
                "   a) Remove DATABASE_URL from the service environment to use local SQLite, OR\n"
                "   b) Point DATABASE_URL to a non-quota-stopped Postgres instance, OR\n"
                "   c) If this was a paid proxy, upgrade your Neon plan\n\n"
                "3. Update service file: /home/YOUR_USER/.config/systemd/user/open-swarm-oracle.service\n"
                "4. Reload and restart: systemctl --user daemon-reload && systemctl --user start open-swarm-oracle.service\n\n"
                "For local development, see docker-compose.postgres.yml for a local Postgres setup."
            )
            logger.error(msg)
            return False, msg
            
        # Other database errors
        msg = (
            f"Database connection failed: {e}\n\n"
            "Possible causes:\n"
            "- Database host is unreachable\n"
            "- Invalid credentials in DATABASE_URL\n"
            "- Network connectivity issues\n"
            "- Database server is down\n\n"
            "To use SQLite instead, remove DATABASE_URL from the environment.\n"
            "To use local Postgres, see docker-compose.postgres.yml."
        )
        logger.error(msg)
        return False, msg


def enforce_database_health_on_startup() -> None:
    """Enforce database health check on Django startup.
    
    Call this early in Django initialization (e.g., in manage.py or asgi.py)
    to prevent the server from starting when the database is unavailable.
    
    Exits with code 78 (EX_CONFIG) if the database is unhealthy, causing
    systemd to stop trying to restart the service after hitting RestartSec limits.
    
    Set SKIP_DB_HEALTH_CHECK=true to bypass this check (not recommended for production).
    """
    # Allow opt-out for testing or emergency situations
    if os.environ.get('SKIP_DB_HEALTH_CHECK', '').lower() in ('true', '1', 'yes'):
        logger.warning("Database health check skipped (SKIP_DB_HEALTH_CHECK is set)")
        return
        
    is_healthy, error_message = check_database_health()
    
    if not is_healthy:
        logger.critical(
            "=== DATABASE HEALTH CHECK FAILED ===\n"
            "%s\n"
            "=== EXITING TO PREVENT CRASH-LOOP ===",
            error_message
        )
        # Exit with EX_CONFIG (78) to signal configuration error to systemd
        # This is better than crash-looping with exit code 1
        sys.exit(78)
