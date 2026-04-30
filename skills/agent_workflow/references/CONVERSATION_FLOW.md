# Conversation Flow Reference

## Intent Classification

### Intent Recognition

Implement intent recognition to understand customer requests:

```python
from typing import Dict, List, Tuple
import re

class IntentClassifier:
    def __init__(self):
        self.intents = {
            "search_product": {
                "keywords": ["product", "item", "buy", "purchase", "find", "look for"],
                "patterns": [r"what.*product", r"looking.*for.*product", r"need.*buy"],
                "confidence_boost": ["buy", "purchase", "order"]
            },
            "support_ticket": {
                "keywords": ["ticket", "issue", "problem", "bug", "trouble", "help"],
                "patterns": [r"having.*problem", r"issue.*with", r"can't.*work"],
                "confidence_boost": ["urgent", "critical", "immediately"]
            },
            "account_info": {
                "keywords": ["account", "profile", "settings", "information", "update"],
                "patterns": [r"my.*account", r"change.*password", r"update.*info"],
                "confidence_boost": ["urgent", "immediately", "right now"]
            }
        }

    def classify_intent(self, text: str) -> Tuple[str, float]:
        """Classify the intent of the user's input with confidence score."""
        text_lower = text.lower()
        scores = {}

        for intent_name, intent_config in self.intents.items():
            score = 0

            # Score based on keywords
            for keyword in intent_config["keywords"]:
                if keyword in text_lower:
                    score += 1

            # Score based on patterns
            for pattern in intent_config["patterns"]:
                if re.search(pattern, text_lower):
                    score += 2  # Higher weight for patterns

            # Boost score for confidence keywords
            for boost_word in intent_config.get("confidence_boost", []):
                if boost_word in text_lower:
                    score *= 1.5

            scores[intent_name] = score

        # Return intent with highest score and normalized confidence
        if not scores:
            return "unknown", 0.0

        best_intent = max(scores, key=scores.get)
        max_score = scores[best_intent]

        # Normalize confidence to 0-1 range (assuming max possible score is around 10)
        confidence = min(max_score / 10.0, 1.0)

        return best_intent, confidence
```

### Context Switching

Handle transitions between different conversation topics:

```python
class ConversationContext:
    def __init__(self):
        self.current_topic = None
        self.topic_stack = []
        self.context_memory = {}

    def switch_topic(self, new_topic: str):
        """Switch to a new topic, preserving previous context."""
        if self.current_topic:
            self.topic_stack.append(self.current_topic)

        self.current_topic = new_topic
        self.context_memory[new_topic] = {
            "started_at": time.time(),
            "turns_count": 0
        }

    def return_to_previous_topic(self):
        """Return to the previous topic if available."""
        if self.topic_stack:
            self.current_topic = self.topic_stack.pop()
            self.context_memory[self.current_topic]["returned_at"] = time.time()

    def update_context(self, key: str, value: Any):
        """Update the current context with new information."""
        if self.current_topic:
            if self.current_topic not in self.context_memory:
                self.context_memory[self.current_topic] = {}
            self.context_memory[self.current_topic][key] = value
```

## Dialogue Management

### Multi-turn Conversations

Manage complex multi-turn conversations:

```python
class MultiTurnDialogue:
    def __init__(self):
        self.pending_requests = {}  # customer_id -> request_state
        self.request_timeout = 300  # 5 minutes

    def start_request(self, customer_id: str, request_type: str, params: Dict = None):
        """Start a multi-turn request."""
        self.pending_requests[customer_id] = {
            "type": request_type,
            "params": params or {},
            "step": 0,
            "timestamp": time.time(),
            "context": {}
        }

    def continue_request(self, customer_id: str, user_input: str) -> Tuple[str, bool]:
        """Continue a multi-turn request based on user input."""
        if customer_id not in self.pending_requests:
            return "", False

        request = self.pending_requests[customer_id]

        # Check if request has timed out
        if time.time() - request["timestamp"] > self.request_timeout:
            del self.pending_requests[customer_id]
            return "Your request has timed out. Please start over.", False

        # Process the next step based on request type
        if request["type"] == "create_ticket":
            return self._handle_ticket_creation_step(customer_id, user_input, request)
        elif request["type"] == "update_profile":
            return self._handle_profile_update_step(customer_id, user_input, request)

        return "", False

    def complete_request(self, customer_id: str):
        """Complete and clean up a multi-turn request."""
        if customer_id in self.pending_requests:
            del self.pending_requests[customer_id]

    def _handle_ticket_creation_step(self, customer_id: str, user_input: str, request: Dict):
        """Handle ticket creation steps."""
        steps = [
            "subject",  # Ask for ticket subject
            "description",  # Ask for detailed description
            "priority",  # Ask for priority level
            "submit"  # Submit the ticket
        ]

        current_step = steps[request["step"]]

        if current_step == "subject":
            request["params"]["subject"] = user_input
            request["step"] += 1
            return "Thanks. Please provide a detailed description of the issue:", False

        elif current_step == "description":
            request["params"]["description"] = user_input
            request["step"] += 1
            return "What priority level should this ticket have? (low, medium, high, urgent):", False

        elif current_step == "priority":
            priority = user_input.lower().strip()
            if priority in ["low", "medium", "high", "urgent"]:
                request["params"]["priority"] = priority
                request["step"] += 1

                # Submit the ticket
                try:
                    result = create_ticket(customer_id, **request["params"])
                    self.complete_request(customer_id)
                    return f"Your ticket has been created successfully with ID: {result['id']}", True
                except Exception as e:
                    self.complete_request(customer_id)
                    return f"Sorry, I couldn't create your ticket: {str(e)}", True
            else:
                return "Please specify a priority level: low, medium, high, or urgent:", False
```

