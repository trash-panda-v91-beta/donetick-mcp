# Donetick MCP

An MCP server that turns your Donetick instance into tools. Create, list, update, complete, and skip chores, manage things, and check circle members and completion history.

Authenticated with a Donetick API token (no username or password). Built with FastMCP.

## Run with Docker

You need a Donetick instance and an access token (settings > Advanced > API).

```bash
docker build -t donetick-mcp .
docker run -e DONETICK_BASE_URL=https://donetick.example.com \
  -e DONETICK_API_TOKEN=your-token \
  donetick-mcp
```

## Settings

| name | default | notes |
| ---- | ------- | ----- |
| `DONETICK_BASE_URL` | - | required, https only |
| `DONETICK_API_TOKEN` | - | required, from Donetick settings |
| `LOG_LEVEL` | INFO | |
| `RATE_LIMIT_PER_SECOND` | 10 | |
| `RATE_LIMIT_BURST` | 10 | |

Values can come from a `.env` file in the working directory.

## Serve over HTTP

By default the server talks stdio (one process per client). To expose it as an
HTTP MCP endpoint behind a gateway (e.g. LiteLLM), set the FastMCP transport
env vars - no code change required:

| env | default |
| --- | ------- |
| `FASTMCP_TRANSPORT` | `stdio` |
| `FASTMCP_HOST` | `127.0.0.1` |
| `FASTMCP_PORT` | `8000` |
| `FASTMCP_STREAMABLE_HTTP_PATH` | `/mcp` |

Example - serve streamable-http on all interfaces:

```bash
FASTMCP_TRANSPORT=streamable-http FASTMCP_HOST=0.0.0.0 FASTMCP_PORT=8000 \
  donetick-mcp
```

## Tools

Chores: `list_chores`, `get_chore`, `create_chore`, `complete_chore`, `update_chore`, `delete_chore`, `update_chore_priority`, `update_chore_assignee`, `skip_chore`, `update_subtask_completion`, `archive_chore`, `unarchive_chore`, `undo_chore`, `approve_chore`, `reject_chore`, `start_chore`, `pause_chore`

Things: `list_things`, `get_thing`, `get_thing_state`, `change_thing_state`, `create_thing`, `update_thing`, `delete_thing`, `get_thing_history`

Circle: `get_circle_members`

Projects: `list_projects`, `create_project`, `update_project`, `delete_project`

History: `get_chore_history`, `get_all_chores_history`, `get_chore_details`

## License

MIT
