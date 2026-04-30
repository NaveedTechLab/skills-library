# Implementation Patterns for Hybrid Intelligence Systems

## 1. Service Layer Architecture

### Core Service Structure
```python
class HybridIntelligenceService:
    """
    Base class for hybrid intelligence services that combine
    deterministic logic with AI enhancements
    """
    def __init__(self, ai_client=None, fallback_handler=None):
        self.ai_client = ai_client
        self.fallback_handler = fallback_handler
        self.circuit_breaker = AICircuitBreaker()
        self.logger = logging.getLogger(self.__class__.__name__)

    def execute_with_fallback(self, method_name: str, *args, **kwargs):
        """
        Execute a method with automatic fallback to deterministic approach
        """
        try:
            # Try AI-enhanced approach first
            if self.ai_client:
                result = self.circuit_breaker.call(
                    getattr(self, f"_ai_{method_name}"),
                    *args,
                    **kwargs
                )
                return {
                    "result": result,
                    "method": "ai_enhanced",
                    "success": True
                }
        except AICircuitBreakerOpenError:
            # Circuit breaker is open, use fallback
            pass
        except Exception as e:
            self.logger.warning(f"AI method failed: {e}")

        # Fallback to deterministic approach
        result = getattr(self, f"_deterministic_{method_name}")(*args, **kwargs)
        return {
            "result": result,
            "method": "deterministic",
            "success": True,
            "fallback_used": True
        }
```

### Adaptive Learning Path Service
```python
class AdaptiveLearningPathService(HybridIntelligenceService):
    def __init__(self, ai_client=None, fallback_handler=None, db_connection=None):
        super().__init__(ai_client, fallback_handler)
        self.db = db_connection

    def generate_path(self, user_id: str, preferences: dict):
        """
        Generate personalized learning path
        """
        user_profile = self._get_user_profile(user_id)

        return self.execute_with_fallback(
            "generate_path",
            user_profile=user_profile,
            preferences=preferences
        )

    def _ai_generate_path(self, user_profile: dict, preferences: dict):
        """
        AI-enhanced path generation
        """
        prompt = f"""
        Create a personalized learning path for a user with this profile:
        {json.dumps(user_profile, indent=2)}

        Preferences: {json.dumps(preferences, indent=2)}

        Return a structured learning path with recommended modules and sequence.
        """

        return self.ai_client.generate_structured_response(
            prompt=prompt,
            response_schema={
                "type": "object",
                "required": ["modules", "sequence"],
                "properties": {
                    "modules": {"type": "array", "items": {"type": "string"}},
                    "sequence": {"type": "array", "items": {"type": "integer"}},
                    "estimated_duration": {"type": "string"}
                }
            }
        )

    def _deterministic_generate_path(self, user_profile: dict, preferences: dict):
        """
        Deterministic path generation
        """
        # Implement basic recommendation logic
        user_level = user_profile.get('level', 'beginner')
        preferred_subjects = preferences.get('subjects', [])

        # Query database for relevant content
        query = """
        SELECT id, title, difficulty, estimated_time
        FROM content
        WHERE difficulty <= ? AND subject IN ({})
        ORDER BY difficulty, rating DESC
        LIMIT 10
        """.format(','.join(['?' for _ in preferred_subjects]))

        results = self.db.execute(query, [user_level] + preferred_subjects).fetchall()

        return {
            "modules": [row[0] for row in results],
            "sequence": list(range(len(results))),
            "estimated_duration": f"{sum(row[3] for row in results)} minutes",
            "method": "popularity_based"
        }

    def _get_user_profile(self, user_id: str):
        """
        Get user profile from database
        """
        result = self.db.execute(
            "SELECT * FROM user_profiles WHERE user_id = ?", (user_id,)
        ).fetchone()

        if result:
            return dict(zip([column[0] for column in self.db.execute("PRAGMA table_info(user_profiles)").fetchall()], result))
        else:
            return {"level": "beginner", "learning_style": "visual", "subjects": []}
```

## 2. Feature Access Control

