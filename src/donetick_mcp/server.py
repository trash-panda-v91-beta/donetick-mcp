"""Donetick MCP server built on FastMCP."""

import json
import logging
import urllib.parse
from functools import wraps
from typing import Any

import httpx2 as httpx
from fastmcp import FastMCP
from fastmcp.server.lifespan import lifespan

from . import __version__
from .client import DonetickClient
from .config import config
from .models import ChoreUpdate

config.configure_logging()
logger = logging.getLogger(__name__)


@lifespan
async def donetick_lifespan(server):
    """Close the shared Donetick client on shutdown."""
    global client
    yield None
    if client is not None:
        await client.close()
        client = None


mcp = FastMCP("donetick-chores", lifespan=donetick_lifespan)

# Shared client instance (initialized on first use)
client: DonetickClient | None = None


async def get_client() -> DonetickClient:
    """Get the shared Donetick client, creating it on first use."""
    global client
    if client is None:
        client = DonetickClient()
    return client


def _error_text(tool_name: str, exc: Exception) -> str:
    """Map an exception to a user-friendly error message."""
    if isinstance(exc, httpx.HTTPStatusError):
        status_code = exc.response.status_code
        api_error = None
        try:
            error_data = exc.response.json()
            api_error = error_data.get("error") or error_data.get("message")
        except Exception:
            try:
                api_error = exc.response.text[:200] if exc.response.text else None
            except Exception:
                pass

        if status_code == 401:
            msg = (
                "Authentication failed. Check your Donetick API token.\n\n"
                "\U0001f4a1 Hint: Verify the token in your environment or .env file:\n"
                "   - DONETICK_BASE_URL\n"
                "   - DONETICK_API_TOKEN"
            )
        elif status_code == 403:
            msg = (
                "Permission denied. You may not have authorization for this operation.\n\n"
                "\U0001f4a1 Hint: Verify that:\n"
                "   - You have the correct API token\n"
                "   - The resource exists and belongs to your circle\n"
                "   - You have the necessary permissions (e.g., only creators can delete chores)"
            )
        elif status_code == 404:
            if "chore" in tool_name:
                msg = (
                    "Chore not found.\n\n"
                    "\U0001f4a1 Hint: Use list_chores to see available chores and their IDs.\n"
                    "   Chores may have been deleted or the ID may be incorrect."
                )
            else:
                msg = "Resource not found."
        elif status_code == 422:
            base = (
                f"Validation error: {api_error}"
                if api_error
                else "Validation error. The API rejected the request parameters."
            )
            msg = (
                f"{base}\n\n"
                "\U0001f4a1 Hint: Common issues:\n"
                "   - Invalid date format (use YYYY-MM-DD or RFC3339)\n"
                "   - Missing required fields (name, due_date for some operations)\n"
                "   - Invalid user IDs (use get_circle_members first)"
            )
        elif status_code == 429:
            msg = (
                "Rate limit exceeded. The server is receiving too many requests.\n\n"
                "\U0001f4a1 Hint: Wait a few seconds before retrying. The rate limit is\n"
                "   typically 10 requests per second."
            )
        elif 400 <= status_code < 500:
            if api_error:
                msg = (
                    f"API Error: {api_error}\n\n"
                    "\U0001f4a1 Hint: Review the error message above and check:\n"
                    "   - Required fields are provided\n"
                    "   - Data types match expectations (IDs are integers, names are strings)\n"
                    "   - Values are in correct format (dates, colors, etc.)\n"
                    "   - User IDs exist in your circle (use get_circle_members to check)"
                )
            else:
                msg = (
                    f"Request failed with status {status_code}. Please check your input.\n\n"
                    "\U0001f4a1 Hint: Review the tool's input parameters and ensure:\n"
                    "   - Required fields are provided\n"
                    "   - Data types match expectations (IDs are integers, names are strings)\n"
                    "   - Values are in correct format (dates, colors, etc.)"
                )
        else:
            if api_error:
                msg = (
                    f"Server error ({status_code}): {api_error}\n\n"
                    "\U0001f4a1 Hint: This is a server-side issue. Try again in a moment.\n"
                    "   If the problem persists, check the Donetick server status."
                )
            else:
                msg = (
                    f"API request failed with status {status_code}.\n\n"
                    "\U0001f4a1 Hint: This is likely a server-side issue. Try again in a moment.\n"
                    "   If the problem persists, check the Donetick server status."
                )
        return f"Error: {msg}"

    if isinstance(exc, httpx.TimeoutException):
        logger.error(f"Timeout executing tool {tool_name}: {exc}", exc_info=True)
        return (
            "Error: Request timed out.\n\n"
            "\U0001f4a1 Hint: The Donetick server took too long to respond. This could mean:\n"
            "   - The server is under heavy load\n"
            "   - Network connectivity issues\n"
            "   - The server may be down\n"
            "Try again in a few moments."
        )

    # Kind of error message for validation or generic failure (safe to expose).
    logger.warning(f"Validation error in tool {tool_name}: {exc}")
    return (
        f"Validation Error: {exc}\n\n"
        "\U0001f4a1 Hint: This is a data validation error. Check that:\n"
        "   - All required parameters are provided\n"
        "   - Data types are correct (numbers as integers, text as strings)\n"
        "   - Values are in expected format (dates, emails, URLs, etc.)"
    )


