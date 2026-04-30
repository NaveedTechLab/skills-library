# LLM Prompting Best Practices

## Overview

Comprehensive guide for effective prompt engineering with Claude (Anthropic) and GPT (OpenAI) models, covering system prompts, few-shot learning, and multi-agent orchestration.

## Prompt Engineering Fundamentals

### Core Principles

1. **Be Clear and Specific**: Ambiguity leads to unpredictable outputs
2. **Provide Context**: Give the model relevant background information
3. **Use Examples**: Show the model what you want (few-shot learning)
4. **Set Constraints**: Define boundaries and requirements explicitly
5. **Iterate**: Refine prompts based on outputs

### Prompt Structure

```
[System Context]
You are an expert marketing content creator...

[Task Description]
Create a LinkedIn post about...

[Constraints]
- Maximum 280 characters
- Professional tone
- Include 2-3 relevant hashtags

[Examples] (optional)
Example 1: ...
Example 2: ...

[Output Format]
Return JSON with: {content, hashtags, tone}
```

## Claude-Specific Patterns

### System Prompts for Claude

```xml
<system>
You are an expert social media marketing specialist with deep knowledge of LinkedIn, Twitter, and Facebook best practices.

Your role is to:
1. Analyze user requirements and target audience
2. Generate engaging, platform-appropriate content
3. Optimize for engagement metrics
4. Maintain brand voice consistency

Guidelines:
- Always consider platform-specific character limits
- Use data-driven insights when available
- Prioritize authenticity over clickbait
- Include clear calls-to-action

Output Format:
Provide responses in JSON format with clear structure.
</system>
```

### XML Tags for Structure

Claude responds well to XML-style tags:

```xml
<task>
Generate a LinkedIn post about AI in marketing
</task>

<context>
Target audience: Marketing professionals
Company: B2B SaaS startup
Tone: Professional but approachable
</context>

<constraints>
- 150-200 words
- Include 3 hashtags
- Add a question to drive engagement
</constraints>

<examples>
<example>
<input>Topic: Content marketing trends</input>
<output>
Content marketing in 2024 is all about authenticity...
#ContentMarketing #DigitalStrategy #MarketingTrends
</output>
</example>
</examples>
```

### Chain of Thought Prompting

Encourage step-by-step reasoning:

```
Analyze this social media campaign performance:
- Impressions: 50,000
- Engagement: 2,500
- Clicks: 500

Think through this step by step:
1. Calculate engagement rate
2. Calculate click-through rate
3. Compare to industry benchmarks
4. Identify strengths and weaknesses
5. Provide actionable recommendations

Show your reasoning for each step.
```

### Constitutional AI Principles

Claude is trained with constitutional AI. Leverage this:

```
Generate marketing content that:
- Is truthful and avoids misleading claims
- Respects user privacy and data protection
- Promotes inclusive and diverse perspectives
- Avoids manipulative or dark patterns
- Maintains ethical advertising standards
```

## GPT-Specific Patterns

### System Messages for GPT

```python
system_message = {
    "role": "system",
    "content": """You are a social media content expert specializing in B2B marketing.

Your expertise includes:
- LinkedIn thought leadership content
- Twitter engagement strategies
- Facebook community building
- Data-driven content optimization

Always provide:
1. Clear, actionable recommendations
2. Platform-specific best practices
3. Measurable success metrics
4. A/B testing suggestions

Format all outputs as structured JSON."""
}
```

### Function Calling

GPT models support function calling for structured outputs:

```python
functions = [
    {
        "name": "generate_social_post",
        "description": "Generate a social media post with metadata",
        "parameters": {
            "type": "object",
            "properties": {
                "content": {
                    "type": "string",
                    "description": "The post content"
                },
                "platform": {
                    "type": "string",
                    "enum": ["linkedin", "twitter", "facebook"]
                },
                "hashtags": {
                    "type": "array",
                    "items": {"type": "string"}
                },
                "tone": {
                    "type": "string",
                    "enum": ["professional", "casual", "inspirational"]
                }
            },
            "required": ["content", "platform"]
        }
    }
]
```

### Temperature and Top-P Settings

```python
# Creative content generation
response = openai.ChatCompletion.create(
    model="gpt-4",
    temperature=0.8,  # Higher for creativity
    top_p=0.9,
    messages=[...]
)

# Analytical tasks
response = openai.ChatCompletion.create(
    model="gpt-4",
    temperature=0.2,  # Lower for consistency
    top_p=0.95,
    messages=[...]
)
```

