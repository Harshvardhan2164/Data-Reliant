"""Shared test configuration and fixtures."""

from __future__ import annotations

import pytest


@pytest.fixture
def anyio_backend():
    """Use asyncio for async tests."""
    return "asyncio"
