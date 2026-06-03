import os
import unittest
from unittest.mock import patch, MagicMock

# Import from src
import sys
from pathlib import Path
src_path = str(Path(__file__).resolve().parent.parent.parent / "src")
if src_path not in sys.path:
    sys.path.insert(0, src_path)

from swarm.utils.env_utils import get_test_user_password

class TestSecurityFix(unittest.TestCase):
    def test_get_test_user_password_default(self):
        """Test that get_test_user_password returns 'testpass' by default."""
        with patch.dict(os.environ, {}, clear=True):
            self.assertEqual(get_test_user_password(), "testpass")

    def test_get_test_user_password_custom(self):
        """Test that get_test_user_password reads from environment variable."""
        with patch.dict(os.environ, {"SWARM_TEST_USER_PASSWORD": "custom_password"}):
            self.assertEqual(get_test_user_password(), "custom_password")

if __name__ == "__main__":
    unittest.main()
