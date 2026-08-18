"""Tests for the MCP server tools (FastMCP surface, token auth)."""

import json

import pytest
from fastmcp.exceptions import NotFoundError
from pytest_httpx2 import HTTPXMock

import donetick_mcp.server as server

BASE = "https://donetick.example.com"

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


async def call_tool(name, arguments=None):
    result = await server.mcp.call_tool(name, arguments)
    return result.content


async def list_tools():
    return await server.mcp.list_tools()


class TestToolList:
    @pytest.mark.asyncio
    async def test_list_tools(self):
        tools = await list_tools()
        names = {t.name for t in tools}
        assert len(tools) == 18
        assert {
            "list_chores",
            "get_chore",
            "create_chore",
            "complete_chore",
            "update_chore",
            "delete_chore",
            "update_chore_priority",
            "update_chore_assignee",
            "skip_chore",
            "update_subtask_completion",
            "get_circle_members",
            "get_chore_history",
            "get_all_chores_history",
            "get_chore_details",
            "list_things",
            "get_thing",
            "get_thing_state",
            "change_thing_state",
        } == names


class TestChoreTools:
    @pytest.mark.asyncio
    async def test_list_chores(self, httpx_mock: HTTPXMock):
        httpx_mock.add_response(url=f"{BASE}/eapi/v1/chore", json=[SAMPLE_CHORE])
        result = await call_tool("list_chores", {})
        data = json.loads(result[0].text)
        assert data["count"] == 1
        assert data["chores"][0]["name"] == "Test Chore"

    @pytest.mark.asyncio
    async def test_list_chores_empty(self, httpx_mock: HTTPXMock):
        httpx_mock.add_response(url=f"{BASE}/eapi/v1/chore", json=[])
        result = await call_tool("list_chores", {})
        assert "No chores found" in result[0].text

    @pytest.mark.asyncio
    async def test_get_chore(self, httpx_mock: HTTPXMock):
        httpx_mock.add_response(url=f"{BASE}/api/v1/chores/1", json={"res": SAMPLE_CHORE})
        result = await call_tool("get_chore", {"chore_id": 1})
        data = json.loads(result[0].text)
        assert data["id"] == 1

    @pytest.mark.asyncio
    async def test_get_chore_not_found(self, httpx_mock: HTTPXMock):
        httpx_mock.add_response(url=f"{BASE}/api/v1/chores/999", status_code=404)
        result = await call_tool("get_chore", {"chore_id": 999})
        assert "not found" in result[0].text.lower()

    @pytest.mark.asyncio
    async def test_create_chore(self, httpx_mock: HTTPXMock):
        httpx_mock.add_response(url=f"{BASE}/eapi/v1/chore", json=SAMPLE_CHORE, method="POST")
        result = await call_tool("create_chore", {"name": "Test Chore", "description": "desc"})
        assert "Successfully created" in result[0].text
        assert "Test Chore" in result[0].text

    @pytest.mark.asyncio
    async def test_create_chore_invalid_username(self, httpx_mock: HTTPXMock):
        httpx_mock.add_response(
            url=f"{BASE}/api/v1/circles/members/",
            json=[
                {
                    "id": 1,
                    "userId": 1,
                    "circleId": 1,
                    "role": "member",
                    "isActive": True,
                    "username": "alice",
                    "displayName": "Alice",
                    "points": 0,
                    "pointsRedeemed": 0,
                }
            ],
        )
        result = await call_tool("create_chore", {"name": "X", "usernames": ["charlie"]})
        assert "Could not find user" in result[0].text

    @pytest.mark.asyncio
    async def test_complete_chore(self, httpx_mock: HTTPXMock):
        httpx_mock.add_response(url=f"{BASE}/api/v1/chores/1/do", json=SAMPLE_CHORE, method="POST")
        result = await call_tool("complete_chore", {"chore_id": 1})
        assert "Successfully completed" in result[0].text

    @pytest.mark.asyncio
    async def test_update_chore(self, httpx_mock: HTTPXMock):
        httpx_mock.add_response(url=f"{BASE}/api/v1/chores/1", json={"res": SAMPLE_CHORE})
        httpx_mock.add_response(
            url=f"{BASE}/api/v1/chores/", json={"message": "Chore added successfully"}, method="PUT"
        )
        httpx_mock.add_response(url=f"{BASE}/api/v1/chores/1", json={"res": {**SAMPLE_CHORE, "name": "Renamed"}})
        result = await call_tool("update_chore", {"chore_id": 1, "name": "Renamed"})
        assert "Successfully updated" in result[0].text

    @pytest.mark.asyncio
    async def test_delete_chore(self, httpx_mock: HTTPXMock):
        httpx_mock.add_response(
            url=f"{BASE}/eapi/v1/chore/1", json={"message": "Chore deleted successfully"}, method="DELETE"
        )
        result = await call_tool("delete_chore", {"chore_id": 1})
        assert "Successfully deleted" in result[0].text

    @pytest.mark.asyncio
    async def test_update_chore_priority(self, httpx_mock: HTTPXMock):
        httpx_mock.add_response(
            url=f"{BASE}/api/v1/chores/1/priority", json={**SAMPLE_CHORE, "priority": 4}, method="PUT"
        )
        result = await call_tool("update_chore_priority", {"chore_id": 1, "priority": 4})
        assert "priority to 4" in result[0].text

    @pytest.mark.asyncio
    async def test_update_chore_priority_invalid(self, httpx_mock: HTTPXMock):
        result = await call_tool("update_chore_priority", {"chore_id": 1, "priority": 5})
        assert "must be 0-4" in result[0].text

    @pytest.mark.asyncio
    async def test_skip_chore(self, httpx_mock: HTTPXMock):
        httpx_mock.add_response(
            url=f"{BASE}/api/v1/chores/1/skip", json={**SAMPLE_CHORE, "nextDueDate": "2025-11-17"}, method="POST"
        )
        result = await call_tool("skip_chore", {"chore_id": 1})
        assert "Successfully skipped" in result[0].text
        assert "next due date" in result[0].text.lower()

    @pytest.mark.asyncio
    async def test_get_circle_members(self, httpx_mock: HTTPXMock):
        httpx_mock.add_response(
            url=f"{BASE}/api/v1/circles/members/",
            json=[
                {
                    "id": 1,
                    "userId": 1,
                    "circleId": 1,
                    "role": "admin",
                    "isActive": True,
                    "username": "alice",
                    "displayName": "Alice Admin",
                    "points": 100,
                    "pointsRedeemed": 25,
                }
            ],
        )
        result = await call_tool("get_circle_members", {})
        assert "Found 1 member(s)" in result[0].text
        assert "alice" in result[0].text

    @pytest.mark.asyncio
    async def test_get_chore_history(self, httpx_mock: HTTPXMock):
        httpx_mock.add_response(
            url=f"{BASE}/api/v1/chores/1/history",
            json=[
                {
                    "id": 1,
                    "choreId": 1,
                    "performedAt": "2025-11-05T10:00:00Z",
                    "completedBy": 1,
                    "assignedTo": 1,
                    "note": "Done",
                    "dueDate": "2025-11-05",
                }
            ],
        )
        result = await call_tool("get_chore_history", {"chore_id": 1})
        assert "Total completions: 1" in result[0].text

    @pytest.mark.asyncio
    async def test_get_chore_details(self, httpx_mock: HTTPXMock):
        httpx_mock.add_response(
            url=f"{BASE}/api/v1/chores/1/details",
            json={"res": {**SAMPLE_CHORE, "totalCompletedCount": 5}},
        )
        result = await call_tool("get_chore_details", {"chore_id": 1})
        assert "Total Completions: 5" in result[0].text