## Few-Shot Learning Patterns

### Basic Few-Shot

```
Generate social media posts in this style:

Example 1:
Input: Product launch - AI writing tool
Output: "🚀 Excited to announce our new AI writing assistant!
Transform your content creation workflow with intelligent suggestions
and real-time optimization. Try it free: [link]
#AIWriting #ContentCreation #ProductLaunch"

Example 2:
Input: Company milestone - 10k users
Output: "🎉 We just hit 10,000 users! Thank you to our amazing
community for believing in our vision. This is just the beginning.
What feature should we build next? 👇
#Milestone #Startup #Community"

Now generate:
Input: New feature - Analytics dashboard
Output:
```

### Dynamic Few-Shot Selection

Select examples based on similarity to the current task:

```python
def select_few_shot_examples(query, example_pool, n=3):
    """Select most relevant examples using embeddings"""
    query_embedding = get_embedding(query)

    similarities = []
    for example in example_pool:
        example_embedding = get_embedding(example['input'])
        similarity = cosine_similarity(query_embedding, example_embedding)
        similarities.append((similarity, example))

    # Return top N most similar examples
    top_examples = sorted(similarities, reverse=True)[:n]
    return [ex for _, ex in top_examples]
```

### Chain-of-Thought Few-Shot

```
Analyze social media performance with reasoning:

Example:
Post: "New blog post on AI trends"
Metrics: 1000 impressions, 50 likes, 10 comments, 5 shares
Analysis:
1. Engagement rate: (50+10+5)/1000 = 6.5% (above 3% benchmark ✓)
2. Comment ratio: 10/50 = 20% (high discussion quality ✓)
3. Share ratio: 5/50 = 10% (good viral potential ✓)
Conclusion: Strong performance, content resonates with audience

Now analyze:
Post: "Product update announcement"
Metrics: 5000 impressions, 100 likes, 5 comments, 2 shares
Analysis:
```

## Multi-Agent System Prompts

### Orchestrator Agent

```xml
<system>
You are the Orchestrator Agent responsible for coordinating multiple specialist agents to complete complex marketing tasks.

Your responsibilities:
1. Analyze incoming requests and break them into subtasks
2. Determine which specialist agents to invoke
3. Coordinate agent execution (parallel or sequential)
4. Aggregate results from multiple agents
5. Synthesize final output for the user

Available Specialist Agents:
- ContentCreator: Generates social media posts
- Analyzer: Analyzes performance metrics
- Scheduler: Determines optimal posting times
- Validator: Reviews content for quality and compliance

Decision Framework:
- For content generation: ContentCreator → Validator
- For performance analysis: Analyzer → ContentCreator (for improvements)
- For campaign planning: Analyzer → Scheduler → ContentCreator → Validator

Always explain your reasoning for agent selection and execution order.
</system>
```

### Content Creator Agent

```xml
<system>
You are the Content Creator Agent, specialized in generating high-quality social media content.

Expertise:
- Platform-specific content optimization (LinkedIn, Twitter, Facebook)
- Audience targeting and personalization
- Engagement-driven copywriting
- Brand voice consistency
- Hashtag strategy

Input Format:
{
  "topic": "string",
  "platform": "linkedin|twitter|facebook",
  "target_audience": "string",
  "tone": "professional|casual|inspirational",
  "constraints": {...}
}

Output Format:
{
  "content": "string",
  "hashtags": ["string"],
  "call_to_action": "string",
  "estimated_engagement": "low|medium|high",
  "reasoning": "string"
}

Quality Standards:
- Clear, concise messaging
- Platform-appropriate length
- Engaging hooks
- Actionable CTAs
- Relevant hashtags (2-5)
</system>
```

### Validator Agent

```xml
<system>
You are the Validator Agent, responsible for quality assurance of generated content.

Validation Criteria:
1. Brand Voice Consistency
   - Tone matches brand guidelines
   - Language is appropriate for target audience

2. Platform Compliance
   - Character limits respected
   - Format follows platform best practices
   - Hashtags are relevant and not excessive

3. Content Quality
   - Grammar and spelling are correct
   - Message is clear and compelling
   - CTA is present and actionable

4. Ethical Standards
   - No misleading claims
   - Respects privacy and data protection
   - Inclusive and respectful language

Output Format:
{
  "approved": boolean,
  "issues": [{"category": "string", "description": "string", "severity": "low|medium|high"}],
  "suggestions": ["string"],
  "confidence_score": 0.0-1.0
}

If approved=false, provide specific, actionable feedback for improvement.
</system>
```

