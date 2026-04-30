#!/usr/bin/env python3
"""
Customer Success Agent Implementation
Implements the core Customer Success Agent using OpenAI Agents SDK.
Manages orchestration of tool calls, conversation logic, and state management.
"""

import asyncio
import logging
import json
from datetime import datetime
from typing import Dict, Any, List, Optional, Tuple
from enum import Enum

from openai import OpenAI
from pydantic import BaseModel

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Import required libraries
try:
    import redis
    REDIS_AVAILABLE = True
except ImportError:
    REDIS_AVAILABLE = False

# Models
class ErrorType(Enum):
    INVALID_INPUT = "invalid_input"
    AUTHENTICATION_FAILED = "authentication_failed"
    PERMISSION_DENIED = "permission_denied"
    VALIDATION_ERROR = "validation_error"
    INTERNAL_ERROR = "internal_error"
    TOOL_EXECUTION_FAILED = "tool_execution_failed"

class ErrorContext:
    def __init__(self, error_type: ErrorType, message: str, customer_id: str = None):
        self.error_type = error_type
        self.message = message
        self.customer_id = customer_id
        self.timestamp = datetime.now()

# State Management
class CustomerState:
    def __init__(self, customer_id: str):
        self.customer_id = customer_id
        self.created_at = datetime.now()
        self.updated_at = datetime.now()

        # Customer profile information
        self.profile = {
            "name": "",
            "email": "",
            "phone": "",
            "company": "",
            "preferences": {},
            "loyalty_tier": "basic"
        }

        # Active conversation context
        self.conversation_context = {
            "current_topic": None,
            "intents": [],
            "entities": {},
            "last_interaction": None
        }

        # Active tickets and issues
        self.active_items = {
            "tickets": [],
            "orders": [],
            "appointments": []
        }

        # Conversation history
        self.history = {
            "messages": [],
            "sessions": [],
            "resolution_attempts": []
        }

        # Temporary state for multi-turn conversations
        self.temp_state = {}

    def update_profile(self, updates: Dict[str, Any]):
        """Update customer profile information."""
        self.profile.update(updates)
        self.updated_at = datetime.now()

    def add_message(self, role: str, content: str, timestamp: datetime = None):
        """Add a message to the conversation history."""
        if timestamp is None:
            timestamp = datetime.now()

        message = {
            "role": role,
            "content": content,
            "timestamp": timestamp.isoformat()
        }
        self.history["messages"].append(message)
        self.updated_at = datetime.now()

    def set_temp_state(self, key: str, value: Any):
        """Set temporary state for multi-turn conversations."""
        self.temp_state[key] = value

    def get_temp_state(self, key: str, default: Any = None):
        """Get temporary state value."""
        return self.temp_state.get(key, default)

    def clear_temp_state(self):
        """Clear all temporary state."""
        self.temp_state.clear()

    def to_dict(self) -> Dict[str, Any]:
        """Convert state to dictionary for serialization."""
        return {
            "customer_id": self.customer_id,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
            "profile": self.profile,
            "conversation_context": self.conversation_context,
            "active_items": self.active_items,
            "history": self.history,
            "temp_state": self.temp_state
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'CustomerState':
        """Create CustomerState from dictionary."""
        state = cls(data["customer_id"])
        state.created_at = datetime.fromisoformat(data["created_at"])
        state.updated_at = datetime.fromisoformat(data["updated_at"])
        state.profile = data["profile"]
        state.conversation_context = data["conversation_context"]
        state.active_items = data["active_items"]
        state.history = data["history"]
        state.temp_state = data.get("temp_state", {})
        return state

# State Manager
class StateManager:
    def __init__(self):
        self._states = {}
        self.redis_client = None

        if REDIS_AVAILABLE:
            try:
                self.redis_client = redis.Redis(host='localhost', port=6379, decode_responses=True)
            except:
                logger.warning("Could not connect to Redis, using in-memory storage")

    def get_state(self, customer_id: str) -> CustomerState:
        """Get customer state, creating if it doesn't exist."""
        # Try to load from Redis first
        if self.redis_client:
            try:
                serialized_state = self.redis_client.get(f"customer_state:{customer_id}")
                if serialized_state:
                    data = json.loads(serialized_state)
                    return CustomerState.from_dict(data)
            except Exception as e:
                logger.error(f"Redis error: {e}")

        # Fall back to in-memory storage
        if customer_id not in self._states:
            self._states[customer_id] = CustomerState(customer_id)

        return self._states[customer_id]

    def save_state(self, state: CustomerState):
        """Save customer state."""
        # Save to Redis if available
        if self.redis_client:
            try:
                serialized_state = json.dumps(state.to_dict())
                self.redis_client.setex(f"customer_state:{state.customer_id}", 3600, serialized_state)
            except Exception as e:
                logger.error(f"Redis save error: {e}")

        # Save to in-memory storage
        self._states[state.customer_id] = state

# Tool Registry
class ToolRegistry:
    def __init__(self):
        self.tools = {}
        self.tool_schemas = {}

    def register_tool(self, name: str, func, schema: Dict):
        """Register a new tool with its function and schema."""
        self.tools[name] = func
        self.tool_schemas[name] = schema

    def get_tool_schema(self, name: str) -> Dict:
        """Get the schema for a registered tool."""
        return self.tool_schemas.get(name)

    def call_tool(self, name: str, **kwargs) -> Any:
        """Execute a registered tool with provided arguments."""
        if name not in self.tools:
            raise ValueError(f"Tool {name} not found")

        try:
            return self.tools[name](**kwargs)
        except Exception as e:
            raise RuntimeError(f"Error calling tool {name}: {str(e)}")

# Mock tool implementations
def search_knowledge_base(query: str, category: str = None, max_results: int = 5) -> List[Dict]:
    """Mock search tool for knowledge base."""
    logger.info(f"Searching knowledge base for: {query}")

    # Mock results
    results = [
        {
            "title": "How to Reset Your Password",
            "content": "To reset your password, go to Settings > Account > Reset Password",
            "relevance_score": 0.9
        },
        {
            "title": "Troubleshooting Login Issues",
            "content": "If you're having trouble logging in, try clearing your browser cache",
            "relevance_score": 0.8
        }
    ]

    return results[:max_results]

def create_ticket(
    customer_id: str,
    subject: str,
    description: str,
    priority: str = "medium",
    category: str = "general"
) -> Dict:
    """Mock tool to create a support ticket."""
    logger.info(f"Creating ticket for customer {customer_id}: {subject}")

    # Mock ticket creation
    import random
    ticket_id = f"T-{random.randint(10000, 99999)}"

    return {
        "ticket_id": ticket_id,
        "status": "created",
        "subject": subject,
        "description": description,
        "priority": priority,
        "category": category,
        "created_at": datetime.now().isoformat()
    }

def get_customer_info(customer_id: str) -> Dict:
    """Mock tool to retrieve customer information."""
    logger.info(f"Retrieving customer info for: {customer_id}")

    # Mock customer data
    return {
        "customer_id": customer_id,
        "name": "John Doe",
        "email": "john.doe@example.com",
        "company": "Example Corp",
        "loyalty_tier": "premium",
        "join_date": "2023-01-15",
        "last_interaction": "2023-10-15"
    }

def send_notification(customer_id: str, message: str, method: str = "email") -> Dict:
    """Mock tool to send notifications."""
    logger.info(f"Sending {method} notification to customer {customer_id}")

    return {
        "status": "sent",
        "method": method,
        "recipient": customer_id,
        "message_preview": message[:50] + "..." if len(message) > 50 else message
    }

# Conversation Flow Management
class ConversationFlow:
    def __init__(self):
        self.active_intents = {}
        self.pending_requests = {}

    def classify_intent(self, user_input: str) -> Tuple[str, float]:
        """Simple intent classification."""
        user_lower = user_input.lower()

        if any(word in user_lower for word in ["search", "find", "help", "know", "article", "guide"]):
            return "search", 0.8
        elif any(word in user_lower for word in ["ticket", "issue", "problem", "bug", "support", "create"]):
            return "create_ticket", 0.8
        elif any(word in user_lower for word in ["profile", "account", "info", "update", "change"]):
            return "account_info", 0.8
        elif any(word in user_lower for word in ["hello", "hi", "hey", "greet"]):
            return "greeting", 0.9
        else:
            return "unknown", 0.1

    def start_request(self, customer_id: str, request_type: str, params: Dict = None):
        """Start a multi-turn request."""
        self.pending_requests[customer_id] = {
            "type": request_type,
            "params": params or {},
            "step": 0,
            "timestamp": datetime.now(),
            "context": {}
        }

    def continue_request(self, customer_id: str, user_input: str) -> Tuple[str, bool]:
        """Continue a multi-turn request."""
        if customer_id not in self.pending_requests:
            return "", False

        request = self.pending_requests[customer_id]

        # Check if request has timed out
        if (datetime.now() - request["timestamp"]).seconds > 300:  # 5 minutes
            del self.pending_requests[customer_id]
            return "Your request has timed out. Please start over.", False

        # Handle ticket creation steps
        if request["type"] == "create_ticket":
            return self._handle_ticket_creation_step(customer_id, user_input, request)

        return "", False

    def _handle_ticket_creation_step(self, customer_id: str, user_input: str, request: Dict):
        """Handle ticket creation steps."""
        steps = ["subject", "description", "priority", "submit"]

        if request["step"] == 0:  # Ask for subject
            request["params"]["subject"] = user_input
            request["step"] += 1
            return "Thanks. Please provide a detailed description of the issue:", False

        elif request["step"] == 1:  # Ask for description
            request["params"]["description"] = user_input
            request["step"] += 1
            return "What priority level should this ticket have? (low, medium, high, urgent):", False

        elif request["step"] == 2:  # Ask for priority
            priority = user_input.lower().strip()
            if priority in ["low", "medium", "high", "urgent"]:
                request["params"]["priority"] = priority
                request["step"] += 1

                # Submit the ticket
                try:
                    result = create_ticket(customer_id, **request["params"])
                    if customer_id in self.pending_requests:
                        del self.pending_requests[customer_id]
                    return f"Your ticket has been created successfully with ID: {result['ticket_id']}", True
                except Exception as e:
                    if customer_id in self.pending_requests:
                        del self.pending_requests[customer_id]
                    return f"Sorry, I couldn't create your ticket: {str(e)}", True
            else:
                return "Please specify a priority level: low, medium, high, or urgent:", False

    def complete_request(self, customer_id: str):
        """Complete and clean up a multi-turn request."""
        if customer_id in self.pending_requests:
            del self.pending_requests[customer_id]

# Main Customer Success Agent
class CustomerSuccessAgent:
    def __init__(self, api_key: str, model: str = "gpt-4-turbo"):
        self.client = OpenAI(api_key=api_key)
        self.model = model
        self.logger = logging.getLogger(__name__)
        self.state_manager = StateManager()
        self.conversation_flow = ConversationFlow()
        self.tool_registry = ToolRegistry()

        # Register tools
        self._register_default_tools()

    def _register_default_tools(self):
        """Register default tools for the agent."""
        # Search tool schema
        search_schema = {
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

        # Create ticket schema
        ticket_schema = {
            "type": "function",
            "function": {
                "name": "create_ticket",
                "description": "Create a support ticket for the customer",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "customer_id": {
                            "type": "string",
                            "description": "Unique customer identifier"
                        },
                        "subject": {
                            "type": "string",
                            "description": "Ticket subject"
                        },
                        "description": {
                            "type": "string",
                            "description": "Detailed description of the issue"
                        },
                        "priority": {
                            "type": "string",
                            "description": "Priority level (low, medium, high, urgent)",
                            "default": "medium"
                        },
                        "category": {
                            "type": "string",
                            "description": "Ticket category (general, technical, billing)",
                            "default": "general"
                        }
                    },
                    "required": ["customer_id", "subject", "description"]
                }
            }
        }

        # Register tools
        self.tool_registry.register_tool("search_knowledge_base", search_knowledge_base, search_schema)
        self.tool_registry.register_tool("create_ticket", create_ticket, ticket_schema)
        self.tool_registry.register_tool("get_customer_info", get_customer_info, {
            "type": "function",
            "function": {
                "name": "get_customer_info",
                "description": "Get customer information",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "customer_id": {
                            "type": "string",
                            "description": "Unique customer identifier"
                        }
                    },
                    "required": ["customer_id"]
                }
            }
        })
        self.tool_registry.register_tool("send_notification", send_notification, {
            "type": "function",
            "function": {
                "name": "send_notification",
                "description": "Send a notification to the customer",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "customer_id": {
                            "type": "string",
                            "description": "Unique customer identifier"
                        },
                        "message": {
                            "type": "string",
                            "description": "Message to send to the customer"
                        },
                        "method": {
                            "type": "string",
                            "description": "Method of notification (email, sms)",
                            "default": "email"
                        }
                    },
                    "required": ["customer_id", "message"]
                }
            }
        })

    def chat(self, message: str, customer_id: str) -> str:
        """Main method for processing customer messages."""
        try:
            # Retrieve customer state
            state = self.state_manager.get_state(customer_id)

            # Add user message to conversation history
            state.add_message("user", message)

            # Check for pending multi-turn requests
            if customer_id in self.conversation_flow.pending_requests:
                response, is_complete = self.conversation_flow.continue_request(customer_id, message)

                if is_complete:
                    # Add assistant message to conversation history
                    state.add_message("assistant", response)
                    self.state_manager.save_state(state)
                    return response
                elif response:
                    # Add assistant message to conversation history
                    state.add_message("assistant", response)
                    self.state_manager.save_state(state)
                    return response

            # Classify intent
            intent, confidence = self.conversation_flow.classify_intent(message)

            # Handle different intents
            if intent == "create_ticket" and confidence > 0.5:
                # Start multi-turn ticket creation
                self.conversation_flow.start_request(customer_id, "create_ticket", {"customer_id": customer_id})
                response = "I can help you create a support ticket. What is the subject of your ticket?"
            elif intent == "search" and confidence > 0.5:
                # Call search tool
                search_results = search_knowledge_base(query=message)
                response = f"I found {len(search_results)} relevant articles:\n"
                for i, article in enumerate(search_results, 1):
                    response += f"{i}. {article['title']}\n   {article['content'][:100]}...\n\n"
            elif intent == "greeting" and confidence > 0.5:
                # Get customer info for personalized greeting
                customer_info = get_customer_info(customer_id)
                response = f"Hello {customer_info.get('name', 'there')}! How can I help you today?"
            else:
                # Use OpenAI to generate response with tools
                tools = [self.tool_registry.get_tool_schema(name) for name in self.tool_registry.tools.keys()]

                response_obj = self.client.chat.completions.create(
                    model=self.model,
                    messages=[
                        {"role": "system", "content": self._get_system_prompt()},
                        {"role": "user", "content": message}
                    ],
                    tools=tools,
                    tool_choice="auto"
                )

                # Process tool calls if any
                if response_obj.choices[0].finish_reason == "tool_calls":
                    tool_calls = response_obj.choices[0].message.tool_calls

                    if tool_calls:
                        # Execute tool calls
                        tool_results = []
                        for tool_call in tool_calls:
                            function_name = tool_call.function.name
                            arguments = json.loads(tool_call.function.arguments)

                            try:
                                result = self.tool_registry.call_tool(function_name, **arguments)
                                tool_results.append({
                                    "tool_call_id": tool_call.id,
                                    "result": result
                                })
                            except Exception as e:
                                tool_results.append({
                                    "tool_call_id": tool_call.id,
                                    "error": str(e)
                                })

                        # Generate final response based on tool results
                        tool_results_str = "\n".join([
                            f"Result: {res['result']}" if 'result' in res else f"Error: {res['error']}"
                            for res in tool_results
                        ])

                        final_response = self.client.chat.completions.create(
                            model=self.model,
                            messages=[
                                {"role": "system", "content": self._get_system_prompt()},
                                {"role": "user", "content": message},
                                {"role": "assistant", "content": f"Tool results: {tool_results_str}"}
                            ]
                        )
                        response = final_response.choices[0].message.content
                    else:
                        response = response_obj.choices[0].message.content
                else:
                    response = response_obj.choices[0].message.content or "I'm not sure how to help with that."

            # Add assistant message to conversation history
            state.add_message("assistant", response)

            # Save updated state
            self.state_manager.save_state(state)

            return response

        except Exception as e:
            self.logger.error(f"Agent error: {str(e)}", exc_info=True)
            return "I apologize, but I'm experiencing technical difficulties. Please try again later."

    def _get_system_prompt(self) -> str:
        """Get the system prompt for the agent."""
        return """
        You are a helpful Customer Success Agent. Your role is to assist customers with their inquiries,
        help them find information, create support tickets, and provide a positive experience.
        Always be polite, professional, and aim to resolve customer issues efficiently.
        """

# Health check
def health_check():
    """Basic health check for the agent."""
    return {
        "status": "healthy",
        "components": {
            "agent": "running",
            "tools": list(ToolRegistry().tools.keys()) if 'ToolRegistry' in globals() else [],
            "state_management": "available" if REDIS_AVAILABLE else "using_in_memory"
        }
    }

if __name__ == "__main__":
    import os

    # Example usage
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        logger.error("OPENAI_API_KEY environment variable not set")
        exit(1)

    agent = CustomerSuccessAgent(api_key=api_key)

    # Example conversation
    customer_id = "cust_12345"

    print("Customer Success Agent Demo")
    print("=" * 40)

    # Simulate a conversation
    messages = [
        "Hello, I need help with resetting my password",
        "Can you help me create a ticket about login issues?",
        "My login isn't working and I need urgent help"
    ]

    for i, msg in enumerate(messages):
        print(f"\nCustomer ({i+1}): {msg}")
        response = agent.chat(msg, customer_id)
        print(f"Agent: {response}")