## Conversation State Machine

### State Transitions

Implement a state machine for conversation flow:

```python
from enum import Enum

class ConversationState(Enum):
    GREETING = "greeting"
    ACTIVE_LISTENING = "active_listening"
    PROCESSING_REQUEST = "processing_request"
    AWAITING_INPUT = "awaiting_input"
    PROVIDING_INFORMATION = "providing_information"
    HANDLING_ERROR = "handling_error"
    ESCALATING = "escalating"
    CLOSING = "closing"

class ConversationStateMachine:
    def __init__(self):
        self.current_state = ConversationState.GREETING
        self.state_handlers = {
            ConversationState.GREETING: self._handle_greeting,
            ConversationState.ACTIVE_LISTENING: self._handle_active_listening,
            ConversationState.PROCESSING_REQUEST: self._handle_processing_request,
            ConversationState.AWAITING_INPUT: self._handle_awaiting_input,
            ConversationState.PROVIDING_INFORMATION: self._handle_providing_information,
            ConversationState.HANDLING_ERROR: self._handle_handling_error,
            ConversationState.ESCALATING: self._handle_escalating,
            ConversationState.CLOSING: self._handle_closing
        }

    def transition_to(self, new_state: ConversationState):
        """Transition to a new state."""
        self.current_state = new_state

    def process_input(self, user_input: str, customer_id: str) -> str:
        """Process user input based on current state."""
        handler = self.state_handlers.get(self.current_state)
        if handler:
            return handler(user_input, customer_id)
        else:
            return "I'm sorry, I'm not sure how to handle your request right now."

    def _handle_greeting(self, user_input: str, customer_id: str) -> str:
        """Handle the greeting state."""
        # Retrieve customer info and greet them
        customer = get_customer_info(customer_id)
        greeting = f"Hello {customer.get('name', 'there')}! How can I help you today?"
        self.transition_to(ConversationState.ACTIVE_LISTENING)
        return greeting

    def _handle_active_listening(self, user_input: str, customer_id: str) -> str:
        """Handle active listening state - classify intent and decide next action."""
        intent_classifier = IntentClassifier()
        intent, confidence = intent_classifier.classify_intent(user_input)

        if confidence < 0.3:
            # Uncertain about intent, ask for clarification
            self.transition_to(ConversationState.AWAITING_INPUT)
            return "I'm not quite sure what you need help with. Could you please clarify your request?"

        # Process based on intent
        if intent == "support_ticket":
            # Start multi-turn ticket creation
            multi_turn = MultiTurnDialogue()
            multi_turn.start_request(customer_id, "create_ticket")
            self.transition_to(ConversationState.AWAITING_INPUT)
            return "I can help you create a support ticket. What is the subject of your ticket?"
        elif intent == "search_product":
            # Process product search
            self.transition_to(ConversationState.PROCESSING_REQUEST)
            # Implementation continues...

        return f"I understand you need help with {intent}. Let me assist you with that."
```

## Follow-up Question Handling

### Contextual Follow-ups

Handle follow-up questions within the same context:

