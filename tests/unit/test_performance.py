"""
Performance and reliability tests for Donetick MCP server.
"""

import asyncio
import time

import httpx2 as httpx
import pytest
from pytest_httpx2 import HTTPXMock

from donetick_mcp.client import DonetickClient, TokenBucket

BASE = "https://test.donetick.com"


@pytest.fixture
def client():
    """Create a test client instance with a lower rate limit."""
    return DonetickClient(
        base_url=BASE,
        api_token="test-token",
        rate_limit_per_second=10.0,
        rate_limit_burst=10,
    )


@pytest.fixture
def fast_client():
    """Create a test client with high rate limit for performance tests."""
    return DonetickClient(
        base_url=BASE,
        api_token="test-token",
        rate_limit_per_second=100.0,
        rate_limit_burst=100,
    )


@pytest.fixture
def sample_chore_data():
    """Sample chore data for testing."""
    return {
        "id": 1,
        "name": "Test Chore",
        "description": "Test description",
        "frequencyType": "once",
        "frequency": 1,
        "frequencyMetadata": {},
        "nextDueDate": "2025-11-10T00:00:00Z",
        "isRolling": False,
        "assignedTo": 1,
        "assignees": [{"userId": 1}],
        "assignStrategy": "least_completed",
        "isActive": True,
        "notification": False,
        "notificationMetadata": {"nagging": False, "predue": False},
        "labels": None,
        "labelsV2": [],
        "circleId": 1,
        "createdAt": "2025-11-03T00:00:00Z",
        "updatedAt": "2025-11-03T00:00:00Z",
        "createdBy": 1,
        "updatedBy": 1,
        "status": "active",
        "priority": 2,
        "isPrivate": False,
        "points": None,
        "subTasks": [],
        "thingChore": None,
    }


class TestRateLimiting:
    @pytest.mark.asyncio
    async def test_rate_limiting_respected(self, client, sample_chore_data, httpx_mock: HTTPXMock):
        for _ in range(20):
            httpx_mock.add_response(url=f"{BASE}/eapi/v1/chore", json=[sample_chore_data])

        async with client:
            start_time = time.perf_counter()
            tasks = [client.list_chores() for _ in range(20)]
            results = await asyncio.gather(*tasks)
            elapsed = time.perf_counter() - start_time

            assert len(results) == 20
            assert all(len(r) == 1 for r in results)
            # Token bucket allows burst of 10, then refills at 10/sec
            assert elapsed >= 0.8, f"Requests completed too fast ({elapsed:.2f}s)"
            assert elapsed <= 3.0, f"Requests took too long ({elapsed:.2f}s)"

    @pytest.mark.asyncio
    async def test_token_bucket_refill(self):
        bucket = TokenBucket(rate=10.0, capacity=10)
        await bucket.acquire(10)
        assert bucket.tokens == 0.0
        await asyncio.sleep(0.5)
        await bucket.acquire(1)
        assert bucket.tokens >= 3.0
        assert bucket.tokens <= 5.0


class TestConcurrentRequests:
    @pytest.mark.asyncio
    async def test_concurrent_requests_handling(self, fast_client, sample_chore_data, httpx_mock: HTTPXMock):
        for _ in range(5):
            httpx_mock.add_response(url=f"{BASE}/eapi/v1/chore", json=[sample_chore_data])
        for i in range(1, 6):
            httpx_mock.add_response(url=f"{BASE}/api/v1/chores/{i}", json={**sample_chore_data, "id": i})

        async with fast_client:
            start = time.perf_counter()
            tasks = [fast_client.list_chores() for _ in range(5)] + [fast_client.get_chore(i) for i in range(1, 6)]
            results = await asyncio.gather(*tasks)
            elapsed = time.perf_counter() - start

            assert len(results) == 10
            assert all(len(r) == 1 for r in results[:5])
            for i, r in enumerate(results[5:], start=1):
                assert r is not None and r.id == i
            assert elapsed < 2.0

    @pytest.mark.asyncio
    async def test_connection_pooling(self, fast_client, sample_chore_data, httpx_mock: HTTPXMock):
        for _ in range(60):
            httpx_mock.add_response(url=f"{BASE}/eapi/v1/chore", json=[sample_chore_data])

        async with fast_client:
            results = []
            for _ in range(3):
                tasks = [fast_client.list_chores() for _ in range(20)]
                results.extend(await asyncio.gather(*tasks))
            assert len(results) == 60
            assert all(len(r) == 1 for r in results)


