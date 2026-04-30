import pytest
from unittest.mock import Mock, patch
from scripts.customer_success_agent import CustomerSuccessAgent, CustomerState, StateManager

def test_customer_state_initialization():
    """Test that CustomerState initializes correctly."""
    state = CustomerState("test_customer_123")

    assert state.customer_id == "test_customer_123"
    assert state.profile["name"] == ""
    assert state.profile["email"] == ""
    assert state.profile["loyalty_tier"] == "basic"
    assert len(state.history["messages"]) == 0

def test_customer_state_add_message():
    """Test adding messages to customer state."""
    state = CustomerState("test_customer_123")

    state.add_message("user", "Hello, I need help.")

    assert len(state.history["messages"]) == 1
    assert state.history["messages"][0]["role"] == "user"
    assert state.history["messages"][0]["content"] == "Hello, I need help."

def test_state_manager_get_state():
    """Test that StateManager creates new states when needed."""
    state_manager = StateManager()

    # Get a state that doesn't exist yet
    state = state_manager.get_state("new_customer_123")

    assert state.customer_id == "new_customer_123"
    assert isinstance(state, CustomerState)

def test_state_serialization():
    """Test that state can be serialized and deserialized."""
    original_state = CustomerState("test_customer_456")
    original_state.update_profile({"name": "John Doe", "email": "john@example.com"})

    # Serialize
    serialized = original_state.to_dict()

    # Deserialize
    deserialized_state = CustomerState.from_dict(serialized)

    assert deserialized_state.customer_id == original_state.customer_id
    assert deserialized_state.profile["name"] == "John Doe"
    assert deserialized_state.profile["email"] == "john@example.com"

@patch('openai.OpenAI')
def test_agent_initialization(mock_openai):
    """Test that the agent initializes correctly."""
    mock_client = Mock()
    mock_openai.return_value = mock_client

    agent = CustomerSuccessAgent(api_key="test-key")

    assert agent.client == mock_client
    assert agent.model == "gpt-4-turbo"
    assert len(agent.tool_registry.tools) > 0  # Should have registered tools

def test_intent_classification():
    """Test that the conversation flow can classify intents."""
    from scripts.customer_success_agent import ConversationFlow

    flow = ConversationFlow()

    # Test search intent
    intent, confidence = flow.classify_intent("I need help finding information")
    assert intent == "search"
    assert confidence > 0.5

    # Test ticket creation intent
    intent, confidence = flow.classify_intent("I want to create a support ticket")
    assert intent == "create_ticket"
    assert confidence > 0.5

    # Test greeting intent
    intent, confidence = flow.classify_intent("Hello there")
    assert intent == "greeting"
    assert confidence > 0.5

    # Test unknown intent
    intent, confidence = flow.classify_intent("kjlasdnflkjandsf")
    assert intent == "unknown"
    assert confidence <= 0.5

if __name__ == "__main__":
    pytest.main([__file__])