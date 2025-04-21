#!/bin/bash
# Remove Django test databases in /tmp to avoid readonly/corruption errors
# Usage: source this or run before pytest/uv run pytest

find /tmp -type f -name 'test*.sqlite3' -delete
find /tmp -type f -name 'test*' -delete