class TestTokenAuth:
    @pytest.mark.asyncio
    async def test_invalid_token_raises(self, fast_client, sample_chore_data, httpx_mock: HTTPXMock):
        httpx_mock.add_response(url=f"{BASE}/eapi/v1/chore", status_code=401, json={"error": "API token required"})
        async with fast_client:
            with pytest.raises(httpx.HTTPStatusError):
                await fast_client.list_chores()


class TestRetryBackoff:
    @pytest.mark.asyncio
    async def test_retry_exponential_backoff(self, fast_client, sample_chore_data, httpx_mock: HTTPXMock):
        httpx_mock.add_response(url=f"{BASE}/eapi/v1/chore", status_code=500, json={"error": "err"})
        httpx_mock.add_response(url=f"{BASE}/eapi/v1/chore", status_code=500, json={"error": "err"})
        httpx_mock.add_response(url=f"{BASE}/eapi/v1/chore", json=[sample_chore_data])

        async with fast_client:
            start = time.perf_counter()
            chores = await fast_client.list_chores()
            elapsed = time.perf_counter() - start

            assert len(chores) == 1
            assert elapsed >= 2.0
            assert elapsed <= 5.0

    @pytest.mark.asyncio
    async def test_retry_timeout_with_backoff(self, fast_client, sample_chore_data, httpx_mock: HTTPXMock):
        httpx_mock.add_exception(httpx.TimeoutException("Request timeout"))
        httpx_mock.add_exception(httpx.TimeoutException("Request timeout"))
        httpx_mock.add_response(url=f"{BASE}/eapi/v1/chore", json=[sample_chore_data])

        async with fast_client:
            chores = await fast_client.list_chores()
            assert len(chores) == 1


class TestLargePayloads:
    @pytest.mark.asyncio
    async def test_large_payload_handling(self, fast_client, httpx_mock: HTTPXMock):
        large_response = [
            {
                "id": i + 1,
                "name": f"Chore {i + 1}",
                "description": None,
                "frequencyType": "weekly",
                "frequency": 1,
                "frequencyMetadata": {},
                "nextDueDate": "2025-11-10T00:00:00Z",
                "isRolling": False,
                "assignedTo": (i % 5) + 1,
                "assignees": [{"userId": (i % 5) + 1}],
                "assignStrategy": "least_completed",
                "isActive": True,
                "notification": False,
                "notificationMetadata": {},
                "labels": None,
                "labelsV2": [],
                "circleId": 1,
                "createdAt": "2025-11-03T00:00:00Z",
                "updatedAt": "2025-11-03T00:00:00Z",
                "createdBy": 1,
                "updatedBy": 1,
                "status": "active",
                "priority": 2,
                "isPrivate": False,
                "points": None,
                "subTasks": [],
                "thingChore": None,
            }
            for i in range(100)
        ]

        httpx_mock.add_response(url=f"{BASE}/eapi/v1/chore", json=large_response)

        async with fast_client:
            chores = await fast_client.list_chores()
            assert len(chores) == 100
            assert chores[0].id == 1
            assert chores[99].name == "Chore 100"

    @pytest.mark.asyncio
    async def test_large_things_response(self, fast_client, httpx_mock: HTTPXMock):
        large_things = [{"id": i + 1, "name": f"thing_{i + 1}", "state": str(i), "type": "number"} for i in range(50)]
        httpx_mock.add_response(url=f"{BASE}/eapi/v1/things/", json=large_things)
        async with fast_client:
            things = await fast_client.list_things()
            assert len(things) == 50
            assert things[0].name == "thing_1"
            assert things[49].name == "thing_50"