```python
class FollowUpHandler:
    def __init__(self):
        self.follow_up_patterns = {
            "yes_no": [r"^(yes|no|y|n)\s*$", r"^(absolutely|definitely|sure|ok|okay)\s*$"],
            "clarification": [r"^what.*", r"how.*", r"why.*", r"when.*", r"where.*", r"who.*"],
            "elaboration": [r"tell me more", r"explain", r"details", r"more information"],
            "confirmation": [r"is that.*", r"are you.*", r"did you.*", r"can you.*"]
        }

    def detect_follow_up(self, user_input: str, previous_context: Dict) -> str:
        """Detect if the input is a follow-up question."""
        user_lower = user_input.lower().strip()

        # Check for yes/no responses
        for pattern in self.follow_up_patterns["yes_no"]:
            if re.match(pattern, user_lower):
                return "yes_no"

        # Check for clarification requests
        for pattern in self.follow_up_patterns["clarification"]:
            if re.match(pattern, user_lower):
                return "clarification"

        # Check for elaboration requests
        for pattern in self.follow_up_patterns["elaboration"]:
            if re.search(pattern, user_lower):
                return "elaboration"

        # Check for confirmation
        for pattern in self.follow_up_patterns["confirmation"]:
            if re.match(pattern, user_lower):
                return "confirmation"

        return "new_topic"

    def handle_follow_up(self, user_input: str, previous_response: str, context: Dict) -> str:
        """Handle follow-up questions appropriately."""
        follow_up_type = self.detect_follow_up(user_input, context)

        if follow_up_type == "yes_no":
            if re.match(r"^(yes|y|ok|okay|sure|absolutely)", user_input.lower()):
                return self.handle_affirmative_follow_up(context)
            else:
                return self.handle_negative_follow_up(context)

        elif follow_up_type == "clarification":
            return self.provide_clarification(user_input, previous_response)

        elif follow_up_type == "elaboration":
            return self.provide_elaboration(previous_response)

        elif follow_up_type == "confirmation":
            return self.handle_confirmation(user_input, previous_response)

        else:
            # New topic, start fresh
            return "new_topic"

    def handle_affirmative_follow_up(self, context: Dict) -> str:
        """Handle positive responses to previous questions."""
        if context.get("expected_follow_up") == "ticket_creation":
            # Continue with ticket creation process
            return "Great! Could you please provide more details about the issue?"

        return "I'm glad that was helpful. How else can I assist you?"

    def handle_negative_follow_up(self, context: Dict) -> str:
        """Handle negative responses to previous questions."""
        if context.get("expected_follow_up") == "ticket_creation":
            # Cancel ticket creation
            return "No problem. Is there something else I can help you with instead?"

        return "I understand. Let me know if there's anything else I can assist you with."
```

## Escalation Criteria

### Automatic Escalation

Implement criteria for escalating to human agents:

```python
class EscalationManager:
    def __init__(self):
        self.escalation_triggers = [
            lambda msg: self._detect_emotional_distress(msg),
            lambda msg: self._detect_complex_technical_issue(msg),
            lambda msg: self._detect_payment_complaints(msg),
            lambda msg: self._detect_legal_concerns(msg)
        ]
        self.max_retries = 3
        self.consecutive_fallbacks = 0

    def should_escalate(self, user_input: str, customer_id: str, conversation_stats: Dict) -> Tuple[bool, str]:
        """Determine if the conversation should be escalated to a human."""

        # Check for escalation triggers
        for trigger in self.escalation_triggers:
            result = trigger(user_input)
            if result[0]:  # If trigger indicates escalation needed
                return True, result[1]  # Return True and reason

        # Check for repeated failures
        if conversation_stats.get("fallback_count", 0) >= self.max_retries:
            return True, "Too many failed attempts to resolve issue"

        # Check for conversation length
        if conversation_stats.get("turn_count", 0) > 15:
            # Long conversation might indicate complexity
            return True, "Long conversation indicating complex issue"

        return False, ""

    def _detect_emotional_distress(self, message: str) -> Tuple[bool, str]:
        """Detect signs of emotional distress in the message."""
        distress_indicators = [
            r"(angry|frustrated|disappointed|upset|annoyed|mad|livid)",
            r"(waste.*time|ridiculous|absurd|joke|scam)",
            r"(complain|complaint|refund|compensation)",
            r"(sue|lawyer|legal|threaten)"
        ]

        message_lower = message.lower()
        for indicator in distress_indicators:
            if re.search(indicator, message_lower):
                return True, "Detected emotional distress in customer message"

        return False, ""

    def _detect_complex_technical_issue(self, message: str) -> Tuple[bool, str]:
        """Detect complex technical issues requiring human intervention."""
        technical_complexity_indicators = [
            r"(debug|traceback|stack.*trace|error.*code)",
            r"(integration|api|sdk|webhook|endpoint)",
            r"(database|server|network|infrastructure)",
            r"(multi.*step.*process|complex.*configuration)"
        ]

        message_lower = message.lower()
        for indicator in technical_complexity_indicators:
            if re.search(indicator, message_lower):
                return True, "Detected complex technical issue"

        return False, ""
```