def _guard(fn: Any) -> Any:
    """Wrap a tool so thrown errors become friendly text results."""

    @wraps(fn)
    async def wrapper(*args: Any, **kwargs: Any) -> str:
        try:
            return await fn(*args, **kwargs)
        except Exception as e:  # noqa: BLE001 - surface friendly message to model
            logger.error(f"Error executing tool {fn.__name__}: {e}", exc_info=True)
            return _error_text(fn.__name__, e)

    return wrapper


@mcp.tool()
@_guard
async def list_chores(
    filter_active: bool | None = None,
    assigned_to_user_id: int | None = None,
    detail_level: str = "full",
) -> str:
    """List all chores from Donetick.

    Args:
        filter_active: Filter by active status (true=active only, false=inactive only, null=all)
        assigned_to_user_id: Filter by assigned user ID (null=all users)
        detail_level: Response format (brief or full). Default full.
    """
    c = await get_client()
    chores = await c.list_chores(
        filter_active=filter_active,
        assigned_to_user_id=assigned_to_user_id,
    )
    if not chores:
        return "No chores found."

    if detail_level == "brief":
        brief = [
            {
                "id": ch.id,
                "name": ch.name,
                "isActive": ch.isActive,
                "assignedTo": ch.assignedTo,
                "nextDueDate": ch.nextDueDate,
            }
            for ch in chores
        ]
        result = {"count": len(brief), "chores": brief}
    else:
        result = {"count": len(chores), "chores": [ch.model_dump() for ch in chores]}

    return json.dumps(result, indent=2)


@mcp.tool()
@_guard
async def get_chore(chore_id: int) -> str:
    """Get details of a specific chore by its ID.

    Args:
        chore_id: The ID of the chore to retrieve
    """
    c = await get_client()
    chore = await c.get_chore(chore_id)
    if not chore:
        return f"Chore with ID {chore_id} not found."
    return json.dumps(chore.model_dump(), indent=2)


@mcp.tool()
@_guard
async def create_chore(
    name: str,
    description: str | None = None,
    due_date: str | None = None,
    created_by: int | None = None,
    usernames: list[str] | None = None,
) -> str:
    """Create a new chore in Donetick.

    Args:
        name: Chore name (required)
        description: Chore description (optional)
        due_date: Due date in YYYY-MM-DD or RFC3339 format (optional)
        created_by: User ID of the creator (optional)
        usernames: Assign creator by username instead of ID (optional)
    """
    c = await get_client()

    if usernames:
        username_map = await c.lookup_user_ids(usernames)
        if not username_map or len(username_map) != len(usernames):
            missing = [u for u in usernames if u not in (username_map or {})]
            return (
                f"Error: Could not find user(s) in circle: {', '.join(missing)}\n\n"
                "\U0001f4a1 Hint: Use get_circle_members to see available users.\n"
                "   Valid users must be members of your circle/household."
            )
        created_by = username_map.get(usernames[0])

    chore = await c.create_chore(name=name, description=description, due_date=due_date, created_by=created_by)
    return f"Successfully created chore '{chore.name}' (ID: {chore.id})\n\n{json.dumps(chore.model_dump(), indent=2)}"


