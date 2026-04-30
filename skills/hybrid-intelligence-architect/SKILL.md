---
name: hybrid-intelligence-architect
description: Expert in selective LLM integration using Claude Agent SDK. Specialized in implementing premium-gated features like adaptive learning paths and LLM-graded assessments while maintaining strict isolation from deterministic logic.
---

# Hybrid Intelligence Architect

Expert in selective LLM integration using Claude Agent SDK. Specialized in implementing premium-gated features like adaptive learning paths and LLM-graded assessments while maintaining strict isolation from deterministic logic.

## When to Use This Skill

Use this skill when designing and implementing hybrid intelligence systems that:
- Integrate LLMs selectively for enhanced functionality
- Implement premium-gated features using Claude Agent SDK
- Create adaptive learning paths based on user performance
- Develop LLM-graded assessments with quality controls
- Maintain strict separation between deterministic and AI-enhanced logic
- Ensure data privacy and security in AI-enabled systems

## Core Principles

### Selective LLM Integration
- Identify use cases where LLMs add genuine value
- Implement fallback mechanisms for deterministic behavior
- Design for graceful degradation when AI services are unavailable
- Balance AI enhancement with system reliability

### Premium-Gated Feature Architecture
- Design feature tiers with clear value propositions
- Implement robust access control and licensing systems
- Create compelling premium experiences that justify costs
- Ensure free-tier users still receive quality core functionality

### Deterministic Logic Isolation
- Strict separation between core business logic and AI enhancements
- Maintain data integrity and consistency guarantees
- Implement circuit breakers for AI service failures
- Preserve audit trails and compliance requirements

## Claude Agent SDK Integration

### Basic Agent Setup
```python
from anthropic import Anthropic
from typing import List, Dict, Any
import json

class ClaudeAgent:
    def __init__(self, api_key: str):
        self.client = Anthropic(api_key=api_key)

    def create_completion(self,
                        messages: List[Dict[str, str]],
                        model: str = "claude-3-sonnet-20240229",
                        max_tokens: int = 1000,
                        temperature: float = 0.7) -> str:
        """
        Create a completion using Claude
        """
        response = self.client.messages.create(
            model=model,
            max_tokens=max_tokens,
            temperature=temperature,
            messages=messages
        )

        return response.content[0].text

# Example usage
agent = ClaudeAgent(api_key="your-api-key")
messages = [
    {"role": "user", "content": "Explain quantum computing in simple terms."}
]
response = agent.create_completion(messages)
```

### Adaptive Learning Path Agent
```python
class AdaptiveLearningAgent:
    def __init__(self, api_key: str):
        self.claude = ClaudeAgent(api_key)

    def generate_personalized_learning_path(
        self,
        user_profile: Dict[str, Any],
        current_performance: Dict[str, Any],
        learning_objectives: List[str],
        available_content: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """
        Generate a personalized learning path based on user data
        """
        system_prompt = """
        You are an expert educational advisor. Create a personalized learning path
        that adapts to the user's current knowledge level, learning pace, and goals.
        Consider their past performance and preferred learning styles.
        """

        user_data = f"""
        User Profile: {json.dumps(user_profile, indent=2)}
        Current Performance: {json.dumps(current_performance, indent=2)}
        Learning Objectives: {learning_objectives}
        Available Content: {json.dumps(available_content[:5], indent=2)}  # Limit to first 5 items
        """

        messages = [
            {"role": "user", "content": f"{system_prompt}\n\n{user_data}"}
        ]

        response = self.claude.create_completion(
            messages=messages,
            max_tokens=2000,
            temperature=0.3  # Lower temperature for more consistent recommendations
        )

        # Parse and validate the response
        try:
            learning_path = json.loads(response)
            return self._validate_learning_path(learning_path)
        except json.JSONDecodeError:
            # Fallback to deterministic algorithm if AI response is malformed
            return self._generate_deterministic_path(user_profile, current_performance, available_content)

    def _validate_learning_path(self, path: Dict[str, Any]) -> Dict[str, Any]:
        """
        Validate the AI-generated learning path
        """
        required_keys = ['recommended_modules', 'sequence', 'estimated_duration']
        for key in required_keys:
            if key not in path:
                raise ValueError(f"Missing required key: {key}")

        return path

    def _generate_deterministic_path(
        self,
        user_profile: Dict[str, Any],
        current_performance: Dict[str, Any],
        available_content: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """
        Fallback deterministic algorithm for learning path generation
        """
        # Implement basic recommendation logic based on performance data
        sorted_content = sorted(
            available_content,
            key=lambda x: x.get('difficulty', 1) if current_performance.get('avg_score', 0) > 70 else x.get('difficulty', 10),
            reverse=current_performance.get('avg_score', 0) > 70
        )

        return {
            'recommended_modules': [item['id'] for item in sorted_content[:5]],
            'sequence': list(range(len(sorted_content[:5]))),
            'estimated_duration': sum(item.get('duration_minutes', 30) for item in sorted_content[:5]),
            'fallback_reason': 'AI response validation failed'
        }
```

