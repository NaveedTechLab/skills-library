#!/usr/bin/env python3
"""
Claude Integration Generator
Generates Claude Agent SDK integration patterns with fallback mechanisms
"""

import os
import sys
import argparse
import json
from pathlib import Path
from typing import Dict, Any, List

def create_claude_client_wrapper() -> str:
    """Generate Claude client wrapper with error handling"""
    return '''from anthropic import Anthropic
from typing import List, Dict, Any, Optional
import logging
import json
import time
from enum import Enum

logger = logging.getLogger(__name__)

class ClaudeIntegrationError(Exception):
    """Custom exception for Claude integration errors"""
    pass

class ClaudeModel(Enum):
    SONNET = "claude-3-sonnet-20240229"
    OPUS = "claude-3-opus-20240229"
    HAiku = "claude-3-haiku-20240307"

class ClaudeClient:
    """
    Wrapper around Claude API client with enhanced error handling and fallbacks
    """

    def __init__(self, api_key: str, default_model: ClaudeModel = ClaudeModel.SONNET):
        self.client = Anthropic(api_key=api_key)
        self.default_model = default_model.value
        self.logger = logging.getLogger(__name__)

    def generate_response(
        self,
        messages: List[Dict[str, str]],
        model: Optional[str] = None,
        max_tokens: int = 1000,
        temperature: float = 0.7,
        system_prompt: Optional[str] = None,
        response_format: Optional[str] = None
    ) -> str:
        """
        Generate response using Claude with comprehensive error handling
        """
        model = model or self.default_model

        try:
            # Prepare the request
            request_params = {
                "model": model,
                "max_tokens": max_tokens,
                "temperature": temperature,
                "messages": messages
            }

            if system_prompt:
                request_params["system"] = system_prompt

            # Make the API call
            response = self.client.messages.create(**request_params)

            # Extract the content
            if response.content and len(response.content) > 0:
                return response.content[0].text
            else:
                raise ClaudeIntegrationError("Empty response from Claude API")

        except Exception as e:
            self.logger.error(f"Claude API error: {e}")
            raise ClaudeIntegrationError(f"Claude API error: {str(e)}")

    def generate_structured_response(
        self,
        prompt: str,
        response_schema: Dict[str, Any],
        system_prompt: Optional[str] = None,
        model: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Generate structured response following a specific schema
        """
        model = model or self.default_model

        # Include schema in the prompt to guide Claude
        schema_str = json.dumps(response_schema, indent=2)
        structured_prompt = f"""
Respond in valid JSON format following this schema:
{schema_str}

Content: {prompt}

Return ONLY the JSON response, no additional text.
"""

        messages = [{"role": "user", "content": structured_prompt}]

        try:
            response = self.generate_response(
                messages=messages,
                system_prompt=system_prompt,
                model=model,
                temperature=0.3  # Lower temperature for more consistent structure
            )

            # Parse and validate the response
            return self._parse_and_validate_json(response, response_schema)

        except ClaudeIntegrationError:
            raise
        except Exception as e:
            self.logger.error(f"Error processing structured response: {e}")
            raise ClaudeIntegrationError(f"Error processing structured response: {str(e)}")

    def _parse_and_validate_json(self, response: str, expected_schema: Dict[str, Any]) -> Dict[str, Any]:
        """
        Parse Claude's response and validate against expected schema
        """
        try:
            # Try to extract JSON from response if surrounded by text
            import re
            json_match = re.search(r'```(?:json)?\s*({.*?})\s*```', response, re.DOTALL)
            if json_match:
                data = json.loads(json_match.group(1))
            else:
                # Try parsing entire response
                data = json.loads(response)

            # Validate against schema structure
            self._validate_against_schema(data, expected_schema)

            return data

        except json.JSONDecodeError as e:
            self.logger.error(f"Invalid JSON in Claude response: {e}")
            self.logger.debug(f"Raw response: {response}")
            raise ClaudeIntegrationError(f"Invalid JSON in Claude response: {str(e)}")
        except ValueError as e:
            self.logger.error(f"Schema validation error: {e}")
            raise ClaudeIntegrationError(f"Schema validation error: {str(e)}")

    def _validate_against_schema(self, data: Dict[str, Any], schema: Dict[str, Any]):
        """
        Basic schema validation
        """
        required_keys = schema.get('required', [])
        for key in required_keys:
            if key not in data:
                raise ValueError(f"Missing required key: {key}")

        # Type validation
        properties = schema.get('properties', {})
        for key, value in data.items():
            if key in properties and 'type' in properties[key]:
                expected_type = properties[key]['type']

                if expected_type == 'string' and not isinstance(value, str):
                    raise ValueError(f"Expected string for {key}, got {type(value).__name__}")
                elif expected_type == 'number' and not isinstance(value, (int, float)):
                    raise ValueError(f"Expected number for {key}, got {type(value).__name__}")
                elif expected_type == 'boolean' and not isinstance(value, bool):
                    raise ValueError(f"Expected boolean for {key}, got {type(value).__name__}")
                elif expected_type == 'array' and not isinstance(value, list):
                    raise ValueError(f"Expected array for {key}, got {type(value).__name__}")
                elif expected_type == 'object' and not isinstance(value, dict):
                    raise ValueError(f"Expected object for {key}, got {type(value).__name__}")

    def health_check(self) -> bool:
        """
        Check if Claude API is accessible
        """
        try:
            test_messages = [{"role": "user", "content": "Say 'health check'"}]
            response = self.generate_response(
                messages=test_messages,
                max_tokens=10,
                temperature=0.1
            )
            return "health check" in response.lower()
        except Exception as e:
            self.logger.error(f"Claude health check failed: {e}")
            return False
'''