@mcp.tool()
@_guard
async def complete_chore(chore_id: int, completed_by: int | None = None) -> str:
    """Mark a chore as complete.

    Args:
        chore_id: The ID of the chore to mark complete
        completed_by: User ID who completed the chore (optional)
    """
    c = await get_client()
    chore = await c.complete_chore(chore_id, completed_by=completed_by)
    return f"Successfully completed chore '{chore.name}' (ID: {chore.id})\n\n" + json.dumps(
        chore.model_dump(), indent=2
    )


@mcp.tool()
@_guard
async def update_chore(
    chore_id: int,
    name: str | None = None,
    description: str | None = None,
    nextDueDate: str | None = None,
    priority: int | None = None,
    points: int | None = None,
    isActive: bool | None = None,
    isPrivate: bool | None = None,
    requireApproval: bool | None = None,
    frequencyType: str | None = None,
    frequency: int | None = None,
    frequencyMetadata: dict | None = None,
    isRolling: bool | None = None,
    assignStrategy: str | None = None,
    notification: bool | None = None,
    notificationMetadata: dict | None = None,
    completionWindow: int | None = None,
    deadlineOffset: int | None = None,
) -> str:
    """Update an existing chore with new values.

    Only provide fields you want to change - other fields remain unchanged.

    Args:
        chore_id: The ID of the chore to update
        name: New chore name
        description: New chore description
        nextDueDate: New due date (ISO 8601 format)
        priority: Priority level (0=unset, 1=lowest, 4=highest)
        points: Points awarded for completion
        isActive: Enable/disable chore
        isPrivate: Hide from other circle members
        requireApproval: Requires approval to mark complete
        frequencyType: Frequency type
        frequency: Frequency value
        frequencyMetadata: Frequency metadata (days, time, timezone, weekPattern)
        isRolling: Rolling schedule vs fixed
        assignStrategy: Assignment rotation strategy
        notification: Enable notifications
        notificationMetadata: Notification settings (templates, nagging, predue)
        completionWindow: Seconds before due time when early completion is allowed
        deadlineOffset: Seconds after due time for grace period
    """
    c = await get_client()
    update_data: dict[str, Any] = {
        k: v
        for k, v in {
            "name": name,
            "description": description,
            "nextDueDate": nextDueDate,
            "priority": priority,
            "points": points,
            "isActive": isActive,
            "isPrivate": isPrivate,
            "requireApproval": requireApproval,
            "frequencyType": frequencyType,
            "frequency": frequency,
            "frequencyMetadata": frequencyMetadata,
            "isRolling": isRolling,
            "assignStrategy": assignStrategy,
            "notification": notification,
            "notificationMetadata": notificationMetadata,
            "completionWindow": completionWindow,
            "deadlineOffset": deadlineOffset,
        }.items()
        if v is not None
    }
    update = ChoreUpdate(**update_data)
    chore = await c.update_chore(chore_id, update)
    return f"Successfully updated chore '{chore.name}' (ID: {chore.id})\n\n" + json.dumps(chore.model_dump(), indent=2)


@mcp.tool()
@_guard
async def delete_chore(chore_id: int) -> str:
    """Delete a chore permanently.

    Only the chore creator can delete a chore.

    Args:
        chore_id: The ID of the chore to delete
    """
    c = await get_client()
    await c.delete_chore(chore_id)
    return f"Successfully deleted chore with ID {chore_id}."


@mcp.tool()
@_guard
async def update_chore_priority(chore_id: int, priority: int) -> str:
    """Update a chore's priority level (0-4).

    Args:
        chore_id: The ID of the chore to update
        priority: New priority level (0=unset, 1=lowest, 4=highest)
    """
    c = await get_client()
    chore = await c.update_chore_priority(chore_id, priority)
    return f"Successfully updated chore '{chore.name}' (ID: {chore.id}) priority to {priority}\n\n" + json.dumps(
        chore.model_dump(), indent=2
    )


@mcp.tool()
@_guard
async def update_chore_assignee(chore_id: int, user_id: int) -> str:
    """Reassign a chore to a different circle member.

    Args:
        chore_id: The ID of the chore to update
        user_id: User ID of the new assignee (from get_circle_members)
    """
    c = await get_client()
    chore = await c.update_chore_assignee(chore_id, user_id)
    return f"Successfully reassigned chore '{chore.name}' (ID: {chore.id}) to user {user_id}\n\n" + json.dumps(
        chore.model_dump(), indent=2
    )


