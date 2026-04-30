---
name: mcp-code-execution
description: Execute MCP interactions via code scripts instead of direct agent tool calls. Use when Claude needs to interact with MCP servers through wrapped APIs rather than direct tool calls. Scripts wrap MCP server APIs, no MCP tools loaded directly into agent context, and return filtered minimal results only.
---

# MCP Code Execution

This skill implements the "MCP Server as Skill" pattern — wrapping MCP server calls in Python scripts so that only filtered, minimal results are returned to the agent context. This keeps token usage low and prevents context bloat when interacting with large data sources like Google Drive, databases, or file systems.

Use this skill when an MCP server's raw output would flood the context window, or when you want deterministic, script-controlled filtering of MCP results.

## Quick Start

```python
# Example: wrapped GDrive search returning top 5 results
# scripts/gdrive_search.py
from mcp_client import MCPClient

client = MCPClient("gdrive-server")
results = client.call("search", {"query": "Q3 report"})
# Filter to top 5, return only name + id
top5 = [{"name": r["name"], "id": r["id"]} for r in results[:5]]
print(top5)
```

```bash
# Claude calls the script, not the MCP tool directly
python scripts/gdrive_search.py
```

## Key Features

- Wraps MCP server API calls in Python scripts for controlled execution
- Filters data within the script before returning results to agent context
- Returns only relevant rows (configurable limit, default top 5) to prevent token bloat
- No MCP tools loaded directly into agent context — all calls go through scripts
- Supports any MCP server (GDrive, databases, file system, Slack, etc.)

## Process

1. Execute MCP server calls through Python scripts
2. Filter data within the script to reduce token usage
3. Return only relevant results to the agent context

The interaction is handled by the supporting scripts which wrap MCP server APIs and minimize data returned.

## When NOT to Use This Skill

- **One-off MCP queries** — if you only need a single result and the server's output is small, calling the tool directly is simpler
- **Real-time streaming data** — script-wrapped calls add latency; use direct tool calls for time-sensitive operations
- **MCP servers with built-in filtering** — if the server already returns paginated, minimal results, wrapping it adds unnecessary indirection

## Common Mistakes

- Returning full API response objects instead of filtering inside the script — defeats the purpose and bloats context anyway
- Hard-coding the top-N limit without making it configurable — callers can't adjust result count when needed
- Not handling MCP server errors in the script — uncaught exceptions crash silently and leave the agent without feedback

## Related Skills

- [`mcp-builder`](../mcp-builder/SKILL.md) — Build the MCP servers that this skill wraps
- [`code-validation-sandbox`](../code-validation-sandbox/SKILL.md) — Validate the wrapper scripts before deploying
- [`orchestrator-engine`](../orchestrator-engine/SKILL.md) — Orchestrate multiple MCP script calls in sequence
