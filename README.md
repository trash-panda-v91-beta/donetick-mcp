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

## Tools

Chores: `list_chores`, `get_chore`, `create_chore`, `complete_chore`, `update_chore`, `delete_chore`, `update_chore_priority`, `update_chore_assignee`, `skip_chore`, `update_subtask_completion`

Things: `list_things`, `get_thing`, `get_thing_state`, `change_thing_state`

Circle: `get_circle_members`

History: `get_chore_history`, `get_all_chores_history`, `get_chore_details`

## License

MIT
