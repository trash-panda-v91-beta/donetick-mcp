"""Unit tests for the Donetick client (token auth, external + full API)."""

import json

import httpx2 as httpx
import pytest
from pytest_httpx2 import HTTPXMock

from donetick_mcp.client import DonetickClient
from donetick_mcp.models import ChoreUpdate, ProjectUpdate


@pytest.fixture
def client():
    """A client using the config defaults (base URL from conftest)."""
    return DonetickClient()


SAMPLE_CHORE = {
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
    "status": 0,
    "priority": 2,
    "isPrivate": False,
    "points": None,
    "subTasks": [],
    "thingChore": None,
}

BASE = "https://donetick.example.com"


class TestTokenAuth:
    @pytest.mark.asyncio
    async def test_sends_secretkey_header(self):
        c = DonetickClient()
        assert c.api_token == "test-token"
        assert c.client.headers["secretkey"] == "test-token"
        await c.close()


class TestExternalChores:
    @pytest.mark.asyncio
    async def test_list_chores(self, client, httpx_mock: HTTPXMock):
        httpx_mock.add_response(url=f"{BASE}/eapi/v1/chore", json=[SAMPLE_CHORE])
        chores = await client.list_chores()
        assert len(chores) == 1
        assert chores[0].name == "Test Chore"

    @pytest.mark.asyncio
    async def test_list_chores_filters_active(self, client, httpx_mock: HTTPXMock):
        inactive = dict(SAMPLE_CHORE, id=2, isActive=False)
        httpx_mock.add_response(url=f"{BASE}/eapi/v1/chore", json=[SAMPLE_CHORE, inactive])
        chores = await client.list_chores(filter_active=True)
        assert len(chores) == 1
        assert chores[0].id == 1

    @pytest.mark.asyncio
    async def test_list_chores_empty(self, client, httpx_mock: HTTPXMock):
        httpx_mock.add_response(url=f"{BASE}/eapi/v1/chore", json=[])
        assert await client.list_chores() == []

    @pytest.mark.asyncio
    async def test_create_chore(self, client, httpx_mock: HTTPXMock):
        httpx_mock.add_response(url=f"{BASE}/eapi/v1/chore", json=SAMPLE_CHORE, method="POST")
        chore = await client.create_chore(name="Test Chore", description="desc", due_date="2025-11-10")
        assert chore.id == 1
        assert chore.name == "Test Chore"

    @pytest.mark.asyncio
    async def test_delete_chore(self, client, httpx_mock: HTTPXMock):
        httpx_mock.add_response(
            url=f"{BASE}/eapi/v1/chore/1", json={"message": "Chore deleted successfully"}, method="DELETE"
        )
        assert await client.delete_chore(1) is True


