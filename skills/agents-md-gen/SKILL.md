---
name: agents-md-gen
description: Generate valid AGENTS.md files for repositories according to AAIF standards. Use when Claude needs to create or update AGENTS.md files that document AI agents in a repository following standard format and best practices.
---

# AGENTS.md Generator

This skill generates AGENTS.md files that document AI agents in a repository according to AAIF (AI Agent Interoperability Framework) standards. It analyzes a repository's structure, identifies agent configurations and conventions, and outputs a properly formatted AGENTS.md that makes the repo AI-tool-friendly.

Use this skill any time you set up a new agent-enabled project or onboard an existing repo to the AAIF standard.

## Quick Start

```bash
# From the repo root, invoke the skill
/agents-md-gen

# The skill will scan your repo and write AGENTS.md
```

The output file is placed at the repository root as `AGENTS.md`.

## Key Features

- Scans repository structure for agent-related files (`.claude/`, `skills/`, `agents/`, config YAMLs)
- Identifies and documents available tools, permissions, and memory configuration
- Outputs AAIF-compliant AGENTS.md with correct section headings
- Adds repository conventions (coding style, commit format, test commands)
- Idempotent — re-running updates rather than overwrites existing content

## Process

1. Analyze the repository structure
2. Identify agent-related files and configurations
3. Document repository conventions and guidelines
4. Generate a properly formatted AGENTS.md file

The generation logic is implemented in the supporting script to maintain consistency and follow AAIF standards.

## When NOT to Use This Skill

- **Non-agent repositories** — if there are no AI agents or Claude Code integrations, an AGENTS.md adds noise without value
- **Already documented projects** — if a complete, accurate AGENTS.md exists, editing it manually is faster than regenerating
- **Proprietary internal tooling** — if your agent configuration contains secrets, verify the generated file before committing

## Common Mistakes

- Running the skill in a subdirectory instead of the repo root — the scanner misses top-level config files
- Not reviewing the generated file before committing — always check agent permissions and memory settings are correct
- Leaving placeholder tool descriptions — fill in real examples so other AI tools can understand the agent's capabilities

## Related Skills

- [`mcp-builder`](../mcp-builder/SKILL.md) — Build the MCP servers that AGENTS.md documents
- [`implementation-specialist`](../implementation-specialist/SKILL.md) — Implement the agent workflows referenced in AGENTS.md
- [`audit-logging-system`](../audit-logging-system/SKILL.md) — Add audit logging to the agents documented here
