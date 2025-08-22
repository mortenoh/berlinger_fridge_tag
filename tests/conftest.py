"""
Pytest configuration file for the Berlinger Fridge Tag API tests.
"""

import pytest
import asyncio
from pathlib import Path


@pytest.fixture(scope="session")
def test_data_dir():
    """Fixture providing the path to test data directory."""
    return Path(__file__).parent / "test_data"


@pytest.fixture(scope="session")
def event_loop():
    """Create an instance of the default event loop for the test session."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()
