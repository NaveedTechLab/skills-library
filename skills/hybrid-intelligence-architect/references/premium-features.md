# Premium-Gated Features Implementation Guide

## Architecture Overview

### Feature Tier System
Premium features should be implemented using a tier-based system that balances value proposition with accessibility:

```
Free Tier:
├── Basic progress tracking
├── Core learning content
├── Simple assessments
└── Community support

Basic Tier ($5/month):
├── Personalized learning paths
├── Enhanced content recommendations
├── Ad-free experience
└── Priority support

Premium Tier ($15/month):
├── Adaptive learning paths (AI-powered)
├── LLM-graded assessments
├── AI tutoring sessions
├── Advanced analytics
└── Certificate of completion

Enterprise Tier ($50/month):
├── All Premium features
├── Team collaboration tools
├── Custom content creation
├── Administrative dashboard
└── Dedicated support
```

## Implementation Patterns

### 1. Feature Access Control Layer
```python
from enum import Enum
from abc import ABC, abstractmethod
from typing import Dict, Any, Optional
import functools

class Tier(Enum):
    FREE = "free"
    BASIC = "basic"
    PREMIUM = "premium"
    ENTERPRISE = "enterprise"

class Feature(Enum):
    ADAPTIVE_LEARNING = "adaptive_learning"
    AI_ASSESSMENTS = "ai_assessments"
    AI_TUTORING = "ai_tutoring"
    ADVANCED_ANALYTICS = "advanced_analytics"
    CUSTOM_CONTENT = "custom_content"
    TEAM_COLLABORATION = "team_collaboration"

class FeaturePermission:
    def __init__(self, tier: Tier, feature: Feature, quota: Optional[int] = None):
        self.tier = tier
        self.feature = feature
        self.quota = quota  # Optional usage limit

# Define feature permissions by tier
FEATURE_PERMISSIONS = {
    Tier.FREE: [
        FeaturePermission(Tier.FREE, Feature.ADVANCED_ANALYTICS, 10),  # 10 reports/month
    ],
    Tier.BASIC: [
        FeaturePermission(Tier.BASIC, Feature.ADVANCED_ANALYTICS, 50),
    ],
    Tier.PREMIUM: [
        FeaturePermission(Tier.PREMIUM, Feature.ADAPTIVE_LEARNING),
        FeaturePermission(Tier.PREMIUM, Feature.AI_ASSESSMENTS),
        FeaturePermission(Tier.PREMIUM, Feature.ADVANCED_ANALYTICS, 200),
    ],
    Tier.ENTERPRISE: [
        FeaturePermission(Tier.ENTERPRISE, Feature.ADAPTIVE_LEARNING),
        FeaturePermission(Tier.ENTERPRISE, Feature.AI_ASSESSMENTS),
        FeaturePermission(Tier.ENTERPRISE, Feature.AI_TUTORING),
        FeaturePermission(Tier.ENTERPRISE, Feature.ADVANCED_ANALYTICS),
        FeaturePermission(Tier.ENTERPRISE, Feature.CUSTOM_CONTENT),
        FeaturePermission(Tier.ENTERPRISE, Feature.TEAM_COLLABORATION),
    ]
}

class AccessControl:
    def __init__(self, db_connection):
        self.db = db_connection

    def has_access(self, user_id: str, feature: Feature) -> Dict[str, Any]:
        """
        Check if user has access to a feature and return access details
        """
        user_tier = self._get_user_tier(user_id)

        # Check if feature is available in user's tier
        tier_permissions = FEATURE_PERMISSIONS.get(user_tier, [])
        feature_perm = next(
            (perm for perm in tier_permissions if perm.feature == feature),
            None
        )

        if not feature_perm:
            return {
                "has_access": False,
                "user_tier": user_tier.value,
                "required_tier": self._get_required_tier(feature).value,
                "message": f"This feature requires {self._get_required_tier(feature).value} tier or higher"
            }

        # Check quota if applicable
        if feature_perm.quota is not None:
            usage = self._get_usage_count(user_id, feature)
            if usage >= feature_perm.quota:
                return {
                    "has_access": False,
                    "user_tier": user_tier.value,
                    "quota_exceeded": True,
                    "usage": usage,
                    "limit": feature_perm.quota,
                    "message": f"You've reached your monthly limit of {feature_perm.quota} uses for this feature"
                }

        return {
            "has_access": True,
            "user_tier": user_tier.value,
            "usage_remaining": feature_perm.quota - self._get_usage_count(user_id, feature) if feature_perm.quota else None
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
            return Tier.FREE

    def _get_required_tier(self, feature: Feature) -> Tier:
        """
        Find the minimum tier required for a feature
        """
        for tier, permissions in FEATURE_PERMISSIONS.items():
            if any(perm.feature == feature for perm in permissions):
                return tier
        return Tier.ENTERPRISE  # Default to highest tier if not found

    def _get_usage_count(self, user_id: str, feature: Feature) -> int:
        """
        Get current usage count for feature
        """
        today = datetime.utcnow().date()
        result = self.db.execute("""
            SELECT COALESCE(SUM(usage_count), 0) FROM feature_usage
            WHERE user_id = ? AND feature = ? AND date_recorded = ?
        """, (user_id, feature.value, today)).fetchone()

        return result[0] if result else 0

    def track_usage(self, user_id: str, feature: Feature, count: int = 1):
        """
        Track feature usage for quota management
        """
        today = datetime.utcnow().date()
        self.db.execute("""
            INSERT INTO feature_usage (user_id, feature, usage_count, date_recorded)
            VALUES (?, ?, ?, ?)
            ON CONFLICT(user_id, feature, date_recorded)
            DO UPDATE SET usage_count = usage_count + ?
        """, (user_id, feature.value, count, today, count))
```