### Tier-Based Access Control
```python
class FeatureAccessController:
    """
    Controls access to premium features based on user tier
    """
    def __init__(self, db_connection):
        self.db = db_connection
        self.tier_features = {
            "free": ["basic_progress_tracking", "core_content"],
            "basic": ["basic_progress_tracking", "core_content", "simple_recommendations"],
            "premium": [
                "basic_progress_tracking", "core_content", "simple_recommendations",
                "adaptive_learning_paths", "ai_assisted_assessments", "advanced_analytics"
            ],
            "enterprise": [
                "basic_progress_tracking", "core_content", "simple_recommendations",
                "adaptive_learning_paths", "ai_assisted_assessments", "advanced_analytics",
                "custom_content_creation", "team_collaboration", "dedicated_support"
            ]
        }

    def has_access(self, user_id: str, feature: str) -> dict:
        """
        Check if user has access to a feature
        """
        user_tier = self._get_user_tier(user_id)

        if feature in self.tier_features.get(user_tier, []):
            # Check usage limits
            if self._has_usage_quota(user_id, feature):
                return {
                    "has_access": True,
                    "tier": user_tier,
                    "feature": feature
                }
            else:
                return {
                    "has_access": False,
                    "reason": "QUOTA_EXCEEDED",
                    "message": "You've reached your usage limit for this feature"
                }
        else:
            required_tier = self._get_required_tier(feature)
            return {
                "has_access": False,
                "reason": "INSUFFICIENT_TIER",
                "required_tier": required_tier,
                "message": f"This feature requires {required_tier} tier or higher"
            }

    def _get_user_tier(self, user_id: str) -> str:
        """
        Get user's current tier from database
        """
        result = self.db.execute("""
            SELECT tier FROM subscriptions
            WHERE user_id = ? AND status = 'active' AND expires_at > ?
        """, (user_id, datetime.utcnow())).fetchone()

        return result[0] if result else "free"

    def _has_usage_quota(self, user_id: str, feature: str) -> bool:
        """
        Check if user has remaining quota for feature
        """
        today = datetime.utcnow().date()
        result = self.db.execute("""
            SELECT SUM(usage_count) FROM feature_usage
            WHERE user_id = ? AND feature = ? AND date_recorded = ?
        """, (user_id, feature, today)).fetchone()

        used = result[0] if result[0] else 0
        quota = self._get_quota_limit(self._get_user_tier(user_id), feature)

        return used < quota

    def _get_quota_limit(self, tier: str, feature: str) -> int:
        """
        Get quota limit for feature based on tier
        """
        quotas = {
            "free": {"simple_recommendations": 5},
            "basic": {"simple_recommendations": 20},
            "premium": {
                "simple_recommendations": 100,
                "adaptive_learning_paths": 50,
                "ai_assisted_assessments": 30
            },
            "enterprise": {
                "simple_recommendations": 1000,
                "adaptive_learning_paths": 500,
                "ai_assisted_assessments": 1000
            }
        }

        return quotas.get(tier, {}).get(feature, 0)

    def track_usage(self, user_id: str, feature: str, count: int = 1):
        """
        Track feature usage for quota management
        """
        today = datetime.utcnow().date()
        self.db.execute("""
            INSERT INTO feature_usage (user_id, feature, usage_count, date_recorded)
            VALUES (?, ?, ?, ?)
            ON CONFLICT(user_id, feature, date_recorded)
            DO UPDATE SET usage_count = usage_count + ?
        """, (user_id, feature, count, today, count))
```

## 3. AI Assessment Grading

