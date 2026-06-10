# Tools

Built-in tools agents call during a run. All filesystem tools execute inside a **workspace jail** (paths cannot escape `WORKSPACE_ROOT`).

## Built-in tools

| Tool | Purpose | Key args |
|------|---------|----------|
| `read_file` | Read a text file | `path` |
| `list_files` | List files in a directory | `path`, `glob` |
| `search_workspace` | Hybrid semantic + grep search | `query`, `path`, `max_hits` |
| `http_request` | HTTP GET/POST to allowlisted hosts | `url`, `method`, … |

Implementations: `tools/tools/builtins/`.

## Attach tools to agents

```yaml
# agents/builtins/manifests/research.yaml
tools:
  - read_file
  - list_files
  - search_workspace
  - http_request
```

## Semantic search

When `SEMANTIC_SEARCH_ENABLED=true` and Qdrant is healthy:

```bash
aicery workspace index guide/
curl -X POST http://localhost:8000/v1/workspace/index \
  -H "X-API-Key: dev" \
  -d '{"workspace_id":"local","paths":["guide/"]}'
```

## HTTP allowlist

Only hosts in `ALLOWED_HTTP_HOSTS` (default `api.github.com,httpbin.org`) are permitted.

## Trace

Each tool call is recorded in trace steps (`type: tool`). Inspect with `aicery trace <run_id>`.

## Add a builtin tool

1. Define schema + handler in `tools/tools/builtins/your_tool.py`
2. Register via `@tool("name", schema)`
3. Import in `tools/tools/builtins/__init__.py`
4. Add name to agent manifest `tools:` list

Use `jail_path(workspace_root, path)` for filesystem access.

## Related

- [Agents](agents.md)
- [Plugins](plugins.md)
- [Replay](replay.md)