class TestFullApiGaps:
    @pytest.mark.asyncio
    async def test_get_chore(self, client, httpx_mock: HTTPXMock):
        httpx_mock.add_response(url=f"{BASE}/api/v1/chores/1", json={"res": SAMPLE_CHORE})
        chore = await client.get_chore(1)
        assert chore.id == 1

    @pytest.mark.asyncio
    async def test_get_chore_not_found(self, client, httpx_mock: HTTPXMock):
        httpx_mock.add_response(url=f"{BASE}/api/v1/chores/999", status_code=404)
        assert await client.get_chore(999) is None

    @pytest.mark.asyncio
    async def test_update_chore(self, client, httpx_mock: HTTPXMock):
        httpx_mock.add_response(url=f"{BASE}/api/v1/chores/1", json={"res": SAMPLE_CHORE})
        httpx_mock.add_response(
            url=f"{BASE}/api/v1/chores/", json={"message": "Chore added successfully"}, method="PUT"
        )
        httpx_mock.add_response(url=f"{BASE}/api/v1/chores/1", json={"res": {**SAMPLE_CHORE, "name": "Renamed"}})
        chore = await client.update_chore(1, ChoreUpdate(name="Renamed"))
        assert chore.id == 1

    @pytest.mark.asyncio
    async def test_complete_chore(self, client, httpx_mock: HTTPXMock):
        httpx_mock.add_response(url=f"{BASE}/api/v1/chores/1/do", json=SAMPLE_CHORE, method="POST")
        chore = await client.complete_chore(1)
        assert chore.id == 1

    @pytest.mark.asyncio
    async def test_update_priority_validation(self, client):
        with pytest.raises(ValueError, match="must be 0-4"):
            await client.update_chore_priority(1, 5)

    @pytest.mark.asyncio
    async def test_update_chore_priority_message_response(self, client, httpx_mock: HTTPXMock):
        # donetick replies {"message": ...}; client must re-fetch the chore
        httpx_mock.add_response(
            url=f"{BASE}/api/v1/chores/1/priority", json={"message": "Priority updated successfully"}, method="PUT"
        )
        httpx_mock.add_response(url=f"{BASE}/api/v1/chores/1", json=SAMPLE_CHORE)
        chore = await client.update_chore_priority(1, 4)
        assert chore.id == 1

    @pytest.mark.asyncio
    async def test_get_circle_members(self, client, httpx_mock: HTTPXMock):
        httpx_mock.add_response(
            url=f"{BASE}/api/v1/circles/members",
            json=[
                {
                    "id": 1,
                    "userId": 1,
                    "circleId": 1,
                    "role": "admin",
                    "isActive": True,
                    "username": "alice",
                    "displayName": "Alice",
                    "points": 10,
                    "pointsRedeemed": 2,
                }
            ],
        )
        members = await client.get_circle_members()
        assert members[0].username == "alice"

    @pytest.mark.asyncio
    async def test_lookup_user_ids(self, client, httpx_mock: HTTPXMock):
        httpx_mock.add_response(
            url=f"{BASE}/api/v1/circles/members",
            json=[
                {
                    "id": 1,
                    "userId": 5,
                    "circleId": 1,
                    "role": "member",
                    "isActive": True,
                    "username": "bob",
                    "displayName": "Bob Jones",
                    "points": 0,
                    "pointsRedeemed": 0,
                },
                {
                    "id": 2,
                    "userId": 7,
                    "circleId": 1,
                    "role": "member",
                    "isActive": True,
                    "username": "alice",
                    "displayName": "Alice",
                    "points": 0,
                    "pointsRedeemed": 0,
                },
            ],
        )
        assert await client.lookup_user_ids(["bob", "Alice"]) == {"bob": 5, "Alice": 7}

    @pytest.mark.asyncio
    async def test_skip_chore(self, client, httpx_mock: HTTPXMock):
        httpx_mock.add_response(
            url=f"{BASE}/api/v1/chores/1/skip", json={**SAMPLE_CHORE, "nextDueDate": "2025-11-17"}, method="POST"
        )
        chore = await client.skip_chore(1)
        assert chore.nextDueDate == "2025-11-17"

    @pytest.mark.asyncio
    async def test_get_chore_history(self, client, httpx_mock: HTTPXMock):
        httpx_mock.add_response(
            url=f"{BASE}/api/v1/chores/1/history",
            json=[
                {
                    "id": 1,
                    "choreId": 1,
                    "performedAt": "2025-11-05T10:00:00Z",
                    "completedBy": 1,
                    "assignedTo": 1,
                    "note": None,
                    "dueDate": "2025-11-05",
                }
            ],
        )
        history = await client.get_chore_history(1)
        assert len(history) == 1
        assert history[0].choreId == 1

    @pytest.mark.asyncio
    async def test_get_chore_details(self, client, httpx_mock: HTTPXMock):
        httpx_mock.add_response(
            url=f"{BASE}/api/v1/chores/1/details",
            json={"res": {**SAMPLE_CHORE, "totalCompletedCount": 5}},
        )
        details = await client.get_chore_details(1)
        assert details.totalCompletedCount == 5

    @pytest.mark.asyncio
    async def test_get_chore_details_lighter_shape(self, client, httpx_mock: HTTPXMock):
        # the detail endpoint omits frequency/circleId/createdAt/updatedAt
        light = {k: v for k, v in SAMPLE_CHORE.items() if k not in ("frequency", "circleId", "createdAt", "updatedAt")}
        httpx_mock.add_response(
            url=f"{BASE}/api/v1/chores/1/details",
            json={"res": {**light, "totalCompletedCount": 5}},
        )
        details = await client.get_chore_details(1)
        assert details.totalCompletedCount == 5