def create_circuit_breaker() -> str:
    """Generate circuit breaker for Claude API calls"""
    return '''import time
from enum import Enum
from typing import Callable, Any
import logging

logger = logging.getLogger(__name__)

class CircuitState(Enum):
    CLOSED = "closed"      # Normal operation
    OPEN = "open"          # Service temporarily unavailable
    HALF_OPEN = "half_open" # Testing if service is restored

class ClaudeCircuitBreaker:
    """
    Circuit breaker specifically for Claude API calls
    Prevents cascading failures when Claude service is unavailable
    """

    def __init__(self, failure_threshold: int = 3, timeout: int = 60):
        self.failure_threshold = failure_threshold
        self.timeout = timeout
        self.failure_count = 0
        self.last_failure_time = None
        self.state = CircuitState.CLOSED
        self.logger = logging.getLogger(__name__)

    def call(self, func: Callable, *args, **kwargs) -> Any:
        """
        Call Claude function with circuit breaker protection
        """
        if self.state == CircuitState.OPEN:
            # Check if timeout has passed to move to half-open state
            if self.last_failure_time and (time.time() - self.last_failure_time > self.timeout):
                self.logger.info("Circuit breaker transitioning to HALF_OPEN state")
                self.state = CircuitState.HALF_OPEN
            else:
                self.logger.warning("Circuit breaker is OPEN - Claude service unavailable")
                raise ClaudeCircuitBreakerOpenError("Claude service is temporarily unavailable")

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
        if self.state == CircuitState.HALF_OPEN:
            self.logger.info("Claude service restored - circuit breaker closed")

    def _on_failure(self):
        """
        Called when Claude call fails
        """
        self.failure_count += 1
        self.last_failure_time = time.time()

        if self.failure_count >= self.failure_threshold:
            self.state = CircuitState.OPEN
            self.logger.error(f"Circuit breaker OPENED after {self.failure_threshold} failures")

    def force_close(self):
        """
        Force circuit breaker to closed state
        """
        self.failure_count = 0
        self.state = CircuitState.CLOSED
        self.logger.info("Circuit breaker forced to CLOSED state")

    def get_state_info(self) -> dict:
        """
        Get current state information
        """
        return {
            "state": self.state.value,
            "failure_count": self.failure_count,
            "failure_threshold": self.failure_threshold,
            "last_failure_time": self.last_failure_time,
            "time_until_reset": (time.time() - self.last_failure_time + self.timeout) if self.last_failure_time else 0
        }

class ClaudeCircuitBreakerOpenError(Exception):
    """Raised when circuit breaker is open and Claude service is unavailable"""
    pass
'''


