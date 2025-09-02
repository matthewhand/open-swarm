#!/usr/bin/env python3
"""
Run pytest in a stable way across environments:
- Disable auto plugin autoload (blocks problematic global plugins)
- Explicitly enable required plugins: pytest-django, pytest-asyncio, pytest-mock

Usage:
  python scripts/run_tests.py [pytest args]
  # or
  ./scripts/run_tests.py -q
"""
import os
import sys

def main() -> int:
    # Only set if not explicitly overridden by user
    os.environ.setdefault("PYTEST_DISABLE_PLUGIN_AUTOLOAD", "1")
    # Ensure Django allows async operations during tests without requiring pytest-env
    os.environ.setdefault("DJANGO_ALLOW_ASYNC_UNSAFE", "true")

    try:
        import pytest  # noqa: WPS433
    except Exception as exc:  # pragma: no cover
        print(f"Error: pytest not available: {exc}", file=sys.stderr)
        return 1

    args = [
        "-p", "django",
        "-p", "asyncio",
        "-p", "pytest_mock",
    ] + sys.argv[1:]
    return int(pytest.main(args))


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
