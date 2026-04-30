# LLM Integration Patterns Guide

## Selective Integration Strategy

### When to Use LLMs
LLMs should be selectively integrated when they provide clear value over deterministic algorithms:

**Good candidates for LLM integration:**
- Natural language understanding and generation
- Creative content creation
- Complex reasoning and analysis
- Personalization and adaptation
- Open-ended question answering

**Better served by deterministic logic:**
- Financial calculations
- User authentication
- Data validation
- Transaction processing
- Compliance reporting

### Integration Architecture Patterns

#### 1. Enhancement Pattern
```python
class ContentEnhancementService:
    def __init__(self, llm_client):
        self.llm_client = llm_client

    def enhance_content(self, content: str, enhancement_type: str) -> str:
        """
        Enhance content using LLM when premium feature is available
        """
        if enhancement_type == "summarize":
            return self._summarize_with_llm(content)
        elif enhancement_type == "translate":
            return self._translate_with_llm(content)
        else:
            # Fallback to basic processing
            return self._basic_enhancement(content, enhancement_type)

    def _summarize_with_llm(self, content: str) -> str:
        prompt = f"Summarize the following content in 3-4 sentences:\n\n{content}"
        return self.llm_client.generate(prompt)

    def _basic_enhancement(self, content: str, enhancement_type: str) -> str:
        """
        Basic enhancement without LLM
        """
        if enhancement_type == "summarize":
            # Simple truncation
            return content[:200] + "..." if len(content) > 200 else content
        return content
```

#### 2. Fallback Pattern
```python
class QuestionAnsweringService:
    def __init__(self, llm_client):
        self.llm_client = llm_client

    def answer_question(self, question: str, context: str) -> dict:
        """
        Attempt LLM answer, fall back to keyword search if needed
        """
        try:
            # Try LLM-based answer
            llm_answer = self._get_llm_answer(question, context)
            return {
                "answer": llm_answer,
                "method": "llm",
                "confidence": 0.8
            }
        except Exception as e:
            # Fall back to keyword search
            keyword_answer = self._keyword_search_answer(question, context)
            return {
                "answer": keyword_answer,
                "method": "keyword_search",
                "confidence": 0.4
            }

    def _get_llm_answer(self, question: str, context: str) -> str:
        prompt = f"Based on the following context, answer the question:\n\nContext: {context}\n\nQuestion: {question}"
        return self.llm_client.generate(prompt)

    def _keyword_search_answer(self, question: str, context: str) -> str:
        """
        Simple keyword-based answer extraction
        """
        import re
        # Extract key terms from question
        question_terms = re.findall(r'\w+', question.lower())

        # Find sentences containing key terms
        sentences = context.split('.')
        best_sentence = ""
        best_match_count = 0

        for sentence in sentences:
            match_count = sum(1 for term in question_terms if term in sentence.lower())
            if match_count > best_match_count:
                best_match_count = match_count
                best_sentence = sentence.strip()

        return best_sentence or "Unable to find relevant answer in context."
```

## Claude Agent SDK Implementation