### Structured Assessment Grading
```python
class AIAssessmentGrader:
    """
    Grades assessments using AI with fallback to deterministic methods
    """
    def __init__(self, ai_client, fallback_handler):
        self.ai_client = ai_client
        self.fallback_handler = fallback_handler
        self.circuit_breaker = AICircuitBreaker()

    def grade_response(self, question: str, correct_answer: str, student_response: str, rubric: dict):
        """
        Grade student response using AI
        """
        try:
            # Try AI grading
            result = self.circuit_breaker.call(
                self._ai_grade_response,
                question=question,
                correct_answer=correct_answer,
                student_response=student_response,
                rubric=rubric
            )

            return {
                **result,
                "grading_method": "ai",
                "success": True
            }
        except AICircuitBreakerOpenError:
            # Use fallback
            result = self._fallback_grade_response(
                question, correct_answer, student_response, rubric
            )
            return {
                **result,
                "grading_method": "fallback",
                "success": True,
                "fallback_reason": "circuit_breaker_open"
            }
        except Exception as e:
            # Use fallback for any other error
            result = self._fallback_grade_response(
                question, correct_answer, student_response, rubric
            )
            return {
                **result,
                "grading_method": "fallback",
                "success": True,
                "fallback_reason": str(e)
            }

    def _ai_grade_response(self, question: str, correct_answer: str, student_response: str, rubric: dict):
        """
        AI-based grading
        """
        prompt = f"""
        Grade the following student response based on the question, correct answer, and rubric:

        Question: {question}
        Correct Answer: {correct_answer}
        Student Response: {student_response}
        Rubric: {json.dumps(rubric, indent=2)}

        Provide a score (0-100), detailed feedback, and assessment of key areas.
        Return in JSON format with structure:
        {{
            "score": float,
            "feedback": "string",
            "strengths": ["string"],
            "improvements_needed": ["string"],
            "content_accuracy": float,
            "clarity": float,
            "completeness": float
        }}
        """

        schema = {
            "type": "object",
            "required": ["score", "feedback"],
            "properties": {
                "score": {"type": "number", "minimum": 0, "maximum": 100},
                "feedback": {"type": "string"},
                "strengths": {"type": "array", "items": {"type": "string"}},
                "improvements_needed": {"type": "array", "items": {"type": "string"}},
                "content_accuracy": {"type": "number", "minimum": 0, "maximum": 100},
                "clarity": {"type": "number", "minimum": 0, "maximum": 100},
                "completeness": {"type": "number", "minimum": 0, "maximum": 100}
            }
        }

        return self.ai_client.generate_structured_response(
            prompt=prompt,
            response_schema=schema
        )

    def _fallback_grade_response(self, question: str, correct_answer: str, student_response: str, rubric: dict):
        """
        Fallback grading using deterministic methods
        """
        # Simple keyword matching approach
        correct_words = set(re.findall(r'\w+', correct_answer.lower()))
        student_words = set(re.findall(r'\w+', student_response.lower()))

        matched_words = len(correct_words.intersection(student_words))
        total_correct_words = len(correct_words)

        score = (matched_words / total_correct_words * 100) if total_correct_words > 0 else 0

        return {
            "score": round(score, 2),
            "feedback": "Graded using keyword matching methodology",
            "strengths": ["Contains relevant keywords"] if matched_words > 0 else [],
            "improvements_needed": ["Consider addressing all key concepts in the correct answer"],
            "content_accuracy": score,
            "clarity": 50,  # Default for fallback
            "completeness": score,
            "grading_method": "keyword_matching"
        }
```

## 4. Data Validation and Sanitization

