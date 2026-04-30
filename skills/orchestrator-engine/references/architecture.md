# Orchestrator Engine Reference Guide

## Architecture Overview

The Orchestrator Engine is designed as a modular system with the following components:

1. **File Router**: Determines which watcher or processor should handle a file
2. **Process Coordinator**: Manages execution of Claude Code processes
3. **Output Aggregator**: Combines results from multiple processes
4. **Configuration Manager**: Handles settings and routing rules
5. **Workflow Engine**: Executes multi-step operations

## Configuration Format

The orchestrator uses a JSON/YAML configuration file with the following structure:

```json
{
  "routing_rules": [
    {
      "pattern": "**/*.py",
      "watcher": "python-analyzer",
      "priority": 10
    }
  ],
  "concurrency_limits": {
    "max_processes": 5,
    "max_concurrent_files": 10
  },
  "output_settings": {
    "default_output_dir": "./processed",
    "preserve_original": true,
    "log_level": "INFO"
  },
  "watcher_endpoints": {
    "python-analyzer": "http://localhost:8001",
    "javascript-analyzer": "http://localhost:8002"
  }
}
```

### Routing Rules

Routing rules determine how files are distributed to different watchers:

- **pattern**: File matching pattern (supports glob patterns)
- **watcher**: Name of the target watcher
- **priority**: Higher priority rules are evaluated first

### Concurrency Limits

Controls how many processes run simultaneously:

- **max_processes**: Maximum concurrent Claude Code processes
- **max_concurrent_files**: Maximum files processed at once

### Output Settings

Configures how results are saved:

- **default_output_dir**: Base directory for output files
- **preserve_original**: Whether to keep original files
- **log_level**: Logging verbosity (DEBUG, INFO, WARNING, ERROR)

## Workflow Definitions

Complex operations are defined as workflows with multiple steps:

```json
{
  "name": "Code Quality Pipeline",
  "description": "Analyze code, generate documentation, and create reports",
  "steps": [
    {
      "name": "analyze_code",
      "type": "file_processing",
      "directory": "./src",
      "recursive": true
    },
    {
      "name": "generate_docs",
      "type": "custom_command",
      "command": "python generate_docs.py --source ./src --output ./docs"
    },
    {
      "name": "create_report",
      "type": "custom_command",
      "command": "python create_report.py --input ./analysis --output ./report"
    }
  ]
}
```

## File Routing Patterns

### Supported Pattern Types

The orchestrator supports standard glob patterns:

- `*.py` - Matches Python files in current directory
- `**/*.py` - Matches Python files recursively
- `src/**/test_*.py` - Matches test files in src directory
- `{*.js,*.ts}` - Matches JavaScript or TypeScript files

### Priority System

When multiple rules match a file, the one with the highest priority is used:

1. Rules with higher priority values are evaluated first
2. If priorities are equal, rules are evaluated in order of definition
3. First matching rule determines the target watcher

## Process Coordination

### Process Lifecycle

1. **Queue**: Files are added to processing queue
2. **Route**: Router determines target watcher
3. **Schedule**: Process scheduled respecting concurrency limits
4. **Execute**: Claude Code process runs
5. **Collect**: Results gathered and stored
6. **Report**: Status reported to user

### Error Handling

The orchestrator implements robust error handling:

- Failed processes are retried with exponential backoff
- Errors are logged with detailed context
- Failed files can be reprocessed separately
- Overall workflow continues despite individual failures

## Performance Optimization

### Batch Processing

Files are processed in batches to minimize overhead:

- Configure batch size based on system capacity
- Balance between throughput and resource usage
- Monitor system resources during processing

### Caching

Results are cached to avoid redundant processing:

- File checksums determine if reprocessing is needed
- Cache invalidation based on file modification time
- Persistent cache across orchestrator restarts

## Integration Points

### With Claude Code

The orchestrator interfaces with Claude Code through:

- Command-line interface
- Standard input/output channels
- Configuration files
- Process return codes

### With External Systems

The orchestrator can integrate with:

- File monitoring systems
- CI/CD pipelines
- Notification services
- Storage systems

## Security Considerations

### File Access

- Restrict orchestrator to specific directory trees
- Validate file paths to prevent directory traversal
- Sanitize file contents before processing

### Process Execution

- Limit process execution time
- Monitor resource usage
- Isolate processes to prevent interference

### Configuration

- Validate configuration files before use
- Encrypt sensitive information
- Audit configuration changes

## Monitoring and Logging

### Log Levels

- **DEBUG**: Detailed diagnostic information
- **INFO**: Normal operational messages
- **WARNING**: Potential issues requiring attention
- **ERROR**: Problems that prevent operation

### Metrics

Track these key metrics:

- Processing throughput (files/minute)
- Error rates
- Resource utilization
- Queue lengths

### Alerts

Configure alerts for:

- High error rates
- Resource exhaustion
- Processing delays
- Failed workflows