class TestThings:
    @pytest.mark.asyncio
    async def test_list_things(self, client, httpx_mock: HTTPXMock):
        httpx_mock.add_response(
            url=f"{BASE}/eapi/v1/things/",
            json=[{"id": 1, "name": "Water Tank", "state": "50", "type": "number"}],
        )
        things = await client.list_things()
        assert things[0].name == "Water Tank"
        assert things[0].state == "50"

    @pytest.mark.asyncio
    async def test_get_thing(self, client, httpx_mock: HTTPXMock):
        httpx_mock.add_response(
            url=f"{BASE}/eapi/v1/things/1",
            json={"thing": {"id": 1, "name": "Water Tank", "state": "50", "type": "number"}},
        )
        thing = await client.get_thing(1)
        assert thing.state == "50"

    @pytest.mark.asyncio
    async def test_change_thing_state(self, client, httpx_mock: HTTPXMock):
        httpx_mock.add_response(url=f"{BASE}/eapi/v1/things/1/state/change?set=60", json={})
        await client.change_thing_state(1, set_value="60")
        request = httpx_mock.get_requests()[0]
        assert request.url.params["set"] == "60"

    @pytest.mark.asyncio
    async def test_create_thing(self, client, httpx_mock: HTTPXMock):
        httpx_mock.add_response(
            url=f"{BASE}/api/v1/things",
            json={"res": {"id": 1, "name": "Water Tank", "type": "number", "state": "50"}},
            method="POST",
        )
        thing = await client.create_thing(name="Water Tank", type="number", state="50")
        assert thing.id == 1
        assert thing.name == "Water Tank"
        request = httpx_mock.get_requests()[0]
        assert request.method == "POST"
        assert json.loads(request.content) == {"name": "Water Tank", "type": "number", "state": "50"}

    @pytest.mark.asyncio
    async def test_update_thing(self, client, httpx_mock: HTTPXMock):
        httpx_mock.add_response(
            url=f"{BASE}/api/v1/things",
            json={"res": {"id": 1, "name": "Water Tank", "type": "number", "state": "60"}},
            method="PUT",
        )
        thing = await client.update_thing(1, name="Water Tank", type="number", state="60")
        assert thing.state == "60"
        request = httpx_mock.get_requests()[0]
        assert json.loads(request.content) == {"id": 1, "name": "Water Tank", "type": "number", "state": "60"}

    @pytest.mark.asyncio
    async def test_delete_thing(self, client, httpx_mock: HTTPXMock):
        httpx_mock.add_response(url=f"{BASE}/api/v1/things/1", json={}, method="DELETE")
        await client.delete_thing(1)
        assert httpx_mock.get_requests()[0].method == "DELETE"

    @pytest.mark.asyncio
    async def test_get_thing_history(self, client, httpx_mock: HTTPXMock):
        httpx_mock.add_response(
            url=f"{BASE}/api/v1/things/1/history",
            json=[{"id": 9, "thingId": 1, "state": "50"}],
        )
        history = await client.get_thing_history(1)
        assert history[0].state == "50"


class TestProjects:
    @pytest.mark.asyncio
    async def test_list_projects(self, client, httpx_mock: HTTPXMock):
        httpx_mock.add_response(
            url=f"{BASE}/api/v1/projects",
            json={"res": [{"id": 1, "name": "Home", "circleId": 2}]},
        )
        projects = await client.list_projects()
        assert projects[0].name == "Home"

    @pytest.mark.asyncio
    async def test_create_project(self, client, httpx_mock: HTTPXMock):
        httpx_mock.add_response(
            url=f"{BASE}/api/v1/projects",
            json={"res": {"id": 1, "name": "Home", "circleId": 2}},
            method="POST",
        )
        project = await client.create_project(ProjectUpdate(name="Home"))
        assert project.id == 1
        request = httpx_mock.get_requests()[0]
        assert json.loads(request.content) == {"name": "Home"}

    @pytest.mark.asyncio
    async def test_delete_project(self, client, httpx_mock: HTTPXMock):
        httpx_mock.add_response(url=f"{BASE}/api/v1/projects/1", json={}, method="DELETE")
        await client.delete_project(1)
        assert httpx_mock.get_requests()[0].method == "DELETE"


class TestChoreActions:
    @pytest.mark.asyncio
    async def test_archive_chore(self, client, httpx_mock: HTTPXMock):
        httpx_mock.add_response(url=f"{BASE}/api/v1/chores/1/archive", json={}, method="PUT")
        await client.archive_chore(1)
        assert httpx_mock.get_requests()[0].method == "PUT"

    @pytest.mark.asyncio
    async def test_undo_chore(self, client, httpx_mock: HTTPXMock):
        httpx_mock.add_response(url=f"{BASE}/api/v1/chores/1/undo", json={}, method="POST")
        await client.undo_chore(1)
        assert httpx_mock.get_requests()[0].method == "POST"


class TestRateLimitAndErrors:
    @pytest.mark.asyncio
    async def test_429_retry_then_success(self, client, httpx_mock: HTTPXMock):
        httpx_mock.add_response(url=f"{BASE}/eapi/v1/chore", status_code=429, headers={"Retry-After": "0"}, json={})
        httpx_mock.add_response(url=f"{BASE}/eapi/v1/chore", json=[])
        assert await client.list_chores() == []

    @pytest.mark.asyncio
    async def test_401_raises(self, client, httpx_mock: HTTPXMock):
        httpx_mock.add_response(url=f"{BASE}/eapi/v1/chore", status_code=401, json={"error": "API token required"})
        with pytest.raises(httpx.HTTPStatusError) as exc_info:
            await client.list_chores()
        assert exc_info.value.response.status_code == 401

    @pytest.mark.asyncio
    async def test_4xx_no_retry(self, client, httpx_mock: HTTPXMock):
        httpx_mock.add_response(url=f"{BASE}/eapi/v1/chore", status_code=404, json={"error": "Not found"})
        with pytest.raises(httpx.HTTPStatusError):
            await client.list_chores()