@mcp.tool()
@_guard
async def skip_chore(chore_id: int) -> str:
    """Skip a chore without marking it complete.

    Args:
        chore_id: The ID of the chore to skip
    """
    c = await get_client()
    chore = await c.skip_chore(chore_id)
    return (
        f"Successfully skipped chore '{chore.name}' (ID: {chore.id}). "
        f"Next due date: {chore.nextDueDate}\n\n" + json.dumps(chore.model_dump(), indent=2)
    )


@mcp.tool()
@_guard
async def update_subtask_completion(chore_id: int, subtask_id: int, completed: bool) -> str:
    """Mark a subtask as complete or incomplete within a chore.

    Args:
        chore_id: The ID of the chore containing the subtask
        subtask_id: The ID of the subtask to update
        completed: True to mark complete, False to mark incomplete
    """
    c = await get_client()
    chore = await c.update_subtask_completion(chore_id, subtask_id, completed)

    total = len(chore.subTasks)
    done = sum(1 for st in chore.subTasks if st.get("completedAt"))
    pct = (done / total * 100) if total else 0
    lines = "\n".join(
        f"  {'\u2705' if st.get('completedAt') else '\u2b1c'} {st.get('name', 'Unnamed')} (ID: {st.get('id')})"
        for st in chore.subTasks
    )
    return (
        f"\u2705 Successfully updated subtask {subtask_id} on chore '{chore.name}' (ID: {chore.id})\n\n"
        f"\U0001f4ca Progress: {done}/{total} subtasks complete ({pct:.0f}%)\n\n"
        f"Subtasks:\n{lines}"
    )


@mcp.tool()
@_guard
async def get_circle_members() -> str:
    """Get all members in the circle (household/team)."""
    c = await get_client()
    members = await c.get_circle_members()
    blocks = []
    for m in members:
        role = "\U0001f451" if m.role == "admin" else "\U0001f464"
        status = "\u2705" if m.isActive else "\u274c"
        display = m.displayName or "(no display name)"
        blocks.append(
            f"{role} {status} {m.username}\n"
            f"  User ID: {m.userId}\n"
            f"  Display Name: {display}\n"
            f"  Role: {m.role}\n"
            f"  Points: {m.points} (Redeemed: {m.pointsRedeemed})"
        )
    return f"Found {len(members)} member(s) in your circle:\n\n" + "\n\n".join(blocks)


@mcp.tool()
@_guard
async def get_chore_history(chore_id: int) -> str:
    """Get completion history for a specific chore.

    Args:
        chore_id: The ID of the chore to fetch history for
    """
    c = await get_client()
    history = await c.get_chore_history(chore_id)
    if not history:
        return f"No completion history found for chore {chore_id}"

    entries = []
    for e in history:
        status = "\U0001f7e2" if e.performedAt else "\u23f3"
        by = f"user {e.completedBy}" if e.completedBy else "Unknown"
        at = e.performedAt or "Unknown"
        notes = e.note or "No notes"
        entries.append(
            f"{status} Completion ID: {e.id}\n"
            f"  \U0001f464 Completed by: {by}\n"
            f"  \U0001f4c5 Completed at: {at}\n"
            f"  \U0001f4dd Notes: {notes}"
        )
    return f"\U0001f4ca Completion History for Chore {chore_id}\nTotal completions: {len(history)}\n\n" + "\n\n".join(
        entries
    )


@mcp.tool()
@_guard
async def get_all_chores_history(limit: int = 50, offset: int = 0) -> str:
    """Get completion history for all chores with pagination.

    Args:
        limit: Maximum number of history entries (default 50, max 200)
        offset: Number of entries to skip for pagination
    """
    c = await get_client()
    history = await c.get_all_chores_history(limit=limit, offset=offset)
    if not history:
        return "No completion history found"

    by_chore: dict[int, list] = {}
    for e in history:
        by_chore.setdefault(e.choreId, []).append(e)

    sections = []
    for chore_id, entries in by_chore.items():
        lines = []
        for e in entries:
            by = f"user {e.completedBy}" if e.completedBy else "Unknown"
            at = e.performedAt or "Unknown"
            lines.append(f"  \u2705 {at} by {by}")
        sections.append(f"\U0001f3f7\ufe0f  Chore #{chore_id}\n" + "\n".join(lines))

    hint = ""
    if len(history) == limit:
        hint = f"\n\n\U0001f4a1 Showing {limit} entries (offset: {offset}). Use offset={offset + limit} to see more."
    return f"\U0001f4ca Chore Completion History\nShowing {len(history)} entries\n\n" + "\n\n".join(sections) + hint


