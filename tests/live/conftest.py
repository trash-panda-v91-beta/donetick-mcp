"""Pytest configuration and fixtures for live API integration tests."""

import os
from collections.abc import AsyncGenerator

import pytest

from donetick_mcp.client import DonetickClient
from donetick_mcp.config import Config


@pytest.fixture(scope="session")
def live_config() -> Config:
    """
    Load configuration from environment variables for live testing.

    This fixture validates that all required credentials are present
    before any live tests run.

    Returns:
        Config: Validated configuration instance

    Raises:
        ValueError: If required environment variables are missing
    """
    config = Config()

    # Validate required variables are present
    if not config.donetick_base_url:
        pytest.skip("DONETICK_BASE_URL not set - skipping live API tests")

    if not config.donetick_api_token:
        pytest.skip("DONETICK_API_TOKEN not set - skipping live API tests")

    return config


@pytest.fixture
async def live_client(live_config: Config) -> AsyncGenerator[DonetickClient]:
    """
    Create a DonetickClient instance connected to a real Donetick instance.

    This fixture initializes an authenticated client and ensures proper cleanup
    after tests complete. The client uses the credentials from environment variables.

    Args:
        live_config: Configuration loaded from environment

    Yields:
        DonetickClient: Authenticated client connected to live API

    Note:
        The client is automatically closed after the test completes, ensuring
        no connection leaks.
    """
    client = DonetickClient(
        base_url=live_config.donetick_base_url,
        api_token=live_config.donetick_api_token,
        rate_limit_per_second=live_config.rate_limit_per_second,
        rate_limit_burst=live_config.rate_limit_burst,
    )

    yield client

    # Cleanup: close client connections
    await client.close()


@pytest.fixture
async def test_chore_ids(live_client: DonetickClient) -> AsyncGenerator[list[int]]:
    """
    Track test chore IDs for cleanup after tests.

    This fixture maintains a list of chore IDs created during tests and
    automatically deletes them after the test completes. This ensures
    tests don't leave behind test data in the live instance.

    Usage in tests:
        ```python
        async def test_create_chore(live_client, test_chore_ids):
            chore = await live_client.create_chore(...)
            test_chore_ids.append(chore.id)
            # ... test logic ...
        ```

    Args:
        live_client: Authenticated client for cleanup

    Yields:
        List[int]: List to append test chore IDs to

    Note:
        Cleanup is attempted even if the test fails. If deletion fails,
        a warning is logged but the test is not failed.
    """
    chore_ids = []

    yield chore_ids

    # Cleanup: delete all test chores
    for chore_id in chore_ids:
        try:
            await live_client.delete_chore(chore_id)
        except Exception as e:
            # Log but don't fail the test if cleanup fails
            print(f"Warning: Failed to delete test chore {chore_id}: {e}")


@pytest.fixture
def test_user_id(live_config: Config) -> int:
    """
    Get the test user ID from environment variables.

    Some tests require knowing the current user's ID for creating chores.
    This can be set explicitly via DONETICK_TEST_USER_ID or will default to 1.

    Returns:
        int: User ID to use for testing

    Note:
        If your Donetick user ID is not 1, set DONETICK_TEST_USER_ID
        in your .env file.
    """
    return int(os.getenv("DONETICK_TEST_USER_ID", "1"))