### 2. Decorator for Feature Access Control
```python
def require_feature_access(feature: Feature):
    """
    Decorator to enforce feature access control
    """
    def decorator(func):
        @functools.wraps(func)
        def wrapper(self, user_id: str, *args, **kwargs):
            access_control = getattr(self, 'access_control', None)
            if not access_control:
                raise AttributeError("Service must have 'access_control' attribute")

            access_result = access_control.has_access(user_id, feature)

            if not access_result["has_access"]:
                raise PermissionError(access_result.get("message", f"Access denied for feature: {feature.value}"))

            # Track usage if access is granted
            if "usage_remaining" in access_result:
                access_control.track_usage(user_id, feature)

            return func(self, user_id, *args, **kwargs)
        return wrapper
    return decorator

# Usage example:
class PremiumFeatureService:
    def __init__(self, access_control: AccessControl):
        self.access_control = access_control

    @require_feature_access(Feature.ADAPTIVE_LEARNING)
    def get_adaptive_path(self, user_id: str, preferences: Dict[str, Any]):
        # Implementation here
        pass

    @require_feature_access(Feature.AI_ASSESSMENTS)
    def grade_assessment(self, user_id: str, response: str):
        # Implementation here
        pass
```

## Adaptive Learning Paths Implementation

### 3. Premium Adaptive Learning Service
```python
from datetime import datetime, timedelta
from typing import List, Dict, Any
import random

class AdaptiveLearningService:
    def __init__(self, access_control: AccessControl, claude_client):
        self.access_control = access_control
        self.claude_client = claude_client

    @require_feature_access(Feature.ADAPTIVE_LEARNING)
    def generate_learning_path(
        self,
        user_id: str,
        user_profile: Dict[str, Any],
        course_content: List[Dict[str, Any]],
        learning_goals: List[str]
    ) -> Dict[str, Any]:
        """
        Generate personalized learning path using AI for premium users
        """
        # Get user's learning history and performance
        learning_history = self._get_learning_history(user_id)
        current_performance = self._analyze_performance(learning_history)

        # Use AI to generate adaptive path
        if self._is_premium_user(user_id):
            return self._generate_ai_path(
                user_profile, current_performance, course_content, learning_goals
            )
        else:
            # Fallback for non-premium users
            return self._generate_basic_path(
                user_profile, current_performance, course_content, learning_goals
            )

    def _is_premium_user(self, user_id: str) -> bool:
        """
        Check if user is premium tier
        """
        tier = self.access_control._get_user_tier(user_id)
        return tier in [Tier.PREMIUM, Tier.ENTERPRISE]

    def _generate_ai_path(
        self,
        user_profile: Dict[str, Any],
        current_performance: Dict[str, Any],
        course_content: List[Dict[str, Any]],
        learning_goals: List[str]
    ) -> Dict[str, Any]:
        """
        Generate learning path using Claude AI
        """
        try:
            system_prompt = """
            You are an expert educational advisor. Create a personalized learning path
            that adapts to the user's learning style, pace, and goals. Consider their
            current performance and recommend content in an optimal sequence.
            """

            user_context = {
                "profile": user_profile,
                "performance": current_performance,
                "goals": learning_goals,
                "available_content": course_content[:10]  # Limit to prevent prompt overflow
            }

            prompt = f"""
            Generate a learning path with the following structure:
            {{
                "path": [
                    {{"id": "...", "title": "...", "difficulty": "...", "estimated_time": "..."}}
                ],
                "strategy": "...",
                "reasoning": "...",
                "estimated_completion": "..."
            }}

            Context: {json.dumps(user_context, indent=2)}
            """

            response = self.claude_client.generate_response(
                messages=[{"role": "user", "content": prompt}],
                system_prompt=system_prompt,
                max_tokens=1500
            )

            import re
            import json

            # Extract JSON from response
            json_match = re.search(r'```(?:json)?\s*({.*?})\s*```', response, re.DOTALL)
            if json_match:
                path_data = json.loads(json_match.group(1))
            else:
                path_data = json.loads(response)

            return {
                "path": path_data.get("path", []),
                "strategy": path_data.get("strategy", ""),
                "reasoning": path_data.get("reasoning", ""),
                "estimated_completion": path_data.get("estimated_completion", ""),
                "generation_method": "ai"
            }

        except Exception as e:
            # Fallback to deterministic method if AI fails
            return self._generate_deterministic_path(
                user_profile, current_performance, course_content, learning_goals
            )

    def _generate_deterministic_path(
        self,
        user_profile: Dict[str, Any],
        current_performance: Dict[str, Any],
        course_content: List[Dict[str, Any]],
        learning_goals: List[str]
    ) -> Dict[str, Any]:
        """
        Fallback deterministic path generation
        """
        # Sort content by difficulty based on user's performance
        avg_score = current_performance.get('average_score', 50)

        sorted_content = sorted(
            course_content,
            key=lambda x: x.get('difficulty', 5),
            reverse=avg_score > 70  # More difficult content if user is performing well
        )

        return {
            "path": [
                {
                    "id": item['id'],
                    "title": item['title'],
                    "difficulty": item.get('difficulty', 'medium'),
                    "estimated_time": item.get('estimated_time', '30 minutes')
                }
                for item in sorted_content[:5]
            ],
            "strategy": "progressive_difficulty",
            "reasoning": f"Based on average score of {avg_score}%",
            "estimated_completion": "variable",
            "generation_method": "deterministic"
        }

    def _get_learning_history(self, user_id: str) -> List[Dict[str, Any]]:
        """
        Get user's learning history from database
        """
        # Implementation to fetch user's learning history
        pass

    def _analyze_performance(self, learning_history: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Analyze user's learning performance
        """
        if not learning_history:
            return {"average_score": 50, "completion_rate": 0.5, "learning_speed": "normal"}

        scores = [item.get('score', 0) for item in learning_history if 'score' in item]
        avg_score = sum(scores) / len(scores) if scores else 50

        completed_items = [item for item in learning_history if item.get('completed', False)]
        completion_rate = len(completed_items) / len(learning_history) if learning_history else 0

        return {
            "average_score": avg_score,
            "completion_rate": completion_rate,
            "learning_speed": "fast" if completion_rate > 0.8 else "slow" if completion_rate < 0.3 else "normal"
        }
```

