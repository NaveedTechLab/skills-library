---
name: agent_workflow
description: Implements the core Customer Success Agent using OpenAI Agents SDK. Manages the orchestration of tool calls (search, ticket creation, etc.), conversation logic, and state management. Use when Claude needs to create or modify Customer Success Agent implementations with OpenAI Agents SDK, orchestrate multiple tools, manage conversation flows, or handle persistent state across interactions.
---

# Customer Success Agent Workflow Skill

This skill provides guidance for implementing the core Customer Success Agent using OpenAI Agents SDK, focusing on orchestration of tool calls, conversation logic, and state management.

## Overview

The Customer Success Agent is responsible for:
- Interacting with customers to resolve issues and answer questions
- Orchestrating multiple tools (search, ticket creation, knowledge base, etc.)
- Maintaining conversation context and state across interactions
- Managing customer data and preferences

## Key Components

### 1. Agent Architecture

The Customer Success Agent follows this architecture:

```python
from openai import OpenAI
from typing import Dict, Any, List
import json

class CustomerSuccessAgent:
    def __init__(self, api_key: str, model: str = "gpt-4-turbo"):
        self.client = OpenAI(api_key=api_key)
        self.model = model
        self.conversation_history = []
        self.state_manager = StateManager()

    def process_message(self, user_input: str, customer_id: str) -> str:
        # Process user input and return response
        pass
```

### 2. Tool Orchestration

The agent orchestrates multiple tools to serve customer needs:
- Search tools for finding relevant information
- Ticket management tools for creating and updating tickets
- Knowledge base tools for accessing documentation
- Customer data tools for retrieving user information
- Notification tools for sending updates

### 3. Conversation Logic

Implement conversation flow management:
- Intent recognition and classification
- Context switching between topics
- Handling of follow-up questions
- Multi-turn dialogue management
- Escalation to human agents when needed

### 4. State Management

Maintain state across conversations:
- Customer profile and preferences
- Current conversation context
- Active tickets and issues
- Previous recommendations and resolutions

## Implementation Guidelines

### Tool Definition and Registration

Define tools with clear schemas:

```python
def search_knowledge_base(query: str, category: str = None) -> List[Dict]:
    """
    Search the knowledge base for relevant articles.

    Args:
        query: Search query
        category: Category to filter by (optional)

    Returns:
        List of relevant articles
    """
    # Implementation here
    pass

def create_customer_ticket(
    customer_id: str,
    subject: str,
    description: str,
    priority: str = "medium"
) -> Dict:
    """
    Create a support ticket for the customer.

    Args:
        customer_id: Unique customer identifier
        subject: Ticket subject
        description: Detailed description
        priority: Priority level

    Returns:
        Created ticket information
    """
    # Implementation here
    pass
```

### State Management Patterns

Use a state manager to persist conversation context:

```python
class StateManager:
    def __init__(self):
        self.customer_states = {}

    def get_state(self, customer_id: str) -> Dict[str, Any]:
        """Retrieve customer state"""
        return self.customer_states.get(customer_id, {})

    def update_state(self, customer_id: str, updates: Dict[str, Any]):
        """Update customer state with new information"""
        if customer_id not in self.customer_states:
            self.customer_states[customer_id] = {}
        self.customer_states[customer_id].update(updates)

    def clear_state(self, customer_id: str):
        """Clear customer state when conversation ends"""
        if customer_id in self.customer_states:
            del self.customer_states[customer_id]
```

### Conversation Flow Control

Implement conversation logic to manage complex interactions:

```python
class ConversationFlow:
    def __init__(self):
        self.active_intents = {}

    def classify_intent(self, user_input: str) -> str:
        """Classify the user's intent"""
        # Implementation using NLP or rule-based classification
        pass

    def handle_intent(self, intent: str, params: Dict) -> str:
        """Handle specific intent with parameters"""
        # Implementation for each intent type
        pass
```

## Best Practices

### Error Handling

- Implement graceful fallbacks when tools fail
- Log errors for debugging and monitoring
- Provide informative error messages to users
- Maintain conversation state even during errors

### Security Considerations

- Validate and sanitize all inputs
- Implement proper authentication and authorization
- Protect customer data privacy
- Audit tool usage and access

### Performance Optimization

- Cache frequently accessed data
- Optimize tool calls to reduce latency
- Implement rate limiting for external services
- Monitor agent response times

## Reference Files

For detailed implementation patterns, see:
- [AGENT_ARCHITECTURE.md](references/AGENT_ARCHITECTURE.md) - Detailed agent architecture patterns
- [TOOL_ORCHESTRATION.md](references/TOOL_ORCHESTRATION.md) - Tool definition and orchestration patterns
- [CONVERSATION_FLOW.md](references/CONVERSATION_FLOW.md) - Conversation logic implementation
- [STATE_MANAGEMENT.md](references/STATE_MANAGEMENT.md) - State persistence strategies
- [ERROR_HANDLING.md](references/ERROR_HANDLING.md) - Error handling and recovery patterns
- [SECURITY_PATTERNS.md](references/SECURITY_PATTERNS.md) - Security implementation guidelines