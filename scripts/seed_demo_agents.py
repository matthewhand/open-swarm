#!/usr/bin/env python3
"""Reset / seed labeled Demo agents (REQ-135). Same path as seed_req156_demo.py."""

from __future__ import annotations

import sys
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parent
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

from seed_req156_demo import main  # noqa: E402


if __name__ == "__main__":
    raise SystemExit(main())