### Basic Claude Integration
```python
from anthropic import Anthropic
import json
from typing import List, Dict, Any, Optional

class ClaudeIntegration:
    def __init__(self, api_key: str):
        self.client = Anthropic(api_key=api_key)

    def generate_response(
        self,
        messages: List[Dict[str, str]],
        model: str = "claude-3-sonnet-20240229",
        max_tokens: int = 1000,
        temperature: float = 0.7,
        system_prompt: Optional[str] = None
    ) -> str:
        """
        Generate response using Claude
        """
        try:
            response = self.client.messages.create(
                model=model,
                max_tokens=max_tokens,
                temperature=temperature,
                system=system_prompt,
                messages=messages
            )

            return response.content[0].text
        except Exception as e:
            raise ClaudeIntegrationError(f"Claude API error: {str(e)}")

    def generate_structured_response(
        self,
        prompt: str,
        response_schema: Dict[str, Any],
        system_prompt: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Generate structured response following a specific schema
        """
        # Include schema in the prompt to guide Claude
        schema_str = json.dumps(response_schema, indent=2)
        structured_prompt = f"""
        Respond in valid JSON format following this schema:
        {schema_str}

        Content: {prompt}
        """

        messages = [{"role": "user", "content": structured_prompt}]

        response = self.generate_response(
            messages=messages,
            system_prompt=system_prompt,
            temperature=0.3  # Lower temperature for more consistent structure
        )

        return self._parse_and_validate_json(response, response_schema)

    def _parse_and_validate_json(self, response: str, expected_schema: Dict[str, Any]) -> Dict[str, Any]:
        """
        Parse Claude's response and validate against expected schema
        """
        try:
            # Try to extract JSON from response (might be surrounded by text)
            import re
            json_match = re.search(r'```(?:json)?\s*({.*?})\s*```', response, re.DOTALL)
            if json_match:
                data = json.loads(json_match.group(1))
            else:
                # Try parsing entire response
                data = json.loads(response)

            # Basic validation against schema structure
            self._validate_against_schema(data, expected_schema)

            return data
        except json.JSONDecodeError:
            raise ClaudeIntegrationError("Invalid JSON response from Claude")
        except Exception as e:
            raise ClaudeIntegrationError(f"Schema validation error: {str(e)}")

    def _validate_against_schema(self, data: Dict[str, Any], schema: Dict[str, Any]):
        """
        Basic schema validation
        """
        required_keys = schema.get('required', [])
        for key in required_keys:
            if key not in data:
                raise ValueError(f"Missing required key: {key}")

        # Additional type validation could be added here
        properties = schema.get('properties', {})
        for key, value in data.items():
            if key in properties and 'type' in properties[key]:
                expected_type = properties[key]['type']
                if expected_type == 'string' and not isinstance(value, str):
                    raise ValueError(f"Expected string for {key}, got {type(value).__name__}")
                elif expected_type == 'number' and not isinstance(value, (int, float)):
                    raise ValueError(f"Expected number for {key}, got {type(value).__name__}")
                elif expected_type == 'boolean' and not isinstance(value, bool):
                    raise ValueError(f"Expected boolean for {key}, got {type(value).__name__")
```

### Error Handling and Circuit Breaker
```python
import time
from enum import Enum
from typing import Callable, Any

class ClaudeIntegrationError(Exception):
    """Custom exception for Claude integration errors"""
    pass

class CircuitState(Enum):
    CLOSED = "closed"      # Normal operation
    OPEN = "open"          # Service temporarily unavailable
    HALF_OPEN = "half_open" # Testing if service is restored

class ClaudeCircuitBreaker:
    def __init__(self, failure_threshold: int = 5, timeout: int = 60):
        self.failure_threshold = failure_threshold
        self.timeout = timeout
        self.failure_count = 0
        self.last_failure_time = None
        self.state = CircuitState.CLOSED
        self.success_on_half_open = False

    def call(self, func: Callable, *args, **kwargs) -> Any:
        """
        Call Claude function with circuit breaker protection
        """
        if self.state == CircuitState.OPEN:
            # Check if timeout has passed to move to half-open state
            if self.last_failure_time and (time.time() - self.last_failure_time > self.timeout):
                self.state = CircuitState.HALF_OPEN
            else:
                raise ClaudeIntegrationError("Circuit breaker is OPEN - Claude service unavailable")

        try:
            result = func(*args, **kwargs)
            self._on_success()
            return result
        except Exception as e:
            self._on_failure()
            raise e

    def _on_success(self):
        """
        Called when Claude call succeeds
        """
        self.failure_count = 0
        self.state = CircuitState.CLOSED
        self.success_on_half_open = True

    def _on_failure(self):
        """
        Called when Claude call fails
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
        self.success_on_half_open = False
```

## Premium-Gated Feature Implementation

