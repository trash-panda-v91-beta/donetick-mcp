"""Root pytest config shared by unit/, integration/, and live/ suites.

The dummy env must live here (not in a per-suite conftest) because the
donetick_mcp.config singleton is instantiated at import of client/server, which
every suite triggers - so the vars must be set before any test module imports.
"""

import os

import pytest


def pytest_collection_modifyitems(items):
    if os.getenv("CI"):
        skip = pytest.mark.skip(reason="skipped in CI")
        for item in items:
            if "skip_in_ci" in item.keywords:
                item.add_marker(skip)


# Default to dummy values so the mocked suites collect without a .env; real
# shell/.env values (if present) win via setdefault.
os.environ.setdefault("DONETICK_BASE_URL", "https://donetick.example.com")
os.environ.setdefault("DONETICK_API_TOKEN", "test-token")