### LLM-Graded Assessment Agent
```python
class LLMGradedAssessmentAgent:
    def __init__(self, api_key: str):
        self.claude = ClaudeAgent(api_key)

    def grade_open_response(
        self,
        question: str,
        correct_answer: str,
        student_response: str,
        rubric: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Grade an open-ended response using LLM
        """
        system_prompt = """
        You are an educational assessment expert. Grade the student's response based on the
        provided question, correct answer, and rubric. Be fair, consistent, and provide
        constructive feedback. Return your response in JSON format with the following structure:
        {
            "score": float (0-100),
            "max_score": 100,
            "feedback": "detailed feedback",
            "strengths": ["list of strengths"],
            "areas_for_improvement": ["list of improvement areas"],
            "confidence": "high|medium|low"
        }
        """

        evaluation_context = f"""
        QUESTION: {question}

        CORRECT ANSWER: {correct_answer}

        STUDENT RESPONSE: {student_response}

        RUBRIC: {json.dumps(rubric, indent=2)}

        Evaluate the student response and provide detailed feedback.
        """

        messages = [
            {"role": "user", "content": f"{system_prompt}\n\n{evaluation_context}"}
        ]

        try:
            response = self.claude.create_completion(
                messages=messages,
                max_tokens=1500,
                temperature=0.2  # Very low temperature for consistency
            )

            # Attempt to parse JSON response
            grade_result = self._extract_json_from_response(response)
            return self._validate_grade_result(grade_result)
        except Exception as e:
            # Fallback to basic keyword matching
            return self._grade_deterministically(question, correct_answer, student_response, rubric)

    def _extract_json_from_response(self, response: str) -> Dict[str, Any]:
        """
        Extract JSON from Claude's response (may include explanatory text)
        """
        # Look for JSON within triple backticks
        import re
        json_match = re.search(r'```(?:json)?\s*({.*?})\s*```', response, re.DOTALL)
        if json_match:
            return json.loads(json_match.group(1))

        # Try to parse the entire response
        return json.loads(response)

    def _validate_grade_result(self, grade: Dict[str, Any]) -> Dict[str, Any]:
        """
        Validate the AI-graded assessment
        """
        required_keys = ['score', 'feedback', 'confidence']
        for key in required_keys:
            if key not in grade:
                raise ValueError(f"Missing required key in grade result: {key}")

        # Validate score range
        if not 0 <= grade['score'] <= 100:
            raise ValueError(f"Score must be between 0-100, got: {grade['score']}")

        return grade

    def _grade_deterministically(
        self,
        question: str,
        correct_answer: str,
        student_response: str,
        rubric: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Fallback deterministic grading
        """
        # Simple keyword matching approach
        correct_keywords = correct_answer.lower().split()
        student_keywords = student_response.lower().split()

        matched_keywords = len(set(correct_keywords) & set(student_keywords))
        total_keywords = len(set(correct_keywords))

        score = (matched_keywords / total_keywords * 100) if total_keywords > 0 else 0

        return {
            'score': round(score, 2),
            'max_score': 100,
            'feedback': 'Automatically graded using keyword matching',
            'strengths': ['Response contains relevant keywords'] if matched_keywords > 0 else [],
            'areas_for_improvement': ['Consider expanding on key concepts'],
            'confidence': 'low',
            'grading_method': 'deterministic_keyword_matching'
        }
```

## Premium Feature Architecture