def create_fallback_handler() -> str:
    """Generate fallback handler for Claude integration"""
    return '''import re
from typing import Dict, Any, List, Optional
import logging

logger = logging.getLogger(__name__)

class ClaudeFallbackHandler:
    """
    Fallback handler for when Claude API is unavailable
    Provides deterministic alternatives to AI-powered features
    """

    def __init__(self):
        self.logger = logging.getLogger(__name__)

    def fallback_content_generation(self, prompt: str, content_type: str = "text") -> str:
        """
        Fallback for content generation
        """
        self.logger.warning("Using fallback for content generation")

        if content_type == "list":
            # Simple keyword-based list generation
            keywords = re.findall(r'\\w+', prompt.lower())
            return "\\n- ".join(keywords[:5]) if keywords else "No relevant keywords found"
        else:
            # Simple text summarization using keyword extraction
            sentences = prompt.split('.')
            return sentences[0][:200] + "..." if len(sentences) > 0 else prompt[:200]

    def fallback_analysis(self, text: str, analysis_type: str = "sentiment") -> Dict[str, Any]:
        """
        Fallback for text analysis
        """
        self.logger.warning("Using fallback for text analysis")

        if analysis_type == "sentiment":
            # Simple keyword-based sentiment analysis
            positive_words = ["good", "great", "excellent", "positive", "happy", "love", "like"]
            negative_words = ["bad", "terrible", "awful", "negative", "sad", "hate", "dislike"]

            text_lower = text.lower()
            pos_count = sum(1 for word in positive_words if word in text_lower)
            neg_count = sum(1 for word in negative_words if word in text_lower)

            if pos_count > neg_count:
                sentiment = "positive"
                score = min(pos_count, 1.0)
            elif neg_count > pos_count:
                sentiment = "negative"
                score = min(neg_count, 1.0)
            else:
                sentiment = "neutral"
                score = 0.5

            return {
                "sentiment": sentiment,
                "score": score,
                "confidence": "low",
                "method": "keyword_matching"
            }
        else:
            return {
                "analysis": "Analysis unavailable",
                "confidence": "low",
                "method": "fallback"
            }

    def fallback_qa(self, question: str, context: str) -> str:
        """
        Fallback for question answering
        """
        self.logger.warning("Using fallback for question answering")

        # Simple keyword matching approach
        question_keywords = set(re.findall(r'\\w+', question.lower()))
        context_sentences = context.split('.')

        best_sentence = ""
        best_match_count = 0

        for sentence in context_sentences:
            sentence_lower = sentence.lower()
            match_count = sum(1 for keyword in question_keywords if keyword in sentence_lower)

            if match_count > best_match_count:
                best_match_count = match_count
                best_sentence = sentence.strip()

        return best_sentence or "Unable to find relevant answer in context."

    def fallback_summarization(self, text: str, max_length: int = 100) -> str:
        """
        Fallback for text summarization
        """
        self.logger.warning("Using fallback for text summarization")

        # Simple approach: extract first few sentences
        sentences = text.split('.')

        summary = ""
        for sentence in sentences:
            if len(summary) + len(sentence) < max_length:
                summary += sentence.strip() + ". "
            else:
                break

        return summary.strip() or text[:max_length] + "..."

    def fallback_classification(self, text: str, categories: List[str]) -> str:
        """
        Fallback for text classification
        """
        self.logger.warning("Using fallback for text classification")

        # Simple keyword matching to categories
        text_lower = text.lower()
        scores = {}

        for category in categories:
            category_keywords = category.lower().split()
            score = sum(1 for keyword in category_keywords if keyword in text_lower)
            scores[category] = score

        # Return category with highest score
        if scores:
            return max(scores, key=scores.get)
        else:
            return categories[0] if categories else "unknown"
'''


