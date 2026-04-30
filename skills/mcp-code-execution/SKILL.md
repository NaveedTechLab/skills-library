---
name: mcp-code-execution
description: Execute MCP interactions via code scripts instead of direct agent tool calls. Use when Claude needs to interact with MCP servers through wrapped APIs rather than direct tool calls. Scripts wrap MCP server APIs, no MCP tools loaded directly into agent context, and return filtered minimal results only.
---

# MCP Code Execution

This skill implements the "MCP Server as Skill" pattern by wrapping frequent MCP server calls in Python scripts.

## Usage
Use this skill when you need to interact with MCP servers (like GDrive, databases, etc.) through wrapped APIs rather than direct tool calls. The skill will:
1. Execute MCP server calls through Python scripts
2. Filter data within the script to reduce token usage
3. Return only relevant results to the agent context

## Process
The interaction is handled by the supporting scripts which:
- Wrap MCP server APIs in Python functions
- Perform data filtering within the script
- Return only relevant rows (e.g., top 5) to prevent token bloat
- Minimize data sent back to the agent context