@mcp.tool()
@_guard
async def get_chore_details(chore_id: int) -> str:
    """Get detailed chore information including completion statistics.

    Args:
        chore_id: The ID of the chore to fetch detailed statistics for
    """
    c = await get_client()
    d = await c.get_chore_details(chore_id)

    total = d.totalCompletedCount or 0
    last = d.lastCompletedDate or "Never"
    last_user = f"user {d.lastCompletedBy}" if d.lastCompletedBy else "N/A"
    avg = f"{d.averageDuration:.1f}s" if d.averageDuration else "N/A"

    recent = []
    if d.completionHistory:
        for e in d.completionHistory[:5]:
            at = e.performedAt or "Unknown"
            by = f"user {e.completedBy}" if e.completedBy else "Unknown"
            recent.append(f"  \u2705 {at} by {by}")
    hist = "\n".join(recent) if recent else "  No completions yet"

    return (
        f"\U0001f4ca Chore Details: {d.name}\n"
        f"ID: {d.id}\n\n"
        f"\U0001f4c8 Statistics:\n"
        f"  Total Completions: {total}\n"
        f"  Average Duration: {avg}\n\n"
        f"\U0001f550 Last Completion:\n"
        f"  Date: {last}\n"
        f"  By: {last_user}\n\n"
        f"\U0001f5dc Recent History (last 5):\n"
        f"{hist}"
    )


@mcp.tool()
@_guard
async def list_things() -> str:
    """List all things (trackable values)."""
    c = await get_client()
    things = await c.list_things()
    if not things:
        return "No things found."
    return "\n".join(f"Thing {t.id}: {t.name} (state: {t.state}, type: {t.type})" for t in things)


@mcp.tool()
@_guard
async def get_thing(thing_id: int) -> str:
    """Get a thing by its ID.

    Args:
        thing_id: The ID of the thing to retrieve
    """
    c = await get_client()
    thing = await c.get_thing(thing_id)
    if thing is None:
        return f"Thing with ID {thing_id} not found."
    return json.dumps(thing.model_dump(), indent=2)


@mcp.tool()
@_guard
async def get_thing_state(thing_id: int) -> str:
    """Get the current state of a thing.

    Args:
        thing_id: The ID of the thing
    """
    c = await get_client()
    thing = await c.get_thing(thing_id)
    if thing is None:
        return f"Thing with ID {thing_id} not found."
    return f"Thing {thing.id} ({thing.name}) state: {thing.state}"


@mcp.tool()
@_guard
async def change_thing_state(
    thing_id: int,
    set_value: str | None = None,
    op: str | None = None,
) -> str:
    """Change a thing's state.

    Provide set_value to set it directly, or op as a signed integer to add to a
    numeric state.

    Args:
        thing_id: The ID of the thing
        set_value: New state value to set
        op: Signed integer to add to the current numeric state (e.g. '-1')
    """
    c = await get_client()
    await c.change_thing_state(thing_id, set_value=set_value, op=op)
    return f"Thing {thing_id} state updated."


@mcp.tool()
@_guard
async def create_thing(name: str, type: str, state: str | None = None) -> str:
    """Create a new thing (trackable value).

    Args:
        name: The thing's name
        type: The thing's type (number, boolean, or text)
        state: Optional initial state value
    """
    c = await get_client()
    thing = await c.create_thing(name=name, type=type, state=state)
    return json.dumps(thing.model_dump(), indent=2)


def main() -> None:
    """Main entry point for the MCP server."""
    logger.info(f"Starting Donetick MCP Server v{__version__}")
    logger.info(f"Connecting to: {sanitize_url(config.donetick_base_url or '')}")
    # transport comes from FASTMCP_* env vars (default stdio); blocks until the server stops
    mcp.run()


def sanitize_url(url: str) -> str:
    """Sanitize URL for logging by hiding host details."""
    try:
        parsed = urllib.parse.urlparse(url)
        return f"{parsed.scheme}://[SERVER]{parsed.path}"
    except Exception:
        return "[URL]"


if __name__ == "__main__":
    main()