## LLM-Graded Assessments Implementation

### 4. Premium Assessment Grading Service
```python
class AssessmentGradingService:
    def __init__(self, access_control: AccessControl, claude_client):
        self.access_control = access_control
        self.claude_client = claude_client

    @require_feature_access(Feature.AI_ASSESSMENTS)
    def grade_open_response(
        self,
        user_id: str,
        question: str,
        correct_answer: str,
        student_response: str,
        rubric: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Grade open-ended response using AI for premium users
        """
        if self._is_premium_user(user_id):
            return self._grade_with_ai(
                question, correct_answer, student_response, rubric
            )
        else:
            # Fallback to basic grading for non-premium users
            return self._grade_basic(
                question, correct_answer, student_response, rubric
            )

    def _grade_with_ai(
        self,
        question: str,
        correct_answer: str,
        student_response: str,
        rubric: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Grade response using Claude AI
        """
        try:
            system_prompt = """
            You are an expert educator and grader. Grade the student's response based on
            the question, correct answer, and rubric. Provide detailed feedback that helps
            the student understand their mistakes and how to improve.
            """

            grading_context = {
                "question": question,
                "correct_answer": correct_answer,
                "student_response": student_response,
                "rubric": rubric
            }

            prompt = f"""
            Grade the student response and provide detailed feedback in JSON format:
            {{
                "score": float (0-100),
                "feedback": "detailed feedback",
                "strengths": ["list of strengths"],
                "areas_for_improvement": ["list of improvement areas"],
                "conceptual_accuracy": float (0-100),
                "completeness": float (0-100),
                "clarity": float (0-100),
                "confidence": "high|medium|low"
            }}

            Context: {json.dumps(grading_context, indent=2)}
            """

            response = self.claude_client.generate_response(
                messages=[{"role": "user", "content": prompt}],
                system_prompt=system_prompt,
                max_tokens=1000
            )

            import re
            import json

            # Extract JSON from response
            json_match = re.search(r'```(?:json)?\s*({.*?})\s*```', response, re.DOTALL)
            if json_match:
                grade_data = json.loads(json_match.group(1))
            else:
                grade_data = json.loads(response)

            return {
                "score": grade_data.get("score", 0),
                "feedback": grade_data.get("feedback", ""),
                "strengths": grade_data.get("strengths", []),
                "areas_for_improvement": grade_data.get("areas_for_improvement", []),
                "conceptual_accuracy": grade_data.get("conceptual_accuracy", 0),
                "completeness": grade_data.get("completeness", 0),
                "clarity": grade_data.get("clarity", 0),
                "confidence": grade_data.get("confidence", "medium"),
                "grading_method": "ai"
            }

        except Exception as e:
            # Fallback to basic grading if AI fails
            return self._grade_basic(
                question, correct_answer, student_response, rubric
            )

    def _grade_basic(
        self,
        question: str,
        correct_answer: str,
        student_response: str,
        rubric: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Basic keyword-based grading for non-premium users
        """
        import re

        # Simple keyword matching
        correct_keywords = set(re.findall(r'\w+', correct_answer.lower()))
        student_keywords = set(re.findall(r'\w+', student_response.lower()))

        matched = len(correct_keywords.intersection(student_keywords))
        total = len(correct_keywords)

        score = (matched / total * 100) if total > 0 else 0

        return {
            "score": round(score, 2),
            "feedback": "Response contains basic keywords from the correct answer",
            "strengths": ["Contains relevant keywords"] if matched > 0 else [],
            "areas_for_improvement": ["Consider addressing all key concepts in more detail"],
            "conceptual_accuracy": score,
            "completeness": score,
            "clarity": 50,
            "confidence": "low",
            "grading_method": "keyword_matching"
        }

    def _is_premium_user(self, user_id: str) -> bool:
        """
        Check if user is premium tier
        """
        tier = self.access_control._get_user_tier(user_id)
        return tier in [Tier.PREMIUM, Tier.ENTERPRISE]
```