### Subscription and Feature Tiers
```python
from enum import Enum
from datetime import datetime, timedelta
from typing import List, Dict, Any

class Feature(Enum):
    ADAPTIVE_LEARNING = "adaptive_learning"
    ADVANCED_ASSESSMENTS = "advanced_assessments"
    AI_TUTOR = "ai_tutor"
    CONTENT_PERSONALIZATION = "content_personalization"
    PROGRESS_ANALYTICS = "progress_analytics"

class Tier(Enum):
    FREE = "free"
    BASIC = "basic"
    PREMIUM = "premium"
    ENTERPRISE = "enterprise"

TIER_FEATURES = {
    Tier.FREE: [
        Feature.PROGRESS_ANALYTICS
    ],
    Tier.BASIC: [
        Feature.PROGRESS_ANALYTICS,
        Feature.CONTENT_PERSONALIZATION
    ],
    Tier.PREMIUM: [
        Feature.ADAPTIVE_LEARNING,
        Feature.ADVANCED_ASSESSMENTS,
        Feature.CONTENT_PERSONALIZATION,
        Feature.PROGRESS_ANALYTICS
    ],
    Tier.ENTERPRISE: [
        Feature.ADAPTIVE_LEARNING,
        Feature.ADVANCED_ASSESSMENTS,
        Feature.AI_TUTOR,
        Feature.CONTENT_PERSONALIZATION,
        Feature.PROGRESS_ANALYTICS
    ]
}

class SubscriptionManager:
    def __init__(self, db_connection):
        self.db = db_connection

    def check_feature_access(self, user_id: str, feature: Feature) -> Dict[str, Any]:
        """
        Check if user has access to a specific feature
        """
        user_tier = self._get_user_tier(user_id)

        # Check if feature is available in user's tier
        has_access = feature in TIER_FEATURES.get(user_tier, [])

        return {
            "has_access": has_access,
            "user_tier": user_tier.value,
            "feature": feature.value,
            "available_in_tier": self._get_tiers_with_feature(feature)
        }

    def _get_user_tier(self, user_id: str) -> Tier:
        """
        Get user's current subscription tier
        """
        result = self.db.execute("""
            SELECT tier FROM subscriptions
            WHERE user_id = ?
            AND status = 'active'
            AND expires_at > ?
        """, (user_id, datetime.utcnow())).fetchone()

        if result:
            return Tier(result[0])
        else:
            return Tier.FREE  # Default to free tier

    def _get_tiers_with_feature(self, feature: Feature) -> List[str]:
        """
        Get all tiers that include the specified feature
        """
        return [
            tier.value for tier, features in TIER_FEATURES.items()
            if feature in features
        ]

    def upgrade_subscription(self, user_id: str, new_tier: Tier, months: int = 1) -> Dict[str, Any]:
        """
        Upgrade user's subscription
        """
        if new_tier == Tier.FREE:
            raise ValueError("Cannot upgrade to FREE tier")

        current_tier = self._get_user_tier(user_id)

        if new_tier.value <= current_tier.value:
            raise ValueError(f"New tier must be higher than current tier ({current_tier.value})")

        # Calculate expiration date
        expires_at = datetime.utcnow() + timedelta(days=months * 30)

        # Update subscription
        self.db.execute("""
            INSERT OR REPLACE INTO subscriptions
            (user_id, tier, status, expires_at, created_at)
            VALUES (?, ?, 'active', ?, CURRENT_TIMESTAMP)
        """, (user_id, new_tier.value, expires_at))

        return {
            "success": True,
            "user_id": user_id,
            "previous_tier": current_tier.value,
            "new_tier": new_tier.value,
            "expires_at": expires_at.isoformat()
        }
```

### Usage Tracking and Quotas
```python
class UsageTracker:
    def __init__(self, db_connection):
        self.db = db_connection

    def track_usage(self, user_id: str, feature: Feature, usage_amount: int = 1) -> Dict[str, Any]:
        """
        Track feature usage for quota management
        """
        today = datetime.utcnow().date()

        # Increment usage count
        self.db.execute("""
            INSERT INTO feature_usage (user_id, feature, usage_count, date_recorded)
            VALUES (?, ?, ?, ?)
            ON CONFLICT(user_id, feature, date_recorded)
            DO UPDATE SET usage_count = usage_count + ?
        """, (user_id, feature.value, usage_amount, today, usage_amount))

        # Get current usage
        current_usage = self.get_daily_usage(user_id, feature, today)

        return {
            "user_id": user_id,
            "feature": feature.value,
            "usage_today": current_usage,
            "timestamp": datetime.utcnow().isoformat()
        }

    def get_daily_usage(self, user_id: str, feature: Feature, date: datetime.date) -> int:
        """
        Get daily usage for a feature
        """
        result = self.db.execute("""
            SELECT usage_count FROM feature_usage
            WHERE user_id = ? AND feature = ? AND date_recorded = ?
        """, (user_id, feature.value, date)).fetchone()

        return result[0] if result else 0

    def check_quota(self, user_id: str, feature: Feature, tier: Tier) -> Dict[str, Any]:
        """
        Check if user is within quota limits
        """
        daily_usage = self.get_daily_usage(user_id, feature, datetime.utcnow().date())

        quota_limits = {
            Tier.FREE: {
                Feature.PROGRESS_ANALYTICS: 10,
                Feature.CONTENT_PERSONALIZATION: 5
            },
            Tier.BASIC: {
                Feature.PROGRESS_ANALYTICS: 50,
                Feature.CONTENT_PERSONALIZATION: 25,
                Feature.ADVANCED_ASSESSMENTS: 10
            },
            Tier.PREMIUM: {
                Feature.ADAPTIVE_LEARNING: 100,
                Feature.ADVANCED_ASSESSMENTS: 50,
                Feature.CONTENT_PERSONALIZATION: 100,
                Feature.PROGRESS_ANALYTICS: 200
            },
            Tier.ENTERPRISE: {
                Feature.ADAPTIVE_LEARNING: 1000,
                Feature.ADVANCED_ASSESSMENTS: 500,
                Feature.AI_TUTOR: 200,
                Feature.CONTENT_PERSONALIZATION: 1000,
                Feature.PROGRESS_ANALYTICS: 2000
            }
        }

        max_usage = quota_limits.get(tier, {}).get(feature, 0)

        return {
            "within_quota": daily_usage < max_usage,
            "daily_usage": daily_usage,
            "quota_limit": max_usage,
            "remaining": max_usage - daily_usage if max_usage > 0 else float('inf')
        }
```

