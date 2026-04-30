"""
Test templates for WhatsApp webhook and Self-Learning feedback loop
"""
import pytest
from unittest.mock import Mock, patch, AsyncMock
from httpx import AsyncClient
from fastapi import status
import json

# WhatsApp Webhook Tests
class TestWhatsAppWebhook:
    """Test suite for WhatsApp webhook integration"""

    @pytest.fixture
    def whatsapp_verification_request(self):
        """Mock WhatsApp webhook verification request"""
        return {
            "hub.mode": "subscribe",
            "hub.verify_token": "test_verify_token",
            "hub.challenge": "test_challenge_string"
        }

    @pytest.fixture
    def whatsapp_message_webhook(self):
        """Mock WhatsApp incoming message webhook"""
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
                            "timestamp": "1234567890",
                            "text": {"body": "Hello, I need help"},
                            "type": "text"
                        }]
                    },
                    "field": "messages"
                }]
            }]
        }

    @pytest.fixture
    def whatsapp_status_webhook(self):
        """Mock WhatsApp message status webhook"""
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
                        "statuses": [{
                            "id": "wamid.test123",
                            "status": "delivered",
                            "timestamp": "1234567890",
                            "recipient_id": "1234567890"
                        }]
                    },
                    "field": "messages"
                }]
            }]
        }

    @pytest.mark.asyncio
    async def test_webhook_verification(self, client: AsyncClient, whatsapp_verification_request):
        """Test WhatsApp webhook verification endpoint"""
        response = await client.get(
            "/api/v1/webhooks/whatsapp",
            params=whatsapp_verification_request
        )

        assert response.status_code == status.HTTP_200_OK
        assert response.text == whatsapp_verification_request["hub.challenge"]

    @pytest.mark.asyncio
    async def test_webhook_verification_invalid_token(self, client: AsyncClient):
        """Test webhook verification with invalid token"""
        response = await client.get(
            "/api/v1/webhooks/whatsapp",
            params={
                "hub.mode": "subscribe",
                "hub.verify_token": "invalid_token",
                "hub.challenge": "test_challenge"
            }
        )

        assert response.status_code == status.HTTP_403_FORBIDDEN

    @pytest.mark.asyncio
    async def test_webhook_receive_message(self, client: AsyncClient, whatsapp_message_webhook):
        """Test receiving WhatsApp message via webhook"""
        with patch("app.services.whatsapp.WhatsAppService.process_message") as mock_process:
            mock_process.return_value = {"status": "processed"}

            response = await client.post(
                "/api/v1/webhooks/whatsapp",
                json=whatsapp_message_webhook
            )

            assert response.status_code == status.HTTP_200_OK
            mock_process.assert_called_once()

    @pytest.mark.asyncio
    async def test_webhook_receive_status_update(self, client: AsyncClient, whatsapp_status_webhook):
        """Test receiving WhatsApp status update via webhook"""
        with patch("app.services.whatsapp.WhatsAppService.process_status") as mock_process:
            mock_process.return_value = {"status": "updated"}

            response = await client.post(
                "/api/v1/webhooks/whatsapp",
                json=whatsapp_status_webhook
            )

            assert response.status_code == status.HTTP_200_OK
            mock_process.assert_called_once()

    @pytest.mark.asyncio
    async def test_webhook_malformed_payload(self, client: AsyncClient):
        """Test webhook with malformed payload"""
        response = await client.post(
            "/api/v1/webhooks/whatsapp",
            json={"invalid": "payload"}
        )

        assert response.status_code == status.HTTP_400_BAD_REQUEST

    @pytest.mark.asyncio
    async def test_webhook_idempotency(self, client: AsyncClient, whatsapp_message_webhook):
        """Test webhook idempotency - duplicate messages should be handled"""
        with patch("app.services.whatsapp.WhatsAppService.process_message") as mock_process:
            mock_process.return_value = {"status": "processed"}

            # Send same message twice
            response1 = await client.post(
                "/api/v1/webhooks/whatsapp",
                json=whatsapp_message_webhook
            )
            response2 = await client.post(
                "/api/v1/webhooks/whatsapp",
                json=whatsapp_message_webhook
            )

            assert response1.status_code == status.HTTP_200_OK
            assert response2.status_code == status.HTTP_200_OK
            # Should only process once
            assert mock_process.call_count == 1

    @pytest.mark.asyncio
    async def test_webhook_reliability_retry(self, client: AsyncClient, whatsapp_message_webhook):
        """Test webhook reliability with retry mechanism"""
        with patch("app.services.whatsapp.WhatsAppService.process_message") as mock_process:
            # Simulate failure then success
            mock_process.side_effect = [Exception("Temporary failure"), {"status": "processed"}]

            response = await client.post(
                "/api/v1/webhooks/whatsapp",
                json=whatsapp_message_webhook
            )

            # Should retry and eventually succeed
            assert response.status_code == status.HTTP_200_OK


