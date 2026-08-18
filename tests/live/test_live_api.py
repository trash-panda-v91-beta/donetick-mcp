"""Live API integration tests (run against a real Donetick instance).

These tests require a live Donetick instance and a valid API token. They are
deselected by default; run them explicitly with:

    pytest tests/live/ -m live_api -v
"""

import pytest

from donetick_mcp.models import ChoreUpdate

# Deselect in the default run; skip in CI where no live instance exists
pytestmark = [pytest.mark.live_api, pytest.mark.skip_in_ci]


class TestChoreLifecycle:
    @pytest.mark.asyncio
    async def test_create_and_list(self, live_client, test_chore_ids):
        created = await live_client.create_chore(
            name="Live Test Chore", description="created by live test", due_date="2026-01-01"
        )
        test_chore_ids.append(created.id)

        assert created.id > 0
        chores = await live_client.list_chores()
        assert any(c.id == created.id for c in chores)

    @pytest.mark.asyncio
    async def test_update(self, live_client, test_chore_ids):
        created = await live_client.create_chore(name="Update Me")
        test_chore_ids.append(created.id)

        updated = await live_client.update_chore(created.id, ChoreUpdate(name="Updated Name"))
        assert updated.name == "Updated Name"

    @pytest.mark.asyncio
    async def test_complete(self, live_client, test_chore_ids):
        created = await live_client.create_chore(name="Complete Me")
        test_chore_ids.append(created.id)

        completed = await live_client.complete_chore(created.id)
        assert completed.id == created.id

    @pytest.mark.asyncio
    async def test_get_missing_returns_none(self, live_client):
        assert await live_client.get_chore(999999999) is None


class TestThings:
    @pytest.mark.asyncio
    async def test_list_things(self, live_client):
        things = await live_client.list_things()
        # Things may not exist; just ensure a list comes back without error.
        assert isinstance(things, list)