class TestThingTools:
    @pytest.mark.asyncio
    async def test_list_things(self, httpx_mock: HTTPXMock):
        httpx_mock.add_response(
            url=f"{BASE}/eapi/v1/things/",
            json=[{"id": 1, "name": "Water Tank", "state": "50", "type": "number"}],
        )
        result = await call_tool("list_things", {})
        assert "Water Tank" in result[0].text

    @pytest.mark.asyncio
    async def test_get_thing_state(self, httpx_mock: HTTPXMock):
        httpx_mock.add_response(
            url=f"{BASE}/eapi/v1/things/1",
            json={"thing": {"id": 1, "name": "Water Tank", "state": "50", "type": "number"}},
        )
        result = await call_tool("get_thing_state", {"thing_id": 1})
        assert "state: 50" in result[0].text

    @pytest.mark.asyncio
    async def test_change_thing_state(self, httpx_mock: HTTPXMock):
        httpx_mock.add_response(url=f"{BASE}/eapi/v1/things/1/state/change?set=60", json={})
        result = await call_tool("change_thing_state", {"thing_id": 1, "set_value": "60"})
        assert "state updated" in result[0].text


class TestErrors:
    @pytest.mark.asyncio
    async def test_401_message(self, httpx_mock: HTTPXMock):
        httpx_mock.add_response(url=f"{BASE}/eapi/v1/chore", status_code=401, json={"error": "API token required"})
        result = await call_tool("list_chores", {})
        assert "Authentication failed" in result[0].text
        assert "DONETICK_API_TOKEN" in result[0].text
        assert "DONETICK_USERNAME" not in result[0].text

    @pytest.mark.asyncio
    async def test_unknown_tool(self):
        with pytest.raises(NotFoundError):
            await call_tool("unknown_tool", {})
