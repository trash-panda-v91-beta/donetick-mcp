"""
End-to-end integration tests for realistic workflow scenarios.

Covers the chore lifecycle (create via External API; get/update/complete/delete
via the Full API) and user lookup + assignment.
"""

import pytest
from pytest_httpx2 import HTTPXMock

from donetick_mcp.client import DonetickClient
from donetick_mcp.models import ChoreUpdate

BASE = "https://test.donetick.com"


@pytest.fixture
def client():
    return DonetickClient(
        base_url=BASE,
        api_token="test-token",
        rate_limit_per_second=100.0,
        rate_limit_burst=100,
    )


def chore_response(**overrides):
    """A full chore response dict with sensible defaults."""
    base = {
        "id": 1,
        "name": "Vacuum Living Room",
        "description": "Clean the carpets",
        "frequencyType": "weekly",
        "frequency": 1,
        "frequencyMetadata": {},
        "nextDueDate": "2025-11-10T00:00:00Z",
        "isRolling": False,
        "assignedTo": 1,
        "assignees": [{"userId": 1}],
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
    base.update(overrides)
    return base


class TestFullChoreLifecycle:
    @pytest.mark.asyncio
    async def test_full_chore_lifecycle(self, client, httpx_mock: HTTPXMock):
        # Create via External API - returns the chore directly
        httpx_mock.add_response(url=f"{BASE}/eapi/v1/chore", json=chore_response(), method="POST")
        # Get / update fetch
        httpx_mock.add_response(url=f"{BASE}/api/v1/chores/1", json=chore_response())
        # PUT full object, API replies message-only
        httpx_mock.add_response(
            url=f"{BASE}/api/v1/chores/", json={"message": "Chore added successfully"}, method="PUT"
        )
        # Re-fetch updated
        httpx_mock.add_response(
            url=f"{BASE}/api/v1/chores/1",
            json=chore_response(description="Clean carpets thoroughly", priority=3),
        )

        async with client:
            created = await client.create_chore(name="Vacuum Living Room", description="Clean the carpets")
            assert created.id == 1
            assert created.name == "Vacuum Living Room"

            updated = await client.update_chore(1, ChoreUpdate(description="Clean carpets thoroughly", priority=3))
            assert updated.description == "Clean carpets thoroughly"
            assert updated.priority == 3

            # Complete
            httpx_mock.add_response(
                url=f"{BASE}/api/v1/chores/1/do",
                json=chore_response(nextDueDate="2025-11-17T00:00:00Z"),
                method="POST",
            )
            completed = await client.complete_chore(1)
            assert completed.nextDueDate == "2025-11-17T00:00:00Z"

            # Delete
            httpx_mock.add_response(url=f"{BASE}/eapi/v1/chore/1", json={}, method="DELETE")
            assert await client.delete_chore(1) is True


class TestUserLookupAndAssignment:
    @pytest.mark.asyncio
    async def test_lookup_users_and_reassign(self, client, httpx_mock: HTTPXMock):
        members = [
            {
                "id": 1,
                "userId": 10,
                "circleId": 1,
                "role": "admin",
                "isActive": True,
                "username": "alice",
                "displayName": "Alice Smith",
                "points": 100,
                "pointsRedeemed": 0,
            },
            {
                "id": 2,
                "userId": 11,
                "circleId": 1,
                "role": "member",
                "isActive": True,
                "username": "bob",
                "displayName": "Bob Jones",
                "points": 50,
                "pointsRedeemed": 0,
            },
        ]
        httpx_mock.add_response(url=f"{BASE}/api/v1/circles/members", json=members)

        async with client:
            user_map = await client.lookup_user_ids(["alice", "Bob Jones"])
            assert user_map == {"alice": 10, "Bob Jones": 11}

            # Reassign chore 1 to Bob
            httpx_mock.add_response(url=f"{BASE}/api/v1/chores/1", json=chore_response())
            httpx_mock.add_response(
                url=f"{BASE}/api/v1/chores/", json={"message": "Chore added successfully"}, method="PUT"
            )
            httpx_mock.add_response(
                url=f"{BASE}/api/v1/chores/1",
                json=chore_response(assignedTo=11, assignees=[{"userId": 11}]),
            )
            reassigned = await client.update_chore_assignee(1, 11)
            assert reassigned.assignedTo == 11