### Feature Access Control
```python
from enum import Enum
from datetime import datetime
from typing import Optional

class FeatureTier(Enum):
    FREE = "free"
    PREMIUM = "premium"
    ENTERPRISE = "enterprise"

class FeatureAccessControl:
    def __init__(self, db_connection):
        self.db = db_connection

    def check_feature_access(
        self,
        user_id: str,
        feature_name: str,
        required_tier: FeatureTier
    ) -> Dict[str, Any]:
        """
        Check if user has access to a premium feature
        """
        # Get user's current tier
        user_tier = self._get_user_tier(user_id)

        # Check if user has required tier or higher
        tier_permissions = {
            FeatureTier.FREE: 0,
            FeatureTier.PREMIUM: 1,
            FeatureTier.ENTERPRISE: 2
        }

        has_access = tier_permissions[user_tier] >= tier_permissions[required_tier]

        return {
            'has_access': has_access,
            'user_tier': user_tier.value,
            'required_tier': required_tier.value,
            'feature_name': feature_name
        }

    def _get_user_tier(self, user_id: str) -> FeatureTier:
        """
        Get user's subscription tier from database
        """
        # Query database for user's subscription status
        result = self.db.execute(
            "SELECT tier FROM subscriptions WHERE user_id = ? AND expires_at > ?",
            (user_id, datetime.utcnow())
        ).fetchone()

        if result:
            return FeatureTier(result[0])
        else:
            return FeatureTier.FREE

    def track_usage(self, user_id: str, feature_name: str, usage_count: int = 1):
        """
        Track feature usage for quota management
        """
        self.db.execute(
            """
            INSERT INTO feature_usage (user_id, feature_name, usage_count, date_recorded)
            VALUES (?, ?, ?, ?)
            ON CONFLICT(user_id, feature_name, date_recorded)
            DO UPDATE SET usage_count = usage_count + ?
            """,
            (user_id, feature_name, usage_count, datetime.utcnow().date(), usage_count)
        )
```

### Circuit Breaker for AI Services
```python
import time
from enum import Enum

class CircuitState(Enum):
    CLOSED = "closed"      # Normal operation
    OPEN = "open"          # Service temporarily unavailable
    HALF_OPEN = "half_open" # Testing if service is restored

class AICircuitBreaker:
    def __init__(self, failure_threshold: int = 5, timeout: int = 60):
        self.failure_threshold = failure_threshold
        self.timeout = timeout
        self.failure_count = 0
        self.last_failure_time = None
        self.state = CircuitState.CLOSED

    def call(self, func, *args, **kwargs):
        """
        Call the AI function with circuit breaker protection
        """
        if self.state == CircuitState.OPEN:
            if time.time() - self.last_failure_time > self.timeout:
                self.state = CircuitState.HALF_OPEN
            else:
                raise Exception("Circuit breaker is OPEN - AI service unavailable")

        try:
            result = func(*args, **kwargs)
            self._on_success()
            return result
        except Exception as e:
            self._on_failure()
            raise e

    def _on_success(self):
        """
        Called when AI call succeeds
        """
        self.failure_count = 0
        self.state = CircuitState.CLOSED

    def _on_failure(self):
        """
        Called when AI call fails
        """
        self.failure_count += 1
        self.last_failure_time = time.time()

        if self.failure_count >= self.failure_threshold:
            self.state = CircuitState.OPEN

    def force_close(self):
        """
        Force circuit breaker to closed state
        """
        self.failure_count = 0
        self.state = CircuitState.CLOSED
```

## Implementation Patterns