## Adaptive Learning Path Implementation

### AI-Powered Learning Path Generation
```python
class AdaptiveLearningEngine:
    def __init__(self, claude_client: ClaudeIntegration):
        self.claude = claude_client

    def generate_learning_path(
        self,
        user_profile: Dict[str, Any],
        course_content: List[Dict[str, Any]],
        learning_objectives: List[str],
        current_progress: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Generate personalized learning path using Claude
        """
        system_prompt = """
        You are an expert educational advisor. Create a personalized learning path
        that considers the learner's profile, current progress, and learning objectives.
        The path should be challenging but achievable, with content ordered by
        prerequisite knowledge and difficulty progression.
        """

        user_data = {
            "user_profile": user_profile,
            "learning_objectives": learning_objectives,
            "current_progress": current_progress,
            "available_content": course_content[:10]  # Limit to prevent prompt overflow
        }

        prompt = f"""
        Based on this user data, create a learning path with the following structure:
        {{
            "recommended_sequence": [
                {{"id": "...", "title": "...", "estimated_time": "...", "prerequisites": [...]}}
            ],
            "learning_strategy": "...",
            "adaptation_reasoning": "...",
            "estimated_completion_time": "..."
        }}

        User Data: {json.dumps(user_data, indent=2)}
        """

        schema = {
            "type": "object",
            "required": ["recommended_sequence", "learning_strategy", "adaptation_reasoning"],
            "properties": {
                "recommended_sequence": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "required": ["id", "title"],
                        "properties": {
                            "id": {"type": "string"},
                            "title": {"type": "string"},
                            "estimated_time": {"type": "string"},
                            "prerequisites": {"type": "array", "items": {"type": "string"}}
                        }
                    }
                },
                "learning_strategy": {"type": "string"},
                "adaptation_reasoning": {"type": "string"},
                "estimated_completion_time": {"type": "string"}
            }
        }

        try:
            response = self.claude.generate_structured_response(
                prompt=prompt,
                response_schema=schema,
                system_prompt=system_prompt
            )

            # Validate and return the learning path
            return self._validate_learning_path(response, course_content)

        except ClaudeIntegrationError:
            # Fallback to deterministic algorithm
            return self._generate_deterministic_path(user_profile, course_content, current_progress)

    def _validate_learning_path(
        self,
        path: Dict[str, Any],
        available_content: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """
        Validate the AI-generated learning path
        """
        available_ids = {item['id'] for item in available_content}

        # Validate all recommended content exists
        for item in path.get('recommended_sequence', []):
            if item['id'] not in available_ids:
                raise ValueError(f"Invalid content ID in learning path: {item['id']}")

        return path

    def _generate_deterministic_path(
        self,
        user_profile: Dict[str, Any],
        course_content: List[Dict[str, Any]],
        current_progress: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Fallback deterministic learning path generation
        """
        # Sort content by difficulty based on user's current performance
        avg_score = current_progress.get('average_score', 0)

        sorted_content = sorted(
            course_content,
            key=lambda x: x.get('difficulty', 5) if avg_score > 70 else x.get('difficulty', 1),
            reverse=avg_score > 70  # More difficult content if user is performing well
        )

        return {
            "recommended_sequence": [
                {
                    "id": item['id'],
                    "title": item['title'],
                    "estimated_time": item.get('estimated_time', '30 minutes'),
                    "prerequisites": item.get('prerequisites', [])
                }
                for item in sorted_content[:5]
            ],
            "learning_strategy": "progressive_difficulty",
            "adaptation_reasoning": f"Based on average score of {avg_score}%",
            "estimated_completion_time": "variable",
            "generation_method": "deterministic"
        }
```

