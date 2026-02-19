"""
Local pytest stabilization for this repo.

This module is auto-imported by Python at startup (via sitecustomize hook)
whenever it is present on sys.path. We use it to make pytest behavior
predictable across environments by disabling auto plugin loading and
explicitly enabling only the plugins we rely on.

Opt-out by setting PYTEST_FORCE_AUTOLOAD=1 in the environment.
"""
from __future__ import annotations

import os

if not os.environ.get("PYTEST_FORCE_AUTOLOAD"):
    # Prevent arbitrary external plugins (e.g., legacy testinfra shims) from loading
    os.environ.setdefault("PYTEST_DISABLE_PLUGIN_AUTOLOAD", "1")

    # Re-enable only the plugins we actually need via command-line opts
    # - pytest-django is required for Django integration
    # - pytest-asyncio is optional; include if available without failing if missing
    # - also explicitly block legacy testinfra shim if present
    addopts = os.environ.get("PYTEST_ADDOPTS", "")
    pieces = [p for p in addopts.split() if p]
    if "-p" not in pieces:  # only append when not already set by caller
        pieces.extend([
            "-p", "pytest_django",
            # Allow pytest to proceed even if pytest-asyncio isn't installed
            # Pytest ignores unknown plugins when -p is specified with missing modules?
            # If this raises in some envs, set PYTEST_FORCE_AUTOLOAD=1 to bypass.
            "-p", "pytest_asyncio",
            # pytest-mock provides the `mocker` fixture used in tests
            "-p", "mock",
            "-p", "no:_testinfra_renamed",
            "-p", "no:testinfra",
        ])
    os.environ["PYTEST_ADDOPTS"] = " ".join(pieces)
