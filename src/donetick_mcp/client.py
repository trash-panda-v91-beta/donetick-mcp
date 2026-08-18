"""Donetick API client with token auth, rate limiting, and retry logic.

Uses the External API (/eapi/v1) where it is the token-native surface
(list, create, delete chores; things) and the Full API (/api/v1) for the
operations the External API lacks (single get, skip, priority, assignee,
subtasks, history, details, circle members). Both are authenticated with a
long-lived access token sent in the `secretkey` header.
"""

import asyncio
import json as json_lib
import logging
import random
import time
from datetime import UTC, datetime
from typing import Any

import httpx2 as httpx

from .config import config
from .models import (
    Chore,
    ChoreDetail,
    ChoreHistory,
    ChoreUpdate,
    CircleMember,
    Project,
    ProjectUpdate,
    Thing,
    ThingHistory,
)

logger = logging.getLogger(__name__)

# Server-generated metadata fields that should be removed before update requests
FIELDS_TO_REMOVE = [
    "createdAt",
    "updatedAt",
    "createdBy",
    "updatedBy",
    "circleId",
    "status",
]


class TokenBucket:
    """Token bucket rate limiter."""

    def __init__(self, rate: float, capacity: int):
        self.rate = rate
        self.capacity = capacity
        self.tokens = float(capacity)
        self.last_update = time.time()
        self.lock = asyncio.Lock()

    async def acquire(self, tokens: int = 1):
        async with self.lock:
            while True:
                now = time.time()
                elapsed = now - self.last_update
                self.tokens = min(self.capacity, self.tokens + elapsed * self.rate)
                self.last_update = now
                if self.tokens >= tokens:
                    self.tokens -= tokens
                    return
                wait_time = (tokens - self.tokens) / self.rate
                await asyncio.sleep(wait_time)