## LLM-Graded Assessments

### AI Assessment Grading
```python
class AIAssessmentGrader:
    def __init__(self, claude_client: ClaudeIntegration):
        self.claude = claude_client

    def grade_open_response(
        self,
        question: str,
        correct_answer: str,
        student_response: str,
        rubric: Dict[str, Any],
        context: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Grade open-ended student response using Claude
        """
        system_prompt = """
        You are an experienced educator and grader. Grade the student's response based on the
        provided question, correct answer, rubric, and context. Provide detailed feedback that
        helps the student understand their mistakes and how to improve.

        Return your response in JSON format with this structure:
        {
            "score": float (0-100),
            "max_score": 100,
            "feedback": "detailed feedback",
            "strengths": ["list of strengths"],
            "areas_for_improvement": ["list of improvement areas"],
            "conceptual_accuracy": float (0-100),
            "completeness": float (0-100),
            "clarity": float (0-100),
            "grade_confidence": "high|medium|low"
        }
        """

        grading_context = {
            "question": question,
            "correct_answer": correct_answer,
            "student_response": student_response,
            "rubric": rubric,
            "context": context or "No additional context provided"
        }

        prompt = f"""
        Grade the following student response according to the rubric and provide detailed feedback:

        {json.dumps(grading_context, indent=2)}
        """

        schema = {
            "type": "object",
            "required": ["score", "feedback", "grade_confidence"],
            "properties": {
                "score": {"type": "number", "minimum": 0, "maximum": 100},
                "max_score": {"type": "number", "const": 100},
                "feedback": {"type": "string"},
                "strengths": {"type": "array", "items": {"type": "string"}},
                "areas_for_improvement": {"type": "array", "items": {"type": "string"}},
                "conceptual_accuracy": {"type": "number", "minimum": 0, "maximum": 100},
                "completeness": {"type": "number", "minimum": 0, "maximum": 100},
                "clarity": {"type": "number", "minimum": 0, "maximum": 100},
                "grade_confidence": {"type": "string", "enum": ["high", "medium", "low"]}
            }
        }

        try:
            response = self.claude.generate_structured_response(
                prompt=prompt,
                response_schema=schema,
                system_prompt=system_prompt
            )

            # Validate the grading result
            return self._validate_grading_result(response)

        except ClaudeIntegrationError:
            # Fallback to keyword-based grading
            return self._grade_keyword_based(
                question, correct_answer, student_response, rubric
            )

    def _validate_grading_result(self, result: Dict[str, Any]) -> Dict[str, Any]:
        """
        Validate the AI-graded assessment result
        """
        required_keys = ['score', 'feedback', 'grade_confidence']
        for key in required_keys:
            if key not in result:
                raise ValueError(f"Missing required key in grading result: {key}")

        # Validate score range
        score = result['score']
        if not (0 <= score <= 100):
            raise ValueError(f"Score must be between 0-100, got: {score}")

        # Validate confidence level
        confidence = result.get('grade_confidence', '').lower()
        if confidence not in ['high', 'medium', 'low']:
            raise ValueError(f"Invalid confidence level: {confidence}")

        return result

    def _grade_keyword_based(
        self,
        question: str,
        correct_answer: str,
        student_response: str,
        rubric: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Fallback keyword-based grading
        """
        import re

        # Extract key concepts from correct answer
        correct_words = set(re.findall(r'\w+', correct_answer.lower()))
        student_words = set(re.findall(r'\w+', student_response.lower()))

        # Calculate overlap
        matched_concepts = len(correct_words.intersection(student_words))
        total_concepts = len(correct_words)

        score = (matched_concepts / total_concepts * 100) if total_concepts > 0 else 0

        return {
            "score": round(score, 2),
            "max_score": 100,
            "feedback": "Graded using keyword matching methodology",
            "strengths": ["Response contains relevant keywords"] if matched_concepts > 0 else [],
            "areas_for_improvement": ["Consider addressing all key concepts in the correct answer"],
            "conceptual_accuracy": score,
            "completeness": score,
            "clarity": 50,  # Default clarity for keyword-based grading
            "grade_confidence": "low",
            "grading_method": "keyword_matching"
        }
```

This guide provides comprehensive patterns for implementing selective LLM integration with proper fallbacks, premium feature gating, and robust error handling.