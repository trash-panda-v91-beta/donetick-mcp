---
name: add-tool
description: Add a new MCP tool, API method, or model to this server. Use when implementing a new tool, extending the Donetick API surface, or "add a tool" / "add an endpoint". Covers the 4-place pipeline (tool, client method, models, tests).
---

# Add a Tool/Endpoint

A new capability touches these spots, in order. Do them all, then run the checks.

## 1. Tool - `src/donetick_mcp/server.py`

Define an async function with `@mcp.tool()` + `@_guard`, returning `json.dumps(...)`. FastMCP builds
the schema from the typed signature + docstring. Read the nearest existing `@mcp.tool` in the file
and copy its shape - this is the source of truth, not this guide.

## 2. Client method - `src/donetick_mcp/client.py`

Add a method to `DonetickClient` and call it from the tool via `get_client()`. Use an `httpx` request against the full API. Remember:
- list endpoints need a trailing slash (`/api/v1/chores/`); updates use `PUT /api/v1/chores/` with
  the ID in the body, not the URL
- single-chore fetches go through `_get_chore_cached` (60s TTL) when the result should be cached
- respect the rate limiter via the existing `_request` path

## 3. Models - `src/donetick_mcp/models.py`

Add Pydantic models for any request/response shapes. Use camelCase field names. Add validators for
constraints (ranges, enums, date formats) matching the existing pattern.

## 4. Tests - `tests/`

Tests live in `tests/unit/` (mocked), `tests/integration/` (full mock workflows), `tests/live/`
(real instance, marked skip_in_ci/live_api).

- `tests/unit/test_client.py` - mock the httpx transport; assert the method hits the right
  URL/method, sends camelCase fields, and parses the response
- `tests/unit/test_mcp_tools.py` - mock the `DonetickClient` and assert the tool returns the
  right output for a given input

## Verify

```bash
mise run check   # ruff + yaml + actionlint
mise run test    # pytest
```

Commit style: `feat: <what the tool does>` (e.g. `feat: add update_chore_priority tool`). Since
release-please drives versioning and the changelog from Conventional Commits on `main`, a `feat`
commit bumps the minor version on release.