## Prompt Optimization Techniques

### Iterative Refinement

```python
def optimize_prompt(base_prompt, test_cases, iterations=5):
    """Iteratively improve prompt based on test results"""
    current_prompt = base_prompt

    for i in range(iterations):
        results = []
        for test_case in test_cases:
            output = call_llm(current_prompt, test_case)
            score = evaluate_output(output, test_case['expected'])
            results.append((test_case, output, score))

        # Analyze failures
        failures = [r for r in results if r[2] < 0.8]

        if not failures:
            break

        # Refine prompt based on failures
        current_prompt = refine_prompt(current_prompt, failures)

    return current_prompt
```

### A/B Testing Prompts

```python
def ab_test_prompts(prompt_a, prompt_b, test_cases):
    """Compare two prompts on same test cases"""
    results_a = []
    results_b = []

    for test_case in test_cases:
        output_a = call_llm(prompt_a, test_case)
        output_b = call_llm(prompt_b, test_case)

        score_a = evaluate_output(output_a, test_case)
        score_b = evaluate_output(output_b, test_case)

        results_a.append(score_a)
        results_b.append(score_b)

    return {
        "prompt_a_avg": sum(results_a) / len(results_a),
        "prompt_b_avg": sum(results_b) / len(results_b),
        "winner": "A" if sum(results_a) > sum(results_b) else "B"
    }
```

## Error Handling and Retries

### Robust API Calls

```python
import anthropic
from tenacity import retry, stop_after_attempt, wait_exponential

@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=4, max=10)
)
def call_claude_with_retry(prompt, max_tokens=1024):
    """Call Claude API with automatic retries"""
    client = anthropic.Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))

    try:
        message = client.messages.create(
            model="claude-3-5-sonnet-20241022",
            max_tokens=max_tokens,
            messages=[{"role": "user", "content": prompt}]
        )
        return message.content[0].text
    except anthropic.RateLimitError:
        # Wait and retry
        raise
    except anthropic.APIError as e:
        # Log and retry
        print(f"API Error: {e}")
        raise
```

### Fallback Strategies

```python
def call_llm_with_fallback(prompt, primary="claude", fallback="gpt"):
    """Try primary LLM, fallback to secondary on failure"""
    try:
        if primary == "claude":
            return call_claude(prompt)
        else:
            return call_gpt(prompt)
    except Exception as e:
        print(f"Primary LLM failed: {e}. Trying fallback...")
        if fallback == "claude":
            return call_claude(prompt)
        else:
            return call_gpt(prompt)
```

## Cost Optimization

### Token Management

```python
def estimate_tokens(text):
    """Rough token estimation (1 token ≈ 4 characters)"""
    return len(text) // 4

def optimize_prompt_length(prompt, max_tokens=4000):
    """Truncate prompt if too long"""
    estimated = estimate_tokens(prompt)
    if estimated > max_tokens:
        # Keep system prompt, truncate examples
        return truncate_intelligently(prompt, max_tokens)
    return prompt
```

### Caching Strategies

```python
from functools import lru_cache
import hashlib

@lru_cache(maxsize=1000)
def cached_llm_call(prompt_hash, model):
    """Cache LLM responses for identical prompts"""
    # Actual LLM call
    return call_llm(prompt_hash, model)

def call_with_cache(prompt, model="claude"):
    prompt_hash = hashlib.md5(prompt.encode()).hexdigest()
    return cached_llm_call(prompt_hash, model)
```

## Best Practices Summary

1. **Clarity**: Be explicit about what you want
2. **Context**: Provide relevant background information
3. **Examples**: Use few-shot learning for consistency
4. **Structure**: Use XML tags or JSON for complex prompts
5. **Iteration**: Test and refine prompts systematically
6. **Error Handling**: Implement retries and fallbacks
7. **Cost Management**: Cache responses, optimize token usage
8. **Evaluation**: Measure prompt performance quantitatively
9. **Documentation**: Keep a library of effective prompts
10. **Ethics**: Ensure prompts align with ethical guidelines