## AI Tutoring Implementation

### 5. Premium AI Tutoring Service
```python
class AITutoringService:
    def __init__(self, access_control: AccessControl, claude_client):
        self.access_control = access_control
        self.claude_client = claude_client

    @require_feature_access(Feature.AI_TUTORING)
    def start_tutoring_session(
        self,
        user_id: str,
        subject: str,
        learning_level: str,
        initial_question: str
    ) -> Dict[str, Any]:
        """
        Start an AI tutoring session for premium users
        """
        session_id = self._create_session(user_id, subject, learning_level)

        tutor_response = self._get_initial_tutor_response(
            subject, learning_level, initial_question
        )

        return {
            "session_id": session_id,
            "initial_response": tutor_response,
            "subject": subject,
            "learning_level": learning_level
        }

    def continue_tutoring_session(
        self,
        session_id: str,
        user_message: str
    ) -> Dict[str, Any]:
        """
        Continue tutoring session with user's follow-up
        """
        session = self._get_session(session_id)
        if not session:
            raise ValueError("Invalid session ID")

        # Verify user still has access to tutoring feature
        access_result = self.access_control.has_access(session['user_id'], Feature.AI_TUTORING)
        if not access_result["has_access"]:
            raise PermissionError("Tutoring session access expired")

        # Get conversation history
        history = self._get_conversation_history(session_id)

        tutor_response = self._get_tutor_response(
            session['subject'],
            session['learning_level'],
            history,
            user_message
        )

        # Track session usage
        self.access_control.track_usage(session['user_id'], Feature.AI_TUTORING)

        return {
            "response": tutor_response,
            "session_id": session_id
        }

    def _get_initial_tutor_response(
        self,
        subject: str,
        learning_level: str,
        initial_question: str
    ) -> str:
        """
        Get initial response from AI tutor
        """
        system_prompt = f"""
        You are an expert tutor in {subject} for {learning_level} learners.
        Provide helpful, encouraging, and educational responses.
        Adapt your teaching style to the student's level and questions.
        """

        prompt = f"""
        Student asks: {initial_question}

        Provide an educational response that:
        1. Answers the question directly
        2. Explains key concepts clearly
        3. Encourages further questions
        4. Maintains an engaging tone
        """

        try:
            return self.claude_client.generate_response(
                messages=[{"role": "user", "content": prompt}],
                system_prompt=system_prompt,
                max_tokens=500
            )
        except Exception:
            return "I'm having trouble connecting to the tutoring service right now. Please try again."

    def _get_tutor_response(
        self,
        subject: str,
        learning_level: str,
        history: List[Dict[str, str]],
        user_message: str
    ) -> str:
        """
        Get AI tutor response considering conversation history
        """
        system_prompt = f"""
        You are an expert tutor in {subject} for {learning_level} learners.
        Maintain continuity with the ongoing conversation while providing helpful responses.
        """

        # Format conversation history
        conversation = "\n".join([
            f"{'Student' if msg['role'] == 'user' else 'Tutor'}: {msg['content']}"
            for msg in history[-5:]  # Last 5 exchanges
        ])

        prompt = f"""
        Previous conversation:
        {conversation}

        Student now says: {user_message}

        Provide a helpful, contextual response that continues the tutoring session.
        """

        try:
            return self.claude_client.generate_response(
                messages=[{"role": "user", "content": prompt}],
                system_prompt=system_prompt,
                max_tokens=500
            )
        except Exception:
            return "I'm having trouble responding right now. Could you repeat your question?"

    def _create_session(self, user_id: str, subject: str, learning_level: str) -> str:
        """
        Create a new tutoring session
        """
        import uuid
        session_id = str(uuid.uuid4())

        # Store session in database
        self.db.execute("""
            INSERT INTO tutoring_sessions
            (session_id, user_id, subject, learning_level, created_at, status)
            VALUES (?, ?, ?, ?, ?, 'active')
        """, (session_id, user_id, subject, learning_level, datetime.utcnow()))

        return session_id

    def _get_session(self, session_id: str) -> Optional[Dict[str, Any]]:
        """
        Get session details
        """
        result = self.db.execute("""
            SELECT user_id, subject, learning_level FROM tutoring_sessions
            WHERE session_id = ? AND status = 'active'
        """, (session_id,)).fetchone()

        if result:
            return {
                "user_id": result[0],
                "subject": result[1],
                "learning_level": result[2]
            }
        return None

    def _get_conversation_history(self, session_id: str) -> List[Dict[str, str]]:
        """
        Get conversation history for session
        """
        result = self.db.execute("""
            SELECT role, content, timestamp FROM tutoring_messages
            WHERE session_id = ? ORDER BY timestamp ASC
        """, (session_id,)).fetchall()

        return [
            {"role": row[0], "content": row[1], "timestamp": row[2]}
            for row in result
        ]
```

