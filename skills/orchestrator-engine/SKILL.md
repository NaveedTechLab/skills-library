---
name: orchestrator-engine
description: Master orchestrator for triggering Claude Code runs, routing files, and coordinating watcher outputs. Use when Claude needs to coordinate multiple Claude Code processes, route files between different watchers and processors, or manage complex multi-step workflows involving file processing and AI interaction.
---

# Orchestrator Engine

## Overview

The Orchestrator Engine is a master coordination system that manages multiple Claude Code processes, routes files between different watchers and processors, and coordinates complex multi-step workflows involving file processing and AI interaction.

## Core Capabilities

The orchestrator engine provides:

1. **Process Orchestration**: Triggers and manages multiple Claude Code runs
2. **File Routing**: Directs files to appropriate watchers and processors based on content/type
3. **Output Coordination**: Consolidates outputs from multiple watchers and processors
4. **Workflow Management**: Manages complex multi-step processes with dependencies
5. **Resource Management**: Coordinates access to shared resources and prevents conflicts

## Usage Scenarios

Use the orchestrator engine when:
- Multiple Claude Code processes need to be coordinated
- Files need to be routed to specific watchers based on content or type
- Complex workflows span multiple processing steps
- Output from different watchers needs to be consolidated
- Resource contention between processes needs to be managed

## Process Orchestration

### Triggering Claude Code Runs

The orchestrator can trigger Claude Code runs based on various conditions:

```python
# Example orchestration logic
def trigger_claude_process(file_path, context, requirements):
    """
    Trigger a Claude Code process with specific parameters
    """
    # Determine appropriate Claude Code configuration
    config = determine_config(file_path, context)

    # Launch Claude Code process
    process = launch_claude_code(config)

    # Monitor and coordinate
    return process
```

### Process Coordination Patterns

**Sequential Processing**: Chain processes where output of one becomes input of the next
**Parallel Processing**: Run multiple processes simultaneously on different file sets
**Conditional Processing**: Branch based on file content or processing results
**Dependency Management**: Ensure processes run in correct order with proper inputs

## File Routing System

### Routing Rules

Files are routed based on:

- **File Extensions**: `.py`, `.md`, `.json`, etc.
- **Content Patterns**: Keywords, structure, or specific markers
- **Context Indicators**: Surrounding file structure or metadata
- **Processing Requirements**: Specific tools or capabilities needed

### Routing Examples

```python
# Route Python files to code analysis
if file_path.endswith('.py'):
    route_to_watcher('code-analyzer', file_path)

# Route markdown files to documentation processor
elif file_path.endswith('.md'):
    route_to_watcher('documentation-processor', file_path)

# Route configuration files to appropriate handlers
elif file_path.endswith(('.json', '.yaml', '.yml')):
    route_to_watcher('config-processor', file_path)
```

## Output Coordination

### Consolidation Strategies

- **Aggregation**: Combine outputs from multiple watchers into unified reports
- **Cross-referencing**: Link related findings across different processing streams
- **Conflict Resolution**: Handle contradictory outputs from different processors
- **Quality Assurance**: Validate outputs meet specified criteria

### Output Formats

The orchestrator supports various output formats:
- Structured JSON for programmatic consumption
- Markdown reports for human readability
- Action items for task tracking
- Integration-ready formats for other tools

## Workflow Management

### Multi-Step Workflows

Complex workflows are broken into manageable steps:
1. **Discovery**: Identify files and processes needed
2. **Planning**: Sequence operations and allocate resources
3. **Execution**: Run coordinated processes
4. **Validation**: Check outputs and handle errors
5. **Reporting**: Consolidate and present results

### Error Handling and Recovery

- **Graceful Degradation**: Continue operation when individual components fail
- **Retry Logic**: Automatically retry failed operations
- **Fallback Procedures**: Alternative approaches when primary methods fail
- **State Persistence**: Maintain progress across interruptions

## Implementation Guidelines

### Best Practices

1. **Modular Design**: Keep orchestrator logic separate from watcher implementations
2. **Configuration Driven**: Use configuration files to define routing rules and workflows
3. **Event-Driven**: Respond to file system events rather than polling
4. **Resource Awareness**: Track resource usage and prevent overload
5. **Logging and Monitoring**: Maintain detailed logs for troubleshooting

### Performance Considerations

- **Batch Processing**: Group operations to reduce overhead
- **Caching**: Store results of expensive operations
- **Throttling**: Control rate of process launches
- **Memory Management**: Clean up resources after use

## Resources

This skill includes example resource directories that demonstrate how to organize different types of bundled resources:

### scripts/
Executable Python scripts for orchestrator operations including process management, file routing, and workflow coordination.

### references/
Detailed documentation for orchestration patterns, configuration formats, and integration guidelines.

### assets/
Template configuration files and workflow definitions for common orchestration scenarios.

---

The orchestrator engine enables sophisticated automation of Claude Code workflows while maintaining flexibility and reliability.