def create_hybrid_service_pattern() -> str:
    """Generate hybrid service pattern combining Claude and fallbacks"""
    return '''from typing import Dict, Any, Optional, List
import logging
from .claude_client import ClaudeClient, ClaudeCircuitBreaker, ClaudeCircuitBreakerOpenError
from .fallback_handler import ClaudeFallbackHandler

logger = logging.getLogger(__name__)

class HybridClaudeService:
    """
    Hybrid service that uses Claude when available and falls back to deterministic methods
    """

    def __init__(self, claude_client: ClaudeClient, fallback_handler: Optional[ClaudeFallbackHandler] = None):
        self.claude_client = claude_client
        self.fallback_handler = fallback_handler or ClaudeFallbackHandler()
        self.circuit_breaker = ClaudeCircuitBreaker()
        self.logger = logging.getLogger(__name__)

    def generate_content_with_fallback(
        self,
        prompt: str,
        content_type: str = "text",
        use_fallback_if_unavailable: bool = True
    ) -> Dict[str, Any]:
        """
        Generate content with fallback to deterministic method
        """
        if use_fallback_if_unavailable:
            try:
                # Try Claude first
                result = self.circuit_breaker.call(
                    self.claude_client.generate_response,
                    messages=[{"role": "user", "content": prompt}],
                    max_tokens=500
                )

                return {
                    "content": result,
                    "method": "claude",
                    "success": True
                }
            except ClaudeCircuitBreakerOpenError:
                # Claude is unavailable, use fallback
                fallback_result = self.fallback_handler.fallback_content_generation(prompt, content_type)
                return {
                    "content": fallback_result,
                    "method": "fallback",
                    "success": True,
                    "fallback_reason": "circuit_breaker_open"
                }
            except Exception as e:
                # Claude failed, use fallback
                self.logger.warning(f"Claude generation failed: {e}, using fallback")
                fallback_result = self.fallback_handler.fallback_content_generation(prompt, content_type)
                return {
                    "content": fallback_result,
                    "method": "fallback",
                    "success": True,
                    "fallback_reason": str(e)
                }
        else:
            # Don't use fallback, raise exception if Claude fails
            result = self.claude_client.generate_response(
                messages=[{"role": "user", "content": prompt}],
                max_tokens=500
            )

            return {
                "content": result,
                "method": "claude",
                "success": True
            }

    def analyze_with_fallback(
        self,
        text: str,
        analysis_type: str = "sentiment",
        use_fallback_if_unavailable: bool = True
    ) -> Dict[str, Any]:
        """
        Analyze text with fallback to deterministic method
        """
        if use_fallback_if_unavailable:
            try:
                # Use Claude for analysis
                prompt = f"Analyze the following text for {analysis_type}:\\n\\n{text}"
                result = self.circuit_breaker.call(
                    self.claude_client.generate_structured_response,
                    prompt=prompt,
                    response_schema={
                        "type": "object",
                        "properties": {
                            "analysis": {"type": "string"},
                            "score": {"type": "number"},
                            "confidence": {"type": "string"}
                        }
                    }
                )

                return {
                    **result,
                    "method": "claude",
                    "success": True
                }
            except ClaudeCircuitBreakerOpenError:
                # Claude is unavailable, use fallback
                fallback_result = self.fallback_handler.fallback_analysis(text, analysis_type)
                return {
                    **fallback_result,
                    "method": "fallback",
                    "success": True,
                    "fallback_reason": "circuit_breaker_open"
                }
            except Exception as e:
                # Claude failed, use fallback
                self.logger.warning(f"Claude analysis failed: {e}, using fallback")
                fallback_result = self.fallback_handler.fallback_analysis(text, analysis_type)
                return {
                    **fallback_result,
                    "method": "fallback",
                    "success": True,
                    "fallback_reason": str(e)
                }
        else:
            # Don't use fallback, raise exception if Claude fails
            prompt = f"Analyze the following text for {analysis_type}:\\n\\n{text}"
            result = self.claude_client.generate_structured_response(
                prompt=prompt,
                response_schema={
                    "type": "object",
                    "properties": {
                        "analysis": {"type": "string"},
                        "score": {"type": "number"},
                        "confidence": {"type": "string"}
                    }
                }
            )

            return {
                **result,
                "method": "claude",
                "success": True
            }

    def qa_with_fallback(
        self,
        question: str,
        context: str,
        use_fallback_if_unavailable: bool = True
    ) -> Dict[str, Any]:
        """
        Question answering with fallback to deterministic method
        """
        if use_fallback_if_unavailable:
            try:
                # Use Claude for QA
                prompt = f"Based on the following context, answer the question:\\n\\nContext: {context}\\n\\nQuestion: {question}"
                result = self.circuit_breaker.call(
                    self.claude_client.generate_response,
                    messages=[{"role": "user", "content": prompt}],
                    max_tokens=300
                )

                return {
                    "answer": result,
                    "method": "claude",
                    "success": True
                }
            except ClaudeCircuitBreakerOpenError:
                # Claude is unavailable, use fallback
                fallback_result = self.fallback_handler.fallback_qa(question, context)
                return {
                    "answer": fallback_result,
                    "method": "fallback",
                    "success": True,
                    "fallback_reason": "circuit_breaker_open"
                }
            except Exception as e:
                # Claude failed, use fallback
                self.logger.warning(f"Claude QA failed: {e}, using fallback")
                fallback_result = self.fallback_handler.fallback_qa(question, context)
                return {
                    "answer": fallback_result,
                    "method": "fallback",
                    "success": True,
                    "fallback_reason": str(e)
                }
        else:
            # Don't use fallback, raise exception if Claude fails
            prompt = f"Based on the following context, answer the question:\\n\\nContext: {context}\\n\\nQuestion: {question}"
            result = self.claude_client.generate_response(
                messages=[{"role": "user", "content": prompt}],
                max_tokens=300
            )

            return {
                "answer": result,
                "method": "claude",
                "success": True
            }

    def health_check(self) -> Dict[str, Any]:
        """
        Check health of both Claude and fallback systems
        """
        claude_healthy = self.claude_client.health_check()
        circuit_state = self.circuit_breaker.get_state_info()

        return {
            "claude_healthy": claude_healthy,
            "circuit_breaker": circuit_state,
            "fallback_available": True,
            "overall_status": "healthy" if claude_healthy or circuit_state["state"] != "OPEN" else "degraded"
        }
'''


