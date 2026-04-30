# MCP Wrapping Best Practices

## Overview

This document provides best practices for wrapping Model Context Protocol (MCP) server APIs in executable scripts. The practices ensure security, performance, and maintainability while enforcing the constraints of the MCP-code-execution skill.

## Security Considerations

### Input Validation
- Always validate input parameters before processing
- Implement strict type checking for all inputs
- Use allowlists for acceptable values where possible
- Sanitize all user-provided inputs to prevent injection attacks

### Command Safety
- Never execute user-provided commands directly without sanitization
- Implement command allowlists for safe operations
- Prevent dangerous operations (rm, mv, dd, mkfs, etc.) in restricted environments
- Use timeouts to prevent long-running or hanging operations

### Access Control
- Implement proper authentication for MCP API calls
- Use principle of least privilege for all operations
- Validate permissions before executing operations
- Log all operations for audit trail

## Performance Optimization

### Result Filtering
- Always limit result sets to essential information only
- Implement pagination for large result sets
- Use streaming for large data operations
- Cache frequently accessed data when appropriate

### Resource Management
- Set appropriate timeouts for all operations
- Implement proper cleanup for temporary resources
- Monitor resource usage and set limits
- Use asynchronous operations where appropriate

### Efficiency Patterns
- Batch similar operations together when possible
- Minimize the number of MCP API calls
- Use bulk operations instead of individual operations
- Implement proper error handling to prevent retries

## Script Design Patterns

### Wrapper Structure
```bash
#!/bin/bash
# MCP wrapper script template

set -e  # Exit on error

# Function to validate inputs
validate_inputs() {
    local input="$1"

    # Add validation logic here
    if [ -z "$input" ]; then
        echo "ERROR: Required input is missing"
        exit 1
    fi
}

# Function to execute MCP operation
execute_mcp_operation() {
    local params="$1"

    # Execute the actual operation
    # This is where you'd call the MCP API
    # Return minimal filtered results
}

# Main function
main() {
    local operation="$1"
    local param1="$2"
    local param2="$3"

    validate_inputs "$param1"
    execute_mcp_operation "$param1" "$param2"
}

main "$@"
```

### Error Handling
- Implement graceful error handling for all operations
- Return meaningful error messages without exposing system details
- Log errors for debugging while keeping user output minimal
- Use appropriate exit codes for different error types

### Output Filtering
- Always filter output to essential information only
- Implement configurable output limits
- Use structured output formats (JSON, etc.) when appropriate
- Sanitize output to remove sensitive information

## MCP-Specific Patterns

### File Operations
- Implement proper file path validation to prevent directory traversal
- Use absolute paths when possible
- Validate file types and sizes before operations
- Implement proper file locking for concurrent access

### Network Operations
- Implement proper timeout handling for network requests
- Validate URLs and endpoints before requests
- Handle network errors gracefully
- Implement retry logic with exponential backoff

### State Management
- Use temporary storage for intermediate results
- Implement proper cleanup of temporary data
- Use atomic operations where possible
- Implement proper synchronization for concurrent access

## Result Filtering Techniques

### Content Filtering
- Use pattern matching to extract relevant information
- Implement configurable filters based on context
- Use regular expressions for complex filtering
- Allow multiple filter types (include/exclude patterns)

### Size Limiting
- Always limit the size of returned data
- Implement streaming for large datasets
- Use pagination for large result sets
- Provide progress indicators for long operations

### Field Selection
- Allow selection of specific fields to return
- Implement default field sets for common operations
- Use projection to limit returned data
- Provide options for detailed vs. summary output

## Security Patterns

### Input Sanitization
```bash
sanitize_input() {
    local input="$1"

    # Remove dangerous characters
    input=$(echo "$input" | sed 's/[;&|$`]/_/g')

    # Validate against allowlist if possible
    if [[ ! "$input" =~ ^[a-zA-Z0-9/_.-]+$ ]]; then
        echo "ERROR: Invalid characters in input"
        exit 1
    fi

    echo "$input"
}
```

### Command Whitelisting
```bash
is_safe_command() {
    local command="$1"
    local safe_commands=("ls" "cat" "grep" "find" "head" "tail" "wc" "sort" "uniq")

    for safe_cmd in "${safe_commands[@]}"; do
        if [[ "$command" == "$safe_cmd"* ]]; then
            return 0
        fi
    done

    return 1
}
```

## Testing Strategies

### Unit Testing
- Test individual functions with various input types
- Test error conditions and edge cases
- Validate output filtering behavior
- Test timeout and resource limit enforcement

### Integration Testing
- Test complete workflow with actual MCP server
- Validate result filtering effectiveness
- Test security constraint enforcement
- Verify performance under load

### Security Testing
- Test input validation with malicious inputs
- Verify command safety mechanisms
- Test access control implementations
- Validate output sanitization

## Monitoring and Observability

### Logging
- Log all operations with appropriate detail levels
- Include operation timing and resource usage
- Log security violations and near-misses
- Maintain audit trails for compliance

### Metrics
- Track operation success/failure rates
- Monitor performance metrics (latency, throughput)
- Track resource usage patterns
- Monitor security-related metrics

## Common Anti-Patterns to Avoid

1. **Direct MCP Tool Loading**: Never load MCP tools directly into agent context
2. **Unfiltered Results**: Always filter results to minimal essential information
3. **Unsafe Command Execution**: Never execute unsanitized commands
4. **Insufficient Validation**: Always validate inputs and outputs
5. **Overly Verbose Output**: Keep output minimal and focused
6. **Missing Error Handling**: Always implement proper error handling
7. **Resource Leaks**: Always clean up temporary resources
8. **Hardcoded Values**: Use configuration for all tunable parameters

## Implementation Checklist

### Before Deployment
- [ ] Input validation implemented for all parameters
- [ ] Command sanitization in place for all executions
- [ ] Result filtering applied to all outputs
- [ ] Proper error handling implemented
- [ ] Resource cleanup implemented
- [ ] Security constraints enforced
- [ ] Performance limits set appropriately

### For Each Operation
- [ ] Validate all inputs
- [ ] Sanitize command execution
- [ ] Filter output to minimal results
- [ ] Handle errors gracefully
- [ ] Clean up resources
- [ ] Log operation for audit trail
- [ ] Return appropriate exit codes

Following these best practices ensures that MCP wrapper scripts are secure, efficient, and maintainable while enforcing the required constraints.