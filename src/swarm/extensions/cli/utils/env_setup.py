# Handles .env management and environment validation for the CLI

import os
from dotenv import load_dotenv

def validate_env():
    """Ensure all required environment variables are set. In test mode, auto-pass or set dummies."""
    load_dotenv()
    required_vars = ["API_KEY", "MCP_SERVER"]
    # If running under test, auto-set dummy values and pass
    if os.getenv("SWARM_TEST_MODE") == "1":
        for var in required_vars:
            if not os.getenv(var):
                os.environ[var] = f"dummy_{var.lower()}"
        print("[TEST MODE] Environment validation auto-passed with dummy values.")
        return True
    missing = [var for var in required_vars if not os.getenv(var)]
    if missing:
        print(f"Missing required environment variables: {', '.join(missing)}")
        return False
    print("Environment validation passed.")
    return True