## Usage Analytics and Reporting

### 6. Premium Analytics Service
```python
class PremiumAnalyticsService:
    def __init__(self, access_control: AccessControl):
        self.access_control = access_control

    @require_feature_access(Feature.ADVANCED_ANALYTICS)
    def get_advanced_analytics(
        self,
        user_id: str,
        start_date: datetime,
        end_date: datetime,
        include_predictions: bool = False
    ) -> Dict[str, Any]:
        """
        Get advanced analytics for premium users
        """
        base_analytics = self._get_standard_analytics(user_id, start_date, end_date)

        if include_predictions and self._is_enterprise_user(user_id):
            predictions = self._generate_learning_predictions(user_id, base_analytics)
            base_analytics["predictions"] = predictions

        return base_analytics

    def _get_standard_analytics(
        self,
        user_id: str,
        start_date: datetime,
        end_date: datetime
    ) -> Dict[str, Any]:
        """
        Get standard analytics data
        """
        # Fetch analytics data from database
        learning_data = self._fetch_learning_data(user_id, start_date, end_date)

        return {
            "learning_time": self._calculate_total_learning_time(learning_data),
            "completion_rate": self._calculate_completion_rate(learning_data),
            "average_score": self._calculate_average_score(learning_data),
            "topics_covered": self._get_topics_covered(learning_data),
            "study_patterns": self._analyze_study_patterns(learning_data),
            "performance_trends": self._analyze_performance_trends(learning_data)
        }

    def _generate_learning_predictions(
        self,
        user_id: str,
        current_analytics: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Generate predictive analytics for enterprise users
        """
        # This would typically involve ML models
        # For demonstration, we'll simulate predictions

        current_performance = current_analytics.get('average_score', 70)
        completion_rate = current_analytics.get('completion_rate', 0.6)

        # Predictions based on current trends
        predicted_completion = min(1.0, completion_rate * 1.2)  # 20% improvement prediction
        predicted_score = min(100, current_performance * 1.1)  # 10% improvement prediction

        return {
            "predicted_completion_rate": predicted_completion,
            "predicted_average_score": predicted_score,
            "time_to_completion": self._predict_completion_time(current_analytics),
            "recommended_actions": self._generate_recommendations(current_analytics),
            "confidence_interval": 0.85
        }

    def _is_enterprise_user(self, user_id: str) -> bool:
        """
        Check if user is enterprise tier
        """
        tier = self.access_control._get_user_tier(user_id)
        return tier == Tier.ENTERPRISE
```