### Secure Data Processing Pipeline
```python
class SecureDataProcessor:
    """
    Processes data securely with validation and sanitization
    """
    def __init__(self):
        self.sensitive_patterns = [
            r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b',  # Email
            r'\b\d{3}-?\d{3}-?\d{4}\b',  # Phone
            r'\b\d{4}[-\s]?\d{4}[-\s]?\d{4}[-\s]?\d{4}\b',  # Credit card
            r'\b\d{3}-\d{2}-\d{4}\b'  # SSN
        ]

    def validate_and_sanitize(self, data: dict) -> dict:
        """
        Validate and sanitize input data
        """
        validated_data = {}

        for key, value in data.items():
            if isinstance(value, str):
                # Sanitize sensitive information
                sanitized_value = self._sanitize_sensitive_info(value)

                # Validate the sanitized value
                if self._is_valid_content(sanitized_value):
                    validated_data[key] = sanitized_value
                else:
                    raise ValueError(f"Invalid content in field '{key}'")
            else:
                validated_data[key] = value

        return validated_data

    def _sanitize_sensitive_info(self, text: str) -> str:
        """
        Remove or mask sensitive information from text
        """
        sanitized_text = text

        for pattern in self.sensitive_patterns:
            sanitized_text = re.sub(pattern, '[REDACTED]', sanitized_text)

        return sanitized_text

    def _is_valid_content(self, text: str) -> bool:
        """
        Validate content for appropriate content
        """
        # Check for prompt injection attempts
        injection_indicators = ['<system>', '<user>', '<assistant>', '{{', '}}']
        for indicator in injection_indicators:
            if indicator in text.lower():
                return False

        # Check for excessive length
        if len(text) > 10000:  # Arbitrary limit
            return False

        # Check for valid characters (basic validation)
        if not re.match(r'^[\\w\\s\\-\\.,!?;:\\(\\)\\[\\]{}\'\"@#\$%\^&\*\+=\|\/\\\\<>~`]+$',
                       text.replace('\n', '').replace('\r', '').replace('\t', '')):
            return False

        return True

    def prepare_for_ai_processing(self, data: dict) -> dict:
        """
        Prepare data for AI processing with additional security measures
        """
        sanitized_data = self.validate_and_sanitize(data)

        # Add security context
        processed_data = {
            **sanitized_data,
            "_security_processed": True,
            "_timestamp": datetime.utcnow().isoformat()
        }

        return processed_data
```

## 5. Error Handling and Monitoring

### Comprehensive Error Handler
```python
class HybridErrorHandler:
    """
    Handles errors in hybrid systems with proper logging and fallbacks
    """
    def __init__(self, logger, alert_system=None):
        self.logger = logger
        self.alert_system = alert_system

    def handle_ai_error(self, error: Exception, context: dict):
        """
        Handle errors from AI services
        """
        error_info = {
            "error_type": type(error).__name__,
            "error_message": str(error),
            "context": context,
            "timestamp": datetime.utcnow().isoformat()
        }

        # Log the error
        self.logger.error(f"AI Service Error: {error_info}")

        # Determine if this is a service-level issue
        if self._is_service_disruption(error):
            # Alert operations team
            if self.alert_system:
                self.alert_system.send_alert(
                    severity="HIGH",
                    message=f"AI Service disruption: {type(error).__name__}",
                    context=error_info
                )

        # Return error handling strategy
        return {
            "action": "use_fallback",
            "retry_allowed": self._is_retryable(error),
            "backoff_seconds": self._calculate_backoff(error)
        }

    def _is_service_disruption(self, error: Exception) -> bool:
        """
        Determine if error indicates service disruption
        """
        service_disruption_errors = [
            "ConnectionError", "Timeout", "RateLimitError",
            "ServiceUnavailable", "InternalServerError"
        ]

        return type(error).__name__ in service_disruption_errors

    def _is_retryable(self, error: Exception) -> bool:
        """
        Determine if error is retryable
        """
        non_retryable_errors = [
            "AuthenticationError", "PermissionError", "NotFoundError",
            "ValidationError", "BadRequestError"
        ]

        return type(error).__name__ not in non_retryable_errors

    def _calculate_backoff(self, error: Exception) -> int:
        """
        Calculate appropriate backoff time
        """
        if self._is_service_disruption(error):
            return 30  # 30 seconds for service disruptions
        else:
            return 5  # 5 seconds for other errors

    def log_ai_interaction(self, request: dict, response: dict, success: bool):
        """
        Log AI interactions for monitoring and debugging
        """
        log_entry = {
            "request": {k: v for k, v in request.items() if k != 'api_key'},  # Don't log API keys
            "response_summary": {
                "success": success,
                "response_length": len(str(response)) if response else 0,
                "timestamp": datetime.utcnow().isoformat()
            }
        }

        self.logger.info(f"AI Interaction: {log_entry}")
```

These patterns provide a comprehensive framework for implementing hybrid intelligence systems that safely integrate LLMs while maintaining deterministic core functionality and proper access controls.