# Self-Learning Feedback Loop Tests
class TestFeedbackLoop:
    """Test suite for Self-Learning feedback loop mechanism"""

    @pytest.fixture
    def feedback_data(self):
        """Mock feedback data"""
        return {
            "post_id": "post_123",
            "platform": "linkedin",
            "metrics": {
                "likes": 150,
                "comments": 25,
                "shares": 10,
                "impressions": 5000,
                "engagement_rate": 0.037
            },
            "content": "Test post content",
            "timestamp": "2024-01-01T12:00:00Z"
        }

    @pytest.fixture
    def learning_context(self):
        """Mock learning context"""
        return {
            "user_id": "user_123",
            "industry": "technology",
            "target_audience": "developers",
            "posting_time": "12:00",
            "content_type": "educational"
        }

    @pytest.mark.asyncio
    async def test_feedback_collection(self, client: AsyncClient, feedback_data):
        """Test collecting feedback from social media posts"""
        response = await client.post(
            "/api/v1/feedback/collect",
            json=feedback_data,
            headers={"Authorization": "Bearer test_token"}
        )

        assert response.status_code == status.HTTP_201_CREATED
        data = response.json()
        assert data["post_id"] == feedback_data["post_id"]
        assert "feedback_id" in data

    @pytest.mark.asyncio
    async def test_feedback_analysis(self, client: AsyncClient, feedback_data):
        """Test analyzing feedback data"""
        with patch("app.services.learning.LearningService.analyze_feedback") as mock_analyze:
            mock_analyze.return_value = {
                "performance_score": 0.85,
                "insights": ["High engagement rate", "Posted at optimal time"],
                "recommendations": ["Similar content performs well"]
            }

            response = await client.post(
                "/api/v1/feedback/analyze",
                json={"feedback_id": "feedback_123"},
                headers={"Authorization": "Bearer test_token"}
            )

            assert response.status_code == status.HTTP_200_OK
            data = response.json()
            assert "performance_score" in data
            assert "insights" in data

    @pytest.mark.asyncio
    async def test_learning_model_update(self, client: AsyncClient, feedback_data, learning_context):
        """Test updating learning model with new feedback"""
        with patch("app.services.learning.LearningService.update_model") as mock_update:
            mock_update.return_value = {
                "model_version": "v1.2.0",
                "updated_at": "2024-01-01T12:00:00Z",
                "improvement": 0.05
            }

            response = await client.post(
                "/api/v1/learning/update",
                json={
                    "feedback": feedback_data,
                    "context": learning_context
                },
                headers={"Authorization": "Bearer test_token"}
            )

            assert response.status_code == status.HTTP_200_OK
            data = response.json()
            assert "model_version" in data

    @pytest.mark.asyncio
    async def test_feedback_loop_integration(self, client: AsyncClient, feedback_data):
        """Test complete feedback loop integration"""
        # 1. Collect feedback
        collect_response = await client.post(
            "/api/v1/feedback/collect",
            json=feedback_data,
            headers={"Authorization": "Bearer test_token"}
        )
        assert collect_response.status_code == status.HTTP_201_CREATED
        feedback_id = collect_response.json()["feedback_id"]

        # 2. Analyze feedback
        with patch("app.services.learning.LearningService.analyze_feedback") as mock_analyze:
            mock_analyze.return_value = {"performance_score": 0.85}

            analyze_response = await client.post(
                "/api/v1/feedback/analyze",
                json={"feedback_id": feedback_id},
                headers={"Authorization": "Bearer test_token"}
            )
            assert analyze_response.status_code == status.HTTP_200_OK

        # 3. Update learning model
        with patch("app.services.learning.LearningService.update_model") as mock_update:
            mock_update.return_value = {"model_version": "v1.2.0"}

            update_response = await client.post(
                "/api/v1/learning/update",
                json={"feedback_id": feedback_id},
                headers={"Authorization": "Bearer test_token"}
            )
            assert update_response.status_code == status.HTTP_200_OK

    @pytest.mark.asyncio
    async def test_feedback_aggregation(self, client: AsyncClient):
        """Test aggregating feedback across multiple posts"""
        with patch("app.services.learning.LearningService.aggregate_feedback") as mock_aggregate:
            mock_aggregate.return_value = {
                "total_posts": 50,
                "average_engagement": 0.042,
                "best_performing_time": "12:00",
                "best_performing_type": "educational"
            }

            response = await client.get(
                "/api/v1/feedback/aggregate",
                params={"user_id": "user_123", "days": 30},
                headers={"Authorization": "Bearer test_token"}
            )

            assert response.status_code == status.HTTP_200_OK
            data = response.json()
            assert "average_engagement" in data

    @pytest.mark.asyncio
    async def test_feedback_recommendations(self, client: AsyncClient, learning_context):
        """Test generating recommendations based on feedback"""
        with patch("app.services.learning.LearningService.generate_recommendations") as mock_recommend:
            mock_recommend.return_value = {
                "recommendations": [
                    "Post between 11 AM - 1 PM for best engagement",
                    "Educational content performs 30% better",
                    "Include code snippets for developer audience"
                ],
                "confidence": 0.87
            }

            response = await client.post(
                "/api/v1/learning/recommendations",
                json=learning_context,
                headers={"Authorization": "Bearer test_token"}
            )

            assert response.status_code == status.HTTP_200_OK
            data = response.json()
            assert len(data["recommendations"]) > 0

    @pytest.mark.asyncio
    async def test_feedback_loop_error_handling(self, client: AsyncClient, feedback_data):
        """Test feedback loop error handling"""
        with patch("app.services.learning.LearningService.analyze_feedback") as mock_analyze:
            mock_analyze.side_effect = Exception("Analysis failed")

            response = await client.post(
                "/api/v1/feedback/analyze",
                json={"feedback_id": "feedback_123"},
                headers={"Authorization": "Bearer test_token"}
            )

            # Should handle error gracefully
            assert response.status_code in [status.HTTP_500_INTERNAL_SERVER_ERROR, status.HTTP_503_SERVICE_UNAVAILABLE]