### Hybrid Service Pattern
```python
class HybridIntelligenceService:
    def __init__(self, api_key: str, db_connection):
        self.ai_agent = ClaudeAgent(api_key)
        self.access_control = FeatureAccessControl(db_connection)
        self.circuit_breaker = AICircuitBreaker()
        self.fallback_enabled = True

    def get_adaptive_learning_path(
        self,
        user_id: str,
        user_profile: Dict[str, Any],
        current_performance: Dict[str, Any],
        available_content: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """
        Get adaptive learning path with fallback mechanisms
        """
        # Check access
        access_check = self.access_control.check_feature_access(
            user_id, "adaptive_learning", FeatureTier.PREMIUM
        )

        if not access_check['has_access']:
            # Use basic recommendation for non-premium users
            return self._get_basic_recommendation(user_profile, current_performance, available_content)

        # Track usage
        self.access_control.track_usage(user_id, "adaptive_learning")

        # Attempt AI-enhanced path generation
        if self.fallback_enabled:
            try:
                agent = AdaptiveLearningAgent(self.ai_agent.client.api_key)

                def ai_call():
                    return agent.generate_personalized_learning_path(
                        user_profile, current_performance, [], available_content
                    )

                return self.circuit_breaker.call(ai_call)

            except Exception as e:
                print(f"AI service failed, falling back to deterministic method: {e}")
                agent = AdaptiveLearningAgent(None)  # Pass None to force fallback
                return agent._generate_deterministic_path(
                    user_profile, current_performance, available_content
                )
        else:
            # Always use deterministic method if fallback is disabled
            agent = AdaptiveLearningAgent(None)
            return agent._generate_deterministic_path(
                user_profile, current_performance, available_content
            )

    def _get_basic_recommendation(
        self,
        user_profile: Dict[str, Any],
        current_performance: Dict[str, Any],
        available_content: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """
        Basic recommendation for free-tier users
        """
        # Implement basic recommendation logic
        sorted_content = sorted(available_content, key=lambda x: x.get('popularity', 0), reverse=True)

        return {
            'recommended_modules': [item['id'] for item in sorted_content[:3]],
            'sequence': list(range(len(sorted_content[:3]))),
            'estimated_duration': sum(item.get('duration_minutes', 30) for item in sorted_content[:3]),
            'tier': 'basic'
        }
```

## Quality Assurance and Testing

### AI Response Validation
```python
import json
import re
from typing import Any, Dict

class AIResponseValidator:
    @staticmethod
    def validate_json_response(response: str, required_keys: list) -> Dict[str, Any]:
        """
        Validate that AI response contains required JSON structure
        """
        try:
            # Extract JSON from response if surrounded by text
            json_match = re.search(r'```(?:json)?\s*({.*?})\s*```', response, re.DOTALL)
            if json_match:
                data = json.loads(json_match.group(1))
            else:
                data = json.loads(response)

            # Check for required keys
            missing_keys = [key for key in required_keys if key not in data]
            if missing_keys:
                raise ValueError(f"Missing required keys: {missing_keys}")

            return data
        except json.JSONDecodeError:
            raise ValueError("Invalid JSON in AI response")
        except Exception as e:
            raise e

    @staticmethod
    def validate_assessment_grade(grade: Dict[str, Any]) -> bool:
        """
        Validate assessment grade structure and values
        """
        required_keys = ['score', 'feedback', 'confidence']
        for key in required_keys:
            if key not in grade:
                return False

        # Validate score range
        if not isinstance(grade['score'], (int, float)) or not 0 <= grade['score'] <= 100:
            return False

        # Validate confidence level
        if grade['confidence'] not in ['high', 'medium', 'low']:
            return False

        return True
```

## Security and Privacy Considerations

### Data Sanitization
```python
import re

class DataSanitizer:
    @staticmethod
    def sanitize_user_input(text: str) -> str:
        """
        Sanitize user input before sending to AI
        """
        # Remove potential prompt injection attempts
        sanitized = re.sub(r'<system[^>]*>', '[SYSTEM_TAG_REMOVED]', text, flags=re.IGNORECASE)
        sanitized = re.sub(r'<user[^>]*>', '[USER_TAG_REMOVED]', sanitized, flags=re.IGNORECASE)
        sanitized = re.sub(r'<assistant[^>]*>', '[ASSISTANT_TAG_REMOVED]', sanitized, flags=re.IGNORECASE)

        # Remove excessive whitespace
        sanitized = re.sub(r'\s+', ' ', sanitized).strip()

        return sanitized

    @staticmethod
    def remove_pii(text: str) -> str:
        """
        Remove personally identifiable information
        """
        # Remove email addresses
        text = re.sub(r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b', '[EMAIL_REMOVED]', text)

        # Remove phone numbers
        text = re.sub(r'\b\d{3}[-.]?\d{3}[-.]?\d{4}\b', '[PHONE_REMOVED]', text)

        # Remove credit card numbers
        text = re.sub(r'\b\d{4}[-\s]?\d{4}[-\s]?\d{4}[-\s]?\d{4}\b', '[CARD_REMOVED]', text)

        return text
```

This skill provides comprehensive guidance for implementing hybrid intelligence systems that selectively integrate LLMs while maintaining strict separation between AI-enhanced features and core deterministic logic.