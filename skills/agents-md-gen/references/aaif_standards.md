# AAIF Standards for AGENTS.md

## Overview

The AI Agent Interoperability Framework (AAIF) defines standards for documenting AI agents in repositories. This document outlines the required elements and format for compliant AGENTS.md files.

## Required Sections

Every AGENTS.md file must contain:

1. **Header**: The title "AI Agents" and a brief introduction
2. **Agent List**: Individual sections for each agent with standardized fields
3. **Index**: Optional but recommended for repositories with many agents

## Agent Section Requirements

Each agent documented in the AGENTS.md must include these fields:

### Mandatory Fields

- **Name**: Descriptive name of the agent
- **Purpose**: Brief description of what the agent does (1-2 sentences)
- **Type**: Category of the agent (Assistant, Tool, Orchestrator, etc.)
- **Interface**: How to interact with the agent (API, CLI, UI, etc.)

### Recommended Fields

- **Capabilities**: List of main functions the agent can perform
- **Dependencies**: External services, models, or tools required
- **Configuration**: Settings or parameters needed to run the agent
- **Usage**: Example usage scenarios or commands
- **Integration Points**: How this agent connects with other components
- **Version**: Current version of the agent
- **Author/Maintainer**: Who is responsible for the agent

## Format Guidelines

### Markdown Structure

```markdown
# AI Agents

This repository contains the following AI agents:

## [Agent Name]

- **Purpose**: [Brief description of what the agent does]
- **Type**: [Assistant, Tool, Orchestrator, etc.]
- **Interface**: [How to interact with the agent - API, CLI, UI, etc.]
- **Capabilities**: [List of main functions the agent can perform]
- **Dependencies**: [External services, models, or tools required]
- **Configuration**: [Settings or parameters needed to run the agent]
- **Usage**: [Example usage scenarios or commands]
- **Integration Points**: [How this agent connects with other components]
```

### Naming Conventions

- Agent names should be descriptive and unique
- Use PascalCase or camelCase for consistency
- Avoid generic names like "Agent1" or "MainAgent"
- Include the domain or function in the name when possible

### Content Guidelines

- Purpose descriptions should be concise but informative
- Capabilities should be specific and actionable
- Dependencies should list versions when relevant
- Usage examples should be copy-paste runnable where possible

## Validation Checklist

Before finalizing an AGENTS.md file, ensure:

- [ ] All mandatory fields are present for each agent
- [ ] Agent names are unique and descriptive
- [ ] Purpose descriptions are clear and concise
- [ ] Interface specifications are accurate
- [ ] No sensitive information is exposed in the documentation
- [ ] All referenced files/configurations exist in the repository
- [ ] Cross-references between agents are accurate

## Common Anti-Patterns to Avoid

- Including sensitive information like API keys or credentials
- Vague capability descriptions that don't help users understand what the agent does
- Missing dependency information that prevents successful deployment
- Inconsistent formatting between different agent sections
- Duplicate or outdated information

## Example Valid AGENTS.md

```markdown
# AI Agents

This repository contains the following AI agents:

## CustomerSupportAssistant

- **Purpose**: Handles customer inquiries and support tickets automatically
- **Type**: Assistant
- **Interface**: REST API
- **Capabilities**:
  - Answer frequently asked questions
  - Route complex issues to human agents
  - Retrieve account information securely
- **Dependencies**: OpenAI GPT-4, PostgreSQL database
- **Configuration**: OPENAI_API_KEY, DATABASE_URL
- **Usage**: POST to /api/chat with user message
- **Integration Points**: Connects to CRM system and knowledge base

## DataProcessingTool

- **Purpose**: Processes and analyzes large datasets for insights
- **Type**: Tool
- **Interface**: CLI and Python API
- **Capabilities**:
  - Clean and normalize data
  - Generate statistical summaries
  - Export results in multiple formats
- **Dependencies**: Pandas, NumPy, SciPy
- **Configuration**: Memory limits, processing threads
- **Usage**: data-process --input data.csv --output results.json
- **Integration Points**: Accepts CSV, JSON, Excel formats
```