def create_example_integration() -> str:
    """Generate example integration code"""
    return '''"""
Example integration of Claude Agent SDK with fallback mechanisms
"""

from claude_client import ClaudeClient, ClaudeModel
from circuit_breaker import ClaudeCircuitBreaker
from fallback_handler import ClaudeFallbackHandler
from hybrid_service import HybridClaudeService

def main():
    # Initialize Claude client
    claude_client = ClaudeClient(
        api_key="your-anthropic-api-key",
        default_model=ClaudeModel.SONNET
    )

    # Initialize fallback handler
    fallback_handler = ClaudeFallbackHandler()

    # Create hybrid service
    hybrid_service = HybridClaudeService(claude_client, fallback_handler)

    # Example: Content generation
    print("=== Content Generation Example ===")
    content_result = hybrid_service.generate_content_with_fallback(
        prompt="Explain quantum computing in simple terms",
        content_type="explanation"
    )
    print(f"Method used: {content_result['method']}")
    print(f"Content: {content_result['content'][:100]}...")
    print()

    # Example: Text analysis
    print("=== Text Analysis Example ===")
    analysis_result = hybrid_service.analyze_with_fallback(
        text="This product is amazing! I love how it works.",
        analysis_type="sentiment"
    )
    print(f"Method used: {analysis_result['method']}")
    print(f"Analysis: {analysis_result}")
    print()

    # Example: Question answering
    print("=== Question Answering Example ===")
    qa_result = hybrid_service.qa_with_fallback(
        question="What is the capital of France?",
        context="France is a country in Europe. Its capital is Paris."
    )
    print(f"Method used: {qa_result['method']}")
    print(f"Answer: {qa_result['answer']}")
    print()

    # Check health
    print("=== Health Check ===")
    health = hybrid_service.health_check()
    print(f"Health status: {health}")

if __name__ == "__main__":
    main()
'''


def main():
    parser = argparse.ArgumentParser(description='Generate Claude Agent SDK integration patterns')
    parser.add_argument('--output-dir', default='./generated', help='Output directory for generated files')

    args = parser.parse_args()

    # Create output directory
    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    print(f"Generating Claude integration patterns...")
    print(f"Output directory: {output_dir}")

    # Generate Claude client wrapper
    client_code = create_claude_client_wrapper()
    client_file = output_dir / "claude_client.py"
    with open(client_file, 'w') as f:
        f.write(client_code)
    print(f"✓ Created Claude client: {client_file}")

    # Generate circuit breaker
    circuit_code = create_circuit_breaker()
    circuit_file = output_dir / "circuit_breaker.py"
    with open(circuit_file, 'w') as f:
        f.write(circuit_code)
    print(f"✓ Created circuit breaker: {circuit_file}")

    # Generate fallback handler
    fallback_code = create_fallback_handler()
    fallback_file = output_dir / "fallback_handler.py"
    with open(fallback_file, 'w') as f:
        f.write(fallback_code)
    print(f"✓ Created fallback handler: {fallback_file}")

    # Generate hybrid service pattern
    hybrid_code = create_hybrid_service_pattern()
    hybrid_file = output_dir / "hybrid_service.py"
    with open(hybrid_file, 'w') as f:
        f.write(hybrid_code)
    print(f"✓ Created hybrid service: {hybrid_file}")

    # Generate example integration
    example_code = create_example_integration()
    example_file = output_dir / "example_integration.py"
    with open(example_file, 'w') as f:
        f.write(example_code)
    print(f"✓ Created example integration: {example_file}")

    print(f"\n🎉 Generation complete! Files created in {output_dir}/")
    print(f"Files created:")
    print(f"  - {client_file.name} (Claude client wrapper)")
    print(f"  - {circuit_file.name} (Circuit breaker for Claude API)")
    print(f"  - {fallback_file.name} (Fallback handlers for deterministic alternatives)")
    print(f"  - {hybrid_file.name} (Hybrid service combining Claude and fallbacks)")
    print(f"  - {example_file.name} (Example integration code)")

    print(f"\nTo use these files:")
    print(f"  1. Install the Anthropic Python SDK: pip install anthropic")
    print(f"  2. Set your ANTHROPIC_API_KEY environment variable")
    print(f"  3. Review and customize the generated code for your use case")
    print(f"  4. Integrate the hybrid service into your application")


if __name__ == "__main__":
    main()