## Payment and Subscription Management

### 7. Subscription Management
```python
class SubscriptionManager:
    def __init__(self, db_connection):
        self.db = db_connection

    def create_subscription(
        self,
        user_id: str,
        tier: Tier,
        payment_method_token: str,
        billing_cycle_months: int = 1
    ) -> Dict[str, Any]:
        """
        Create a new subscription
        """
        from datetime import datetime, timedelta

        # Calculate expiration date
        expires_at = datetime.utcnow() + timedelta(days=30 * billing_cycle_months)

        # Process payment (in real implementation, integrate with payment processor)
        payment_success = self._process_payment(payment_method_token, tier)

        if not payment_success:
            raise ValueError("Payment processing failed")

        # Create subscription record
        self.db.execute("""
            INSERT INTO subscriptions
            (user_id, tier, status, payment_method_token, expires_at, created_at)
            VALUES (?, ?, 'active', ?, ?, ?)
        """, (user_id, tier.value, payment_method_token, expires_at, datetime.utcnow()))

        # Apply any welcome benefits for new subscribers
        self._apply_new_subscriber_benefits(user_id, tier)

        return {
            "success": True,
            "subscription_id": f"sub_{user_id}_{datetime.utcnow().timestamp()}",
            "user_id": user_id,
            "tier": tier.value,
            "expires_at": expires_at.isoformat(),
            "billing_cycle": f"{billing_cycle_months} month(s)"
        }

    def upgrade_subscription(
        self,
        user_id: str,
        new_tier: Tier,
        immediate: bool = False
    ) -> Dict[str, Any]:
        """
        Upgrade user's subscription tier
        """
        current_subscription = self._get_current_subscription(user_id)

        if not current_subscription:
            raise ValueError("No active subscription found")

        if new_tier.value <= current_subscription['tier']:
            raise ValueError("New tier must be higher than current tier")

        # Calculate prorated charges if upgrading mid-cycle
        if immediate:
            refund_amount = self._calculate_proration(
                current_subscription, new_tier
            )

        # Update subscription
        new_expires_at = self._calculate_new_expiry(
            current_subscription, new_tier, immediate
        )

        self.db.execute("""
            UPDATE subscriptions
            SET tier = ?, expires_at = ?
            WHERE user_id = ? AND status = 'active'
        """, (new_tier.value, new_expires_at, user_id))

        return {
            "success": True,
            "user_id": user_id,
            "previous_tier": current_subscription['tier'],
            "new_tier": new_tier.value,
            "expires_at": new_expires_at.isoformat(),
            "upgrade_date": datetime.utcnow().isoformat()
        }

    def cancel_subscription(
        self,
        user_id: str,
        reason: str = None,
        immediate: bool = False
    ) -> Dict[str, Any]:
        """
        Cancel subscription
        """
        current_subscription = self._get_current_subscription(user_id)

        if not current_subscription or current_subscription['status'] != 'active':
            raise ValueError("No active subscription to cancel")

        if immediate:
            # Cancel immediately
            self.db.execute("""
                UPDATE subscriptions
                SET status = 'cancelled', cancelled_at = ?
                WHERE user_id = ?
            """, (datetime.utcnow(), user_id))
        else:
            # Cancel at end of current billing cycle
            self.db.execute("""
                UPDATE subscriptions
                SET status = 'cancelled', cancelled_at = ?,
                    expires_at = (SELECT expires_at FROM subscriptions WHERE user_id = ?)
                WHERE user_id = ?
            """, (datetime.utcnow(), user_id, user_id))

        return {
            "success": True,
            "user_id": user_id,
            "cancelled_at": datetime.utcnow().isoformat(),
            "expires_at": current_subscription['expires_at'],
            "immediate": immediate
        }

    def _get_current_subscription(self, user_id: str) -> Optional[Dict[str, Any]]:
        """
        Get user's current subscription
        """
        result = self.db.execute("""
            SELECT user_id, tier, status, expires_at, created_at
            FROM subscriptions
            WHERE user_id = ? AND status = 'active'
        """, (user_id,)).fetchone()

        if result:
            return {
                "user_id": result[0],
                "tier": result[1],
                "status": result[2],
                "expires_at": result[3],
                "created_at": result[4]
            }
        return None

    def _process_payment(self, token: str, tier: Tier) -> bool:
        """
        Process payment using payment processor
        """
        # In real implementation, integrate with Stripe, PayPal, etc.
        # For demo purposes, always return True
        pricing = {
            Tier.BASIC: 5.00,
            Tier.PREMIUM: 15.00,
            Tier.ENTERPRISE: 50.00
        }

        amount = pricing.get(tier, 0.00)

        # Simulate payment processing
        import random
        return random.random() > 0.1  # 90% success rate for demo

    def _calculate_new_expiry(
        self,
        current_subscription: Dict[str, Any],
        new_tier: Tier,
        immediate: bool
    ) -> datetime:
        """
        Calculate new expiry date for upgraded subscription
        """
        if immediate:
            # Calculate based on current billing cycle
            current_expiry = current_subscription['expires_at']
            days_remaining = (current_expiry - datetime.utcnow()).days
            return datetime.utcnow() + timedelta(days=days_remaining)
        else:
            # Extend to next billing cycle
            return current_subscription['expires_at']
```

This guide provides comprehensive patterns for implementing premium-gated features with proper access control, AI integration, and subscription management.