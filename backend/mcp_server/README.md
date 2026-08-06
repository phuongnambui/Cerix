# Cerix MCP Server

Exposes Cerix's query layer as MCP tools so any MCP client (Claude Desktop,
Claude Code, etc.) can ask Cerix about tech news impact and sourcing.

**Tools:**
- `top_stories(category?, min_score?, limit?)` — highest-impact stories, sorted by score
- `story_confidence(url)` — how well-sourced a story is (rumored / corroborated / confirmed)

**Layout:** `queries.py` is the plain, MCP-free query layer (testable with
`python queries.py`); `server.py` is a thin MCP wrapper over it (stdio transport).

## Connecting to Claude Desktop

1. Open the config file (Claude menu → Settings… → Developer → Edit Config), or
   edit it directly:
   - macOS: `~/Library/Application Support/Claude/claude_desktop_config.json`
   - Windows: `%APPDATA%\Claude\claude_desktop_config.json`

2. Add the `cerix` entry (merge into `mcpServers` if the file already has one).
   **Paths must be absolute** — Claude Desktop spawns the server from an
   arbitrary working directory:

```json
{
  "mcpServers": {
    "cerix": {
      "command": "/Users/phuongnam/Cerix/venv/bin/python",
      "args": ["/Users/phuongnam/Cerix/backend/mcp_server/server.py"]
    }
  }
}
```

Using the venv's python (not system `python3`) matters: it's the interpreter
with `mcp`, `chromadb`, etc. installed.

3. Fully quit and restart Claude Desktop. The tools appear under the
   connectors indicator (bottom-left of the input box) → Manage connectors →
   `cerix`.

4. Try: *"What are the top tech stories Cerix is tracking right now?"* —
   Claude should call `top_stories` and every call asks for your approval
   first.

## Troubleshooting

- Logs: `~/Library/Logs/Claude/mcp-server-cerix.log` (macOS). Stdio servers
  log to stderr, so this file isn't only errors.
- Test the server outside Claude Desktop first: `venv/bin/python backend/mcp_server/server.py`
  should start and wait silently on stdin (Ctrl-C to exit). If it crashes on
  startup, fix that before debugging the Desktop config.
- The Chroma path is resolved against the project root even when the server
  is spawned from another directory (see chroma_client.py) — if queries
  return nothing, confirm `CHROMA_PATH` in `.env` points at the right store.