class DonetickClient:
    """Async client for the Donetick External and Full APIs (token auth)."""

    def __init__(
        self,
        base_url: str | None = None,
        api_token: str | None = None,
        rate_limit_per_second: float | None = None,
        rate_limit_burst: int | None = None,
    ):
        self.base_url = (base_url or config.donetick_base_url or "").rstrip("/")
        self.api_token = api_token or config.donetick_api_token or ""
        self.rate_limiter = TokenBucket(
            rate=rate_limit_per_second or config.rate_limit_per_second,
            capacity=rate_limit_burst or config.rate_limit_burst,
        )

        # Configure httpx client with connection pooling and token auth
        self.client = httpx.AsyncClient(
            headers={
                "Content-Type": "application/json",
                "Accept": "application/json",
                "secretkey": self.api_token,
            },
            limits=httpx.Limits(
                max_connections=100,
                max_keepalive_connections=50,
                keepalive_expiry=30.0,
            ),
            timeout=httpx.Timeout(
                connect=5.0,
                read=30.0,
                write=5.0,
                pool=2.0,
            ),
            verify=True,  # Enforce certificate verification
        )

    async def __aenter__(self):
        """Async context manager entry."""
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit with cleanup."""
        await self.close()

    async def close(self):
        """Close the HTTP client and cleanup resources."""
        if self.client:
            await self.client.aclose()

    async def _request(self, method: str, path: str, max_retries: int = 3, **kwargs: Any) -> Any:
        """Make a rate-limited HTTP request with retry logic.

        Raises:
            httpx.HTTPError: On HTTP errors after all retries exhausted
        """
        url = f"{self.base_url}{path}"
        base_delay = 1.0

        for attempt in range(max_retries):
            try:
                await self.rate_limiter.acquire()
                logger.debug(f"Request {method} {url} (attempt {attempt + 1}/{max_retries})")
                response = await self.client.request(method, url, **kwargs)

                if response.status_code == 429:
                    retry_after = response.headers.get("Retry-After", "60")
                    wait_time = float(retry_after)
                    logger.warning(f"Rate limited, waiting {wait_time}s")
                    await asyncio.sleep(wait_time)
                    continue

                response.raise_for_status()

                try:
                    return response.json()
                except json_lib.JSONDecodeError as e:
                    logger.error(f"Invalid JSON response from {url}: {response.text[:200]}")
                    raise ValueError(f"Invalid JSON response from API: {e}") from e

            except (httpx.TimeoutException, httpx.HTTPStatusError) as e:
                # Don't retry client errors (4xx) except 429
                if (
                    isinstance(e, httpx.HTTPStatusError)
                    and 400 <= e.response.status_code < 500
                    and e.response.status_code != 429
                ):
                    logger.error(f"Client error: {e.response.status_code} - {e.response.text}")
                    raise
                if attempt == max_retries - 1:
                    logger.error(f"Request failed after {max_retries} attempts: {e}")
                    raise
                delay = min(base_delay * (2**attempt), 60.0)
                jitter = delay * random.uniform(-0.25, 0.25)
                logger.warning(f"Retrying in {delay + jitter:.2f}s")
                await asyncio.sleep(delay + jitter)

        raise Exception(f"Failed after {max_retries} retries")

    # ==================== External API (eapi/v1) ====================

    async def list_chores(
        self,
        filter_active: bool | None = None,
        assigned_to_user_id: int | None = None,
        include_subtasks: bool = False,
    ) -> list[Chore]:
        """List all chores (External API). Filters are applied client-side."""
        logger.info("Fetching chores list")
        params = {"includeSubtasks": "true"} if include_subtasks else None
        data = await self._request("GET", "/eapi/v1/chore", params=params)

        chores_list = data if isinstance(data, list) else []
        chores = [Chore(**chore_data) for chore_data in chores_list]

        if filter_active is not None:
            chores = [c for c in chores if c.isActive == filter_active]
        if assigned_to_user_id is not None:
            chores = [c for c in chores if c.assignedTo == assigned_to_user_id]

        logger.info(f"Retrieved {len(chores)} chores")
        return chores

    async def create_chore(
        self,
        name: str,
        description: str | None = None,
        due_date: str | None = None,
        created_by: int | None = None,
    ) -> Chore:
        """Create a chore (External API). Supports name/description/dueDate/createdBy only."""
        logger.info(f"Creating chore: {name}")
        payload = {"name": name}
        if description:
            payload["description"] = description
        if due_date:
            payload["dueDate"] = due_date
        if created_by is not None:
            payload["createdBy"] = created_by

        data = await self._request("POST", "/eapi/v1/chore", json=payload)
        chore = Chore(**data)
        logger.info(f"Created chore {chore.id}: {chore.name}")
        return chore

    async def delete_chore(self, chore_id: int) -> bool:
        """Delete a chore (External API)."""
        logger.info(f"Deleting chore {chore_id}")
        await self._request("DELETE", f"/eapi/v1/chore/{chore_id}")
        logger.info(f"Deleted chore {chore_id}")
        return True

    async def list_things(self) -> list[Thing]:
        """List all things (External API)."""
        logger.info("Fetching things")
        data = await self._request("GET", "/eapi/v1/things/")
        things = data if isinstance(data, list) else []
        return [Thing(**t) for t in things]

    async def get_thing(self, thing_id: int) -> Thing | None:
        """Get a thing by ID (External API)."""
        logger.info(f"Fetching thing {thing_id}")
        data = await self._request("GET", f"/eapi/v1/things/{thing_id}")
        thing = data.get("thing", data) if isinstance(data, dict) else data
        return Thing(**thing)

    async def create_thing(self, name: str, type: str, state: str | None = None) -> Thing:
        """Create a new thing (Full API)."""
        logger.info(f"Creating thing {name}")
        body: dict[str, str] = {"name": name, "type": type}
        if state is not None:
            body["state"] = state
        data = await self._request("POST", "/api/v1/things", json=body)
        thing_data = data.get("res", data) if isinstance(data, dict) else data
        return Thing(**thing_data)

    async def change_thing_state(self, thing_id: int, set_value: str | None = None, op: str | None = None) -> None:
        """Change a thing's state by setting a value or applying a numeric op (External API)."""
        params: dict[str, str] = {}
        if set_value is not None:
            params["set"] = set_value
        if op is not None:
            params["op"] = op
        logger.info(f"Changing thing {thing_id} state: {params}")
        await self._request("GET", f"/eapi/v1/things/{thing_id}/state/change", params=params)

    async def update_thing(self, thing_id: int, name: str, type: str, state: str | None = None) -> Thing:
        """Update a thing's name, type, and optional state (Full API)."""
        logger.info(f"Updating thing {thing_id}")
        body: dict[str, object] = {"id": thing_id, "name": name, "type": type}
        if state is not None:
            body["state"] = state
        data = await self._request("PUT", "/api/v1/things", json=body)
        thing_data = data.get("res", data) if isinstance(data, dict) else data
        return Thing(**thing_data)

    async def delete_thing(self, thing_id: int) -> None:
        """Delete a thing (Full API)."""
        logger.info(f"Deleting thing {thing_id}")
        await self._request("DELETE", f"/api/v1/things/{thing_id}")

    async def get_thing_history(self, thing_id: int) -> list[ThingHistory]:
        """Get a thing's state-change history (Full API)."""
        logger.info(f"Fetching thing {thing_id} history")
        data = await self._request("GET", f"/api/v1/things/{thing_id}/history")
        rows = data.get("res", data) if isinstance(data, dict) else data
        if isinstance(rows, dict):
            rows = rows.get("history", rows.get("res", []))
        if not isinstance(rows, list):
            rows = []
        return [ThingHistory(**r) for r in rows]

    # ==================== Full API (api/v1) - external gaps ====================

    async def get_chore(self, chore_id: int) -> Chore | None:
        """Get a specific chore by ID (includes sub-tasks)."""
        logger.info(f"Fetching chore {chore_id} (includes sub-tasks)")
        try:
            data = await self._request("GET", f"/api/v1/chores/{chore_id}")
            chore_data = data.get("res", data) if isinstance(data, dict) else data
            return Chore(**chore_data)
        except httpx.HTTPStatusError as e:
            if e.response.status_code == 404:
                logger.warning(f"Chore {chore_id} not found")
                return None
            raise

    async def update_chore(self, chore_id: int, update: ChoreUpdate) -> Chore:
        """Update an existing chore (fetch-modify-send on the Full API)."""
        logger.info(f"Updating chore {chore_id}")

        current_chore = await self.get_chore(chore_id)
        if current_chore is None:
            raise ValueError(f"Chore {chore_id} not found")

        chore_dict = current_chore.model_dump(exclude_none=True)
        chore_dict.update(update.model_dump(exclude_none=True))
        chore_dict["id"] = chore_id

        for field in FIELDS_TO_REMOVE:
            chore_dict.pop(field, None)

        if "labelsV2" in chore_dict and chore_dict["labelsV2"]:
            for label in chore_dict["labelsV2"]:
                if "created_by" in label and label["created_by"] is None:
                    label.pop("created_by")

        # If assignedTo is set it must be present in assignees (as {"userId": n})
        assigned_to = chore_dict.get("assignedTo")
        assignees = chore_dict.get("assignees", [])
        if assigned_to is not None:
            if not isinstance(assignees, list):
                assignees = []
                chore_dict["assignees"] = assignees
            ids = [a if isinstance(a, int) else a.get("userId") for a in assignees]
            if assigned_to not in ids:
                assignees.append({"userId": assigned_to})
                chore_dict["assignees"] = assignees

        logger.debug(f"Sending update payload: {json_lib.dumps(chore_dict, indent=2)}")
        data = await self._request("PUT", "/api/v1/chores/", json=chore_dict)

        if "message" in data:
            updated_chore = await self.get_chore(chore_id)
            if updated_chore is None:
                raise ValueError(f"Chore {chore_id} was updated but could not be retrieved")
        else:
            updated_chore = Chore(**data)

        logger.info(f"Updated chore {chore_id}: {updated_chore.name}")
        return updated_chore

    async def complete_chore(self, chore_id: int, completed_by: int | None = None) -> Chore:
        """Mark a chore as complete."""
        logger.info(f"Completing chore {chore_id}")
        body = {}
        if completed_by is not None:
            body["completedBy"] = completed_by
        data = await self._request("POST", f"/api/v1/chores/{chore_id}/do", json=body)
        if isinstance(data, dict) and "res" in data:
            data = data["res"]
        return Chore(**data)

    async def update_chore_priority(self, chore_id: int, priority: int) -> Chore:
        """Update a chore's priority level (0-4)."""
        if not 0 <= priority <= 4:
            raise ValueError(f"Priority must be 0-4, got {priority}")
        data = await self._request("PUT", f"/api/v1/chores/{chore_id}/priority", json={"priority": priority})
        if "message" in data:
            updated_chore = await self.get_chore(chore_id)
            if updated_chore is None:
                raise ValueError(f"Chore {chore_id} was updated but could not be retrieved")
            return updated_chore
        if isinstance(data, dict) and "res" in data:
            data = data["res"]
        return Chore(**data)

    async def update_chore_assignee(self, chore_id: int, user_id: int) -> Chore:
        """Reassign a chore to a different user."""
        logger.info(f"Reassigning chore {chore_id} to user {user_id}")
        current_chore = await self.get_chore(chore_id)
        if current_chore is None:
            raise ValueError(f"Chore {chore_id} not found")

        chore_dict = current_chore.model_dump(exclude_none=True)
        chore_dict["id"] = chore_id
        chore_dict["assignedTo"] = user_id
        chore_dict["assignees"] = [{"userId": user_id}]
        if not chore_dict.get("assignStrategy"):
            chore_dict["assignStrategy"] = "least_completed"
        for field in FIELDS_TO_REMOVE:
            chore_dict.pop(field, None)
        if "labelsV2" in chore_dict and chore_dict["labelsV2"]:
            for label in chore_dict["labelsV2"]:
                if "created_by" in label and label["created_by"] is None:
                    label.pop("created_by")

        data = await self._request("PUT", "/api/v1/chores/", json=chore_dict)
        if "message" in data:
            updated_chore = await self.get_chore(chore_id)
            if updated_chore is None:
                raise ValueError(f"Chore {chore_id} was updated but could not be retrieved")
        else:
            updated_chore = Chore(**data)
        return updated_chore

    async def skip_chore(self, chore_id: int) -> Chore:
        """Skip a chore without marking it complete."""
        logger.info(f"Skipping chore {chore_id}")
        data = await self._request("POST", f"/api/v1/chores/{chore_id}/skip")
        if isinstance(data, dict) and "res" in data:
            data = data["res"]
        return Chore(**data)

    async def update_subtask_completion(self, chore_id: int, subtask_id: int, completed: bool) -> Chore:
        """Update the completion status of a subtask."""
        chore = await self.get_chore(chore_id)
        if chore is None:
            raise ValueError(f"Chore {chore_id} not found")

        updated = False
        for subtask in chore.subTasks:
            if subtask.get("id") == subtask_id:
                if completed:
                    subtask["completedAt"] = datetime.now(UTC).isoformat()
                else:
                    subtask["completedAt"] = None
                    subtask["completedBy"] = 0
                updated = True
                break
        if not updated:
            raise ValueError(f"Subtask {subtask_id} not found in chore {chore_id}")

        return await self.update_chore(chore_id, ChoreUpdate(subTasks=chore.subTasks))

    async def get_chore_history(self, chore_id: int) -> list[ChoreHistory]:
        """Get completion history for a specific chore."""
        logger.info(f"Fetching history for chore {chore_id}")
        data = await self._request("GET", f"/api/v1/chores/{chore_id}/history")
        history_list = data.get("res", data) if isinstance(data, dict) else data
        if not isinstance(history_list, list):
            history_list = []
        return [ChoreHistory(**entry_data) for entry_data in history_list]

    async def get_all_chores_history(self, limit: int = 50, offset: int = 0) -> list[ChoreHistory]:
        """Get completion history for all chores with pagination."""
        logger.info(f"Fetching all chores history (limit={limit}, offset={offset})")
        data = await self._request("GET", "/api/v1/chores/history", params={"limit": limit, "offset": offset})
        history_list = data.get("res", data) if isinstance(data, dict) else data
        if not isinstance(history_list, list):
            history_list = []
        return [ChoreHistory(**entry_data) for entry_data in history_list]

    async def get_chore_details(self, chore_id: int) -> ChoreDetail:
        """Get detailed chore information including statistics."""
        logger.info(f"Fetching detailed information for chore {chore_id}")
        data = await self._request("GET", f"/api/v1/chores/{chore_id}/details")
        detail_data = data.get("res", data) if isinstance(data, dict) and "res" in data else data
        return ChoreDetail(**detail_data)

    async def get_circle_members(self) -> list[CircleMember]:
        """Get all members in the user's circle."""
        logger.info("Fetching circle members")
        data = await self._request("GET", "/api/v1/circles/members")
        members_data = data.get("res", data) if isinstance(data, dict) else data
        return [CircleMember(**member_data) for member_data in members_data]

    # ==================== Chore lifecycle actions (api/v1/chores) ====================

    async def archive_chore(self, chore_id: int) -> None:
        """Archive a chore."""
        await self._request("PUT", f"/api/v1/chores/{chore_id}/archive", json={})

    async def unarchive_chore(self, chore_id: int) -> None:
        """Unarchive a chore."""
        await self._request("PUT", f"/api/v1/chores/{chore_id}/unarchive", json={})

    async def undo_chore(self, chore_id: int) -> None:
        """Undo the last completion of a chore."""
        await self._request("POST", f"/api/v1/chores/{chore_id}/undo", json={})

    async def approve_chore(self, chore_id: int) -> None:
        """Approve a pending chore completion."""
        await self._request("POST", f"/api/v1/chores/{chore_id}/approve", json={})

    async def reject_chore(self, chore_id: int) -> None:
        """Reject a pending chore completion."""
        await self._request("POST", f"/api/v1/chores/{chore_id}/reject", json={})

    async def start_chore(self, chore_id: int) -> None:
        """Mark a chore as in progress (timer)."""
        await self._request("PUT", f"/api/v1/chores/{chore_id}/start", json={})

    async def pause_chore(self, chore_id: int) -> None:
        """Pause a running chore timer."""
        await self._request("PUT", f"/api/v1/chores/{chore_id}/pause", json={})

    # ==================== Projects (api/v1/projects) ====================

    async def list_projects(self) -> list[Project]:
        """List all projects."""
        logger.info("Fetching projects")
        data = await self._request("GET", "/api/v1/projects")
        projects = data.get("res", data) if isinstance(data, dict) else data
        if not isinstance(projects, list):
            projects = []
        return [Project(**p) for p in projects]

    async def create_project(self, project: ProjectUpdate) -> Project:
        """Create a project."""
        logger.info(f"Creating project {project.name}")
        data = await self._request("POST", "/api/v1/projects", json=project.model_dump(exclude_none=True))
        project_data = data.get("res", data) if isinstance(data, dict) else data
        return Project(**project_data)

    async def update_project(self, project_id: int, project: ProjectUpdate) -> Project:
        """Update a project."""
        logger.info(f"Updating project {project_id}")
        data = await self._request("PUT", f"/api/v1/projects/{project_id}", json=project.model_dump(exclude_none=True))
        project_data = data.get("res", data) if isinstance(data, dict) else data
        return Project(**project_data)

    async def delete_project(self, project_id: int) -> None:
        """Delete a project."""
        logger.info(f"Deleting project {project_id}")
        await self._request("DELETE", f"/api/v1/projects/{project_id}")

    async def lookup_user_ids(self, usernames: list[str]) -> dict[str, int]:
        """Lookup user IDs from usernames (case-insensitive)."""
        members = await self.get_circle_members()
        username_map: dict[str, int] = {}
        for member in members:
            member_username = member.username.lower()
            member_display = (member.displayName or "").lower()
            for requested in usernames:
                low = requested.lower()
                if low == member_username or low == member_display:
                    username_map[requested] = member.userId
                    break
        return username_map
