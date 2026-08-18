# donetick-mcp

Model Context Protocol (MCP) server for [Donetick](https://donetick.com) chores management.
Exposes Donetick as MCP tools (chore management, labels, circle/users, history/analytics) with
JWT auth, token-bucket rate limiting, and connection pooling. Stack and versions live in
`pyproject.toml` and `server.py` - read those for the current shape, don't trust this file.

## Common Tasks

```bash
mise run check    # hk: ruff, actionlint, yamllint, yamlfmt, pkl
mise run fix      # hk fix: auto-fix the same
mise run test     # uv run --extra dev pytest
```

`mise run` is the command surface - use it for everything; no direct tool invocation. New tool /
model / API method flow lives in the `add-tool` skill. Run `mise install` once to get the toolchain
(uv, ruff, hk, ...).

## Release

Merging to `main` triggers `.github/workflows/release.yml` (release-please-action v4): it opens a
`release: vX.Y.Z` PR from Conventional Commits. Merge that PR to cut a release - release-please
bumps the version in `pyproject.toml` + README, tags it, and updates `CHANGELOG.md`. Config lives in
`.release-please-config.json` / `.release-please-manifest.json`.

- Conventional commits drive the version bump and changelog; `chore` is hidden, breaking changes
  bump major.
- Multi-change PRs: use footer syntax (one conventional-commit stanza per change) so each lands as
  its own changelog entry - see the `release-please-pr` skill.

## Layout

- `src/donetick_mcp/server.py` - all MCP tools (async funcs with `@mcp.tool` + `_guard`)
- `src/donetick_mcp/client.py` - httpx API client (rate limiting, retry, auth)
- `src/donetick_mcp/models.py` - Pydantic request/response models
- `src/donetick_mcp/config.py` - env-driven config
- `tests/` - pytest suite (mocked + `live_api` integration)
- `.agents/skills/add-tool/` - repo-local skill for adding a tool
- Types/chore/version managed by release-please (see `.release-please-*.json` and `cli/` GH actions)

## Conventions

- camelCase field names in API payloads (Donetick accepts both, we standardize camelCase)
- List endpoints need trailing slashes (`/api/v1/chores/`), `put /api/v1/chores/` takes the ID in
  the body, not the URL
- If a chore has `assignedTo`, that user ID must be in `assignees` or the API 400s
- Ad-hoc analysis scripts go in `tmp/` (gitignored); formal tests go in `tests/`
- Don't create `docs/adr/` or `CONTEXT.md`; repo metadata stays out-of-tree
- Commit messages use Conventional Commits: `feat`, `fix`, `chore`, `refactor`, `docs`, `ci`, ...
  Scope optional (e.g. `fix(update_chore): ...`). release-please drives versioning + changelog from
  these.

## Domain

- Chore - a household task with due date, frequency, assignees, sub-tasks, labels, priority
- Circle - the household/group a user belongs to; all operations are circle-scoped
- Full API - the `/api/v1/` endpoints this server targets (not the external API)
- Sub-task - checklist item on a chore with its own completion state
- frequencyMetadata - recurrence config (unit, timezone, days, time, weekPattern, ...)

## Links

- Repo: git@github.com:trash-panda-v91-beta/donetick-mcp.git
