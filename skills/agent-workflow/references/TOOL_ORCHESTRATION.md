# Tool Orchestration Reference

## Tool Definition Schema

When defining tools for the Customer Success Agent, follow this schema structure:

```json
{
  "type": "function",
  "function": {
    "name": "search_knowledge_base",
    "description": "Search the knowledge base for relevant articles",
    "parameters": {
      "type": "object",
      "properties": {
        "query": {
          "type": "string",
          "description": "Search query to find relevant articles"
        },
        "category": {
          "type": "string",
          "description": "Category to filter articles by (optional)"
        },
        "max_results": {
          "type": "integer",
          "description": "Maximum number of results to return (default: 5)",
          "default": 5
        }
      },
      "required": ["query"]
    }
  }
}
```

## Tool Registration Process

### 1. Define the Tool Function

Create the actual function that will be called:

```python
def search_knowledge_base(query: str, category: str = None, max_results: int = 5) -> List[Dict]:
    """
    Search the knowledge base for relevant articles.

    Args:
        query: Search query to find relevant articles
        category: Category to filter articles by (optional)
        max_results: Maximum number of results to return (default: 5)

    Returns:
        List of relevant articles with title, content, and relevance score
    """
    # Implementation here
    pass
```

### 2. Register the Tool

Register the tool with the agent's tool registry:

```python
# Define the tool schema
search_tool_schema = {
    "type": "function",
    "function": {
        "name": "search_knowledge_base",
        "description": "Search the knowledge base for relevant articles",
        "parameters": {
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "Search query to find relevant articles"
                },
                "category": {
                    "type": "string",
                    "description": "Category to filter articles by (optional)"
                },
                "max_results": {
                    "type": "integer",
                    "description": "Maximum number of results to return (default: 5)",
                    "default": 5
                }
            },
            "required": ["query"]
        }
    }
}

# Register the tool
tool_registry.register_tool("search_knowledge_base", search_knowledge_base, search_tool_schema)
```

## Common Tool Categories

### 1. Search Tools

Tools for finding information in knowledge bases, documentation, or databases:

```python
def search_tickets(customer_id: str, status: str = None, limit: int = 10) -> List[Dict]:
    """Search for tickets belonging to a customer."""
    pass

def search_products(query: str, category: str = None) -> List[Dict]:
    """Search for products based on query and category."""
    pass
```

### 2. Data Management Tools

Tools for creating, updating, or retrieving customer data:

```python
def create_ticket(
    customer_id: str,
    subject: str,
    description: str,
    priority: str = "medium",
    category: str = "general"
) -> Dict:
    """Create a support ticket for a customer."""
    pass

def update_customer_profile(
    customer_id: str,
    updates: Dict[str, Any]
) -> Dict:
    """Update customer profile information."""
    pass
```

### 3. Communication Tools

Tools for sending notifications or communicating with customers:

```python
def send_notification(
    customer_id: str,
    message: str,
    method: str = "email"
) -> Dict:
    """Send a notification to the customer."""
    pass

def escalate_to_human(
    customer_id: str,
    reason: str,
    urgency: str = "medium"
) -> Dict:
    """Escalate the conversation to a human agent."""
    pass
```

## Tool Execution Pipeline

### 1. Tool Selection

The agent selects tools based on the user's request:

```python
def select_tools(user_input: str, available_tools: List[Dict]) -> List[str]:
    """Select the most appropriate tools for the user's request."""
    # Implementation using semantic matching or LLM-based selection
    pass
```

### 2. Tool Calling

Execute the selected tools with proper error handling:

```python
def execute_tool_call(tool_name: str, arguments: Dict[str, Any]) -> Dict[str, Any]:
    """Execute a tool call with error handling and validation."""
    try:
        # Validate arguments
        validated_args = validate_arguments(tool_name, arguments)

        # Execute the tool
        result = tool_registry.call_tool(tool_name, **validated_args)

        return {
            "status": "success",
            "result": result
        }
    except ValidationError as e:
        return {
            "status": "error",
            "error": f"Invalid arguments: {str(e)}"
        }
    except Exception as e:
        return {
            "status": "error",
            "error": f"Tool execution failed: {str(e)}"
        }
```

### 3. Result Processing

Process tool results and format them for the LLM:

```python
def format_tool_results(results: List[Dict]) -> str:
    """Format tool results for the LLM to understand."""
    formatted_results = []

    for result in results:
        if result["status"] == "success":
            formatted_results.append(f"Tool '{result['tool_name']}' succeeded: {result['result']}")
        else:
            formatted_results.append(f"Tool '{result['tool_name']}' failed: {result['error']}")

    return "\n".join(formatted_results)
```

## Parallel Tool Execution

Execute multiple tools concurrently when possible:

```python
import asyncio
from typing import List, Dict, Any

async def execute_parallel_tools(tool_calls: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Execute multiple tool calls in parallel."""

    async def execute_single_call(call: Dict[str, Any]) -> Dict[str, Any]:
        return execute_tool_call(call["name"], call["arguments"])

    tasks = [execute_single_call(call) for call in tool_calls]
    results = await asyncio.gather(*tasks, return_exceptions=True)

    return results
```

## Tool Result Validation

Validate tool results before returning to the LLM:

```python
def validate_tool_result(tool_name: str, result: Any) -> bool:
    """Validate that the tool result matches expected format."""
    expected_format = get_expected_format(tool_name)

    # Check if result matches expected format
    return matches_format(result, expected_format)

def sanitize_tool_result(tool_name: str, result: Any) -> Any:
    """Sanitize tool results to remove sensitive information."""
    # Remove sensitive fields based on tool type
    if tool_name.startswith("customer_"):
        if isinstance(result, dict):
            # Remove sensitive customer data
            sensitive_fields = ["ssn", "credit_card", "password"]
            sanitized = result.copy()
            for field in sensitive_fields:
                sanitized.pop(field, None)
            return sanitized

    return result
```

## Error Handling and Fallbacks

Implement graceful degradation when tools fail:

```python
def handle_tool_failure(tool_name: str, error: str) -> str:
    """Handle tool failure and provide alternative response."""

    # Log the error
    logger.error(f"Tool {tool_name} failed: {error}")

    # Provide fallback response based on tool type
    if tool_name.startswith("search_"):
        return "I'm having trouble searching our knowledge base right now. Could you try rephrasing your question?"
    elif tool_name.startswith("create_") or tool_name.startswith("update_"):
        return "I'm experiencing issues updating your information. Please try again in a moment or contact support directly."
    else:
        return f"I'm having trouble with {tool_name}. Is there something else I can help you with?"
```