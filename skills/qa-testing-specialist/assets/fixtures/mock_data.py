"""
Mock data fixtures for testing
"""
import pytest
from datetime import datetime, timedelta

# User fixtures
@pytest.fixture
def mock_user():
    """Mock user data"""
    return {
        "id": "user_123",
        "email": "test@example.com",
        "username": "testuser",
        "is_active": True,
        "created_at": datetime.utcnow().isoformat()
    }

@pytest.fixture
def mock_authenticated_user(mock_user):
    """Mock authenticated user with token"""
    return {
        **mock_user,
        "access_token": "test_access_token_123",
        "refresh_token": "test_refresh_token_123",
        "token_type": "bearer"
    }

# Social Media Account fixtures
@pytest.fixture
def mock_linkedin_account():
    """Mock LinkedIn account connection"""
    return {
        "id": "linkedin_123",
        "user_id": "user_123",
        "platform": "linkedin",
        "platform_user_id": "linkedin_user_456",
        "access_token": "linkedin_token_789",
        "refresh_token": "linkedin_refresh_789",
        "expires_at": (datetime.utcnow() + timedelta(days=60)).isoformat(),
        "is_active": True
    }

@pytest.fixture
def mock_twitter_account():
    """Mock Twitter account connection"""
    return {
        "id": "twitter_123",
        "user_id": "user_123",
        "platform": "twitter",
        "platform_user_id": "twitter_user_456",
        "access_token": "twitter_token_789",
        "refresh_token": "twitter_refresh_789",
        "expires_at": (datetime.utcnow() + timedelta(hours=2)).isoformat(),
        "is_active": True
    }

@pytest.fixture
def mock_facebook_account():
    """Mock Facebook account connection"""
    return {
        "id": "facebook_123",
        "user_id": "user_123",
        "platform": "facebook",
        "platform_user_id": "facebook_user_456",
        "access_token": "facebook_token_789",
        "expires_at": (datetime.utcnow() + timedelta(days=60)).isoformat(),
        "is_active": True
    }

# Post fixtures
@pytest.fixture
def mock_post():
    """Mock social media post"""
    return {
        "id": "post_123",
        "user_id": "user_123",
        "platform": "linkedin",
        "content": "This is a test post about AI and technology",
        "status": "published",
        "platform_post_id": "urn:li:share:123456789",
        "published_at": datetime.utcnow().isoformat(),
        "created_at": datetime.utcnow().isoformat()
    }

@pytest.fixture
def mock_scheduled_post():
    """Mock scheduled post"""
    return {
        "id": "post_456",
        "user_id": "user_123",
        "platform": "twitter",
        "content": "Scheduled tweet about machine learning",
        "status": "scheduled",
        "scheduled_for": (datetime.utcnow() + timedelta(hours=2)).isoformat(),
        "created_at": datetime.utcnow().isoformat()
    }

# Feedback fixtures
@pytest.fixture
def mock_post_metrics():
    """Mock post performance metrics"""
    return {
        "post_id": "post_123",
        "likes": 150,
        "comments": 25,
        "shares": 10,
        "impressions": 5000,
        "clicks": 200,
        "engagement_rate": 0.037,
        "collected_at": datetime.utcnow().isoformat()
    }

@pytest.fixture
def mock_feedback_data():
    """Mock feedback data for learning"""
    return {
        "id": "feedback_123",
        "post_id": "post_123",
        "user_id": "user_123",
        "platform": "linkedin",
        "metrics": {
            "likes": 150,
            "comments": 25,
            "shares": 10,
            "impressions": 5000,
            "engagement_rate": 0.037
        },
        "context": {
            "posting_time": "12:00",
            "day_of_week": "Tuesday",
            "content_type": "educational",
            "has_image": True,
            "has_hashtags": True,
            "hashtag_count": 3
        },
        "created_at": datetime.utcnow().isoformat()
    }

# WhatsApp fixtures
@pytest.fixture
def mock_whatsapp_message():
    """Mock WhatsApp incoming message"""
    return {
        "from": "1234567890",
        "id": "wamid.test123",
        "timestamp": str(int(datetime.utcnow().timestamp())),
        "text": {"body": "Hello, I need help with my marketing campaign"},
        "type": "text"
    }

@pytest.fixture
def mock_whatsapp_webhook_payload():
    """Mock complete WhatsApp webhook payload"""
    return {
        "object": "whatsapp_business_account",
        "entry": [{
            "id": "123456789",
            "changes": [{
                "value": {
                    "messaging_product": "whatsapp",
                    "metadata": {
                        "display_phone_number": "1234567890",
                        "phone_number_id": "123456789"
                    },
                    "contacts": [{
                        "profile": {"name": "Test User"},
                        "wa_id": "1234567890"
                    }],
                    "messages": [{
                        "from": "1234567890",
                        "id": "wamid.test123",
                        "timestamp": str(int(datetime.utcnow().timestamp())),
                        "text": {"body": "Hello, I need help"},
                        "type": "text"
                    }]
                },
                "field": "messages"
            }]
        }]
    }

# Agent fixtures
@pytest.fixture
def mock_agent_response():
    """Mock AI agent response"""
    return {
        "agent_id": "content_creator",
        "response": "Here's a suggested post: 'Discover the power of AI in marketing...'",
        "confidence": 0.92,
        "metadata": {
            "model": "gpt-4",
            "tokens_used": 150,
            "processing_time": 1.2
        }
    }

@pytest.fixture
def mock_multi_agent_result():
    """Mock multi-agent orchestration result"""
    return {
        "orchestrator_id": "main_orchestrator",
        "agents_used": ["content_creator", "validator", "scheduler"],
        "final_output": {
            "content": "AI-generated marketing post",
            "validation_passed": True,
            "scheduled_time": (datetime.utcnow() + timedelta(hours=2)).isoformat()
        },
        "execution_time": 3.5
    }

# Database fixtures
@pytest.fixture
def mock_db_session():
    """Mock database session"""
    from unittest.mock import AsyncMock
    session = AsyncMock()
    session.commit = AsyncMock()
    session.rollback = AsyncMock()
    session.close = AsyncMock()
    return session

# API Response fixtures
@pytest.fixture
def mock_linkedin_api_response():
    """Mock LinkedIn API response"""
    return {
        "id": "urn:li:share:123456789",
        "activity": "urn:li:activity:123456789",
        "created": {"time": int(datetime.utcnow().timestamp() * 1000)},
        "text": {"text": "Test post content"}
    }

@pytest.fixture
def mock_twitter_api_response():
    """Mock Twitter API response"""
    return {
        "data": {
            "id": "1234567890123456789",
            "text": "Test tweet content",
            "created_at": datetime.utcnow().isoformat()
        }
    }

@pytest.fixture
def mock_facebook_api_response():
    """Mock Facebook API response"""
    return {
        "id": "123456789_987654321",
        "created_time": datetime.utcnow().isoformat(),
        "message": "Test post content"
    }

# Error fixtures
@pytest.fixture
def mock_api_error_response():
    """Mock API error response"""
    return {
        "error": {
            "code": "rate_limit_exceeded",
            "message": "Rate limit exceeded. Please try again later.",
            "status": 429
        }
    }

@pytest.fixture
def mock_validation_error():
    """Mock validation error"""
    return {
        "detail": [
            {
                "loc": ["body", "content"],
                "msg": "field required",
                "type": "value_error.missing"
            }
        ]
    }
