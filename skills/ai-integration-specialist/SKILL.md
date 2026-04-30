---
name: ai-integration-specialist
description: "Expert in LLM integration (Claude/GPT), RAG systems for self-learning, and WhatsApp Business API for remote approval workflows. Use when: (1) Designing prompts for Claude or GPT models with system prompts and few-shot learning, (2) Implementing multi-agent orchestration with specialized agent prompts, (3) Setting up RAG systems with vector databases (Pinecone, ChromaDB, Weaviate), (4) Implementing document chunking, embedding generation, and retrieval strategies, (5) Building WhatsApp approval workflows with interactive messages and buttons, (6) Integrating feedback loops for continuous learning, (7) Optimizing LLM API calls with error handling and retries, (8) Creating message templates for WhatsApp Business API. Provides prompt templates, RAG implementation patterns, WhatsApp message templates, and comprehensive reference documentation."
---

# AI Integration Specialist

Expert guidance for LLM integration, RAG systems, and WhatsApp Business API workflows for intelligent marketing automation.

## Quick Start

### LLM Integration

#### Basic Claude API Call

```python
import anthropic
import os

client = anthropic.Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))

message = client.messages.create(
    model="claude-3-5-sonnet-20241022",
    max_tokens=1024,
    messages=[
        {"role": "user", "content": "Generate a LinkedIn post about AI in marketing"}
    ]
)

print(message.content[0].text)
```

#### Using Prompt Templates

```python
import json

# Load template
with open("assets/prompt-templates/content-generation.json") as f:
    template = json.load(f)

# Fill template
system_prompt = template["system_prompt"].replace("{{platform}}", "linkedin")
user_prompt = template["user_prompt"].replace("{{topic}}", "AI in marketing")

# Call LLM
response = client.messages.create(
    model="claude-3-5-sonnet-20241022",
    max_tokens=1024,
    system=system_prompt,
    messages=[{"role": "user", "content": user_prompt}]
)
```

### RAG System Setup

#### Quick ChromaDB Setup

```python
import chromadb
from sentence_transformers import SentenceTransformer

# Initialize
client = chromadb.Client()
collection = client.create_collection("marketing_knowledge")
embedder = SentenceTransformer("all-MiniLM-L6-v2")

# Add documents
documents = ["AI improves marketing ROI by 40%", "Social media engagement peaks at noon"]
embeddings = embedder.encode(documents).tolist()

collection.add(
    documents=documents,
    embeddings=embeddings,
    ids=["doc1", "doc2"]
)

# Query
query = "How does AI help marketing?"
query_embedding = embedder.encode([query]).tolist()
results = collection.query(query_embeddings=query_embedding, n_results=2)
```

### WhatsApp Approval Workflow

#### Send Approval Request

```python
from assets.whatsapp_templates import approval_messages
import json

# Load template
with open("assets/whatsapp-templates/approval-messages.json") as f:
    templates = json.load(f)

# Fill template
message = templates["approval_request"]
message["interactive"]["body"]["text"] = message["interactive"]["body"]["text"].replace(
    "{{platform}}", "LinkedIn"
).replace("{{request_id}}", "req_123").replace("{{content}}", "Your post content here")

# Send via WhatsApp API
await whatsapp_client.send_message(to="+1234567890", message=message)
```

## LLM Prompting

For comprehensive prompting patterns, best practices, and multi-agent orchestration, see [llm-prompting.md](references/llm-prompting.md).

### System Prompt Design

```python
system_prompt = """You are an expert social media content creator.

Your role:
1. Generate engaging, platform-appropriate content
2. Optimize for target audience engagement
3. Maintain brand voice consistency
4. Include clear calls-to-action

Guidelines:
- Be concise and impactful
- Use data-driven insights
- Follow platform best practices
- Prioritize authenticity

Output Format: JSON with content, hashtags, and CTA"""
```

### Few-Shot Learning

```python
few_shot_prompt = """Generate social media posts in this style:

Example 1:
Input: Product launch - AI writing tool
Output: "🚀 Excited to announce our new AI writing assistant!
Transform your content creation workflow with intelligent suggestions.
Try it free: [link] #AIWriting #ContentCreation"

Example 2:
Input: Company milestone - 10k users
Output: "🎉 We just hit 10,000 users! Thank you to our amazing community.
What feature should we build next? 👇 #Milestone #Startup"

Now generate:
Input: {your_input}
Output:"""
```

### Multi-Agent Orchestration

```python
# Orchestrator decides which agents to use
orchestrator_prompt = """Analyze this request and determine which specialist agents to invoke:

Request: {user_request}

Available Agents:
- ContentCreator: Generates social media posts
- Analyzer: Analyzes performance metrics
- Validator: Reviews content quality

Provide execution plan in JSON:
{
  "agents": ["agent1", "agent2"],
  "execution_mode": "sequential|parallel",
  "reasoning": "why these agents"
}"""
```

## RAG Systems

For complete RAG implementation patterns, vector database integration, and retrieval strategies, see [rag-systems.md](references/rag-systems.md).

### Document Processing

```python
def chunk_text_semantic(text: str, max_chunk_size: int = 512) -> list[str]:
    """Split text at semantic boundaries"""
    import re
    paragraphs = text.split('\n\n')
    chunks = []
    current_chunk = ""

    for para in paragraphs:
        sentences = re.split(r'(?<=[.!?])\s+', para)
        for sentence in sentences:
            if len(current_chunk) + len(sentence) <= max_chunk_size:
                current_chunk += sentence + " "
            else:
                if current_chunk:
                    chunks.append(current_chunk.strip())
                current_chunk = sentence + " "

    if current_chunk:
        chunks.append(current_chunk.strip())

    return chunks
```

### Embedding Generation

```python
from sentence_transformers import SentenceTransformer

embedder = SentenceTransformer("all-MiniLM-L6-v2")
embeddings = embedder.encode(["text1", "text2"])
```

### RAG Pipeline

```python
class RAGSystem:
    def __init__(self, vector_store, llm_client, embedder):
        self.vector_store = vector_store
        self.llm = llm_client
        self.embedder = embedder

    def generate(self, query: str, top_k: int = 5):
        # 1. Retrieve relevant documents
        query_embedding = self.embedder.encode([query])[0]
        docs = self.vector_store.query(query_embedding, top_k=top_k)

        # 2. Construct context
        context = "\n\n".join([doc.text for doc in docs])

        # 3. Generate with context
        prompt = f"Context:\n{context}\n\nQuestion: {query}\n\nAnswer:"
        return self.llm.generate(prompt)
```

### Feedback Loop Integration

```python
def update_knowledge_from_feedback(post_id: str, metrics: dict):
    """Update RAG knowledge base with performance data"""
    # Create learning document
    doc = f"""
    Platform: {metrics['platform']}
    Content: {metrics['content']}
    Engagement Rate: {metrics['engagement_rate']:.2%}
    Success Factors: Posted at {metrics['time']}, {metrics['content_type']} content
    """

    # Add to vector store with performance metadata
    vector_store.add(
        documents=[doc],
        metadatas=[{"performance_score": metrics['engagement_rate']}]
    )
```

## WhatsApp Business API

For complete WhatsApp integration patterns, webhook handling, and approval workflows, see [whatsapp-api.md](references/whatsapp-api.md).

### Client Setup

```python
import os
import httpx

class WhatsAppClient:
    def __init__(self):
        self.api_url = os.getenv("WHATSAPP_API_URL")
        self.phone_number_id = os.getenv("WHATSAPP_PHONE_NUMBER_ID")
        self.access_token = os.getenv("WHATSAPP_ACCESS_TOKEN")

    async def send_message(self, to: str, message: dict):
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{self.api_url}/{self.phone_number_id}/messages",
                headers={"Authorization": f"Bearer {self.access_token}"},
                json={"messaging_product": "whatsapp", "to": to, **message}
            )
            return response.json()
```

### Interactive Button Messages

```python
async def send_approval_request(client, to: str, content: str, request_id: str):
    message = {
        "type": "interactive",
        "interactive": {
            "type": "button",
            "body": {"text": f"Approve this content?\n\n{content}"},
            "action": {
                "buttons": [
                    {"type": "reply", "reply": {"id": f"approve_{request_id}", "title": "✅ Approve"}},
                    {"type": "reply", "reply": {"id": f"reject_{request_id}", "title": "❌ Reject"}}
                ]
            }
        }
    }
    return await client.send_message(to, message)
```

### Webhook Processing

```python
from fastapi import APIRouter, Request

router = APIRouter()

@router.post("/webhooks/whatsapp")
async def receive_webhook(request: Request):
    body = await request.json()

    for entry in body.get("entry", []):
        for change in entry.get("changes", []):
            if change.get("field") == "messages":
                messages = change["value"].get("messages", [])
                for message in messages:
                    if message["type"] == "interactive":
                        await process_approval_response(message)

    return {"status": "ok"}
```

## Prompt Templates

### Content Generation Template

Located at `assets/prompt-templates/content-generation.json`:

```python
import json

with open("assets/prompt-templates/content-generation.json") as f:
    template = json.load(f)

# Access components
system_prompt = template["system_prompt"]
user_prompt = template["user_prompt"]
examples = template["few_shot_examples"]
```

### Custom Template Creation

```python
def create_custom_prompt(
    platform: str,
    topic: str,
    target_audience: str,
    tone: str
) -> str:
    return f"""Generate a {platform} post about {topic}.

Target Audience: {target_audience}
Tone: {tone}

Requirements:
- Platform-appropriate length
- Engaging hook
- Clear call-to-action
- 2-3 relevant hashtags

Output as JSON with: content, hashtags, cta"""
```

## WhatsApp Message Templates

### Using Pre-built Templates

```python
import json

with open("assets/whatsapp-templates/approval-messages.json") as f:
    templates = json.load(f)

# Get specific template
approval_template = templates["approval_request"]
confirmation_template = templates["approval_confirmation"]
```

### Template Variables

Replace placeholders in templates:

```python
def fill_template(template: dict, variables: dict) -> dict:
    """Replace template variables"""
    import json
    template_str = json.dumps(template)

    for key, value in variables.items():
        template_str = template_str.replace(f"{{{{{key}}}}}", str(value))

    return json.loads(template_str)
```

## Error Handling

### LLM API Retries

```python
from tenacity import retry, stop_after_attempt, wait_exponential

@retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=4, max=10))
async def call_llm_with_retry(prompt: str):
    try:
        return await llm_client.generate(prompt)
    except Exception as e:
        print(f"LLM call failed: {e}")
        raise
```

### Fallback Strategy

```python
async def call_with_fallback(prompt: str):
    """Try Claude, fallback to GPT"""
    try:
        return await call_claude(prompt)
    except Exception:
        return await call_gpt(prompt)
```

## Best Practices

### LLM Integration

1. **Clear Instructions**: Be explicit about what you want
2. **Structured Output**: Request JSON for consistent parsing
3. **Few-Shot Examples**: Show the model what you want
4. **Error Handling**: Implement retries and fallbacks
5. **Cost Optimization**: Cache responses, optimize token usage

### RAG Systems

1. **Semantic Chunking**: Preserve context in chunks
2. **Rich Metadata**: Include performance data for filtering
3. **Hybrid Search**: Combine dense and sparse retrieval
4. **Continuous Learning**: Update knowledge base with feedback
5. **Evaluation**: Measure retrieval quality regularly

### WhatsApp Integration

1. **Template Pre-approval**: Get templates approved by Meta
2. **Session Management**: Use TTL for approval requests
3. **Idempotency**: Handle duplicate webhook deliveries
4. **Rate Limiting**: Implement retry logic
5. **User Experience**: Use emojis and clear formatting

## Integration Patterns

### Complete Approval Workflow

```python
async def approval_workflow(content: str, platform: str, approver_phone: str):
    # 1. Generate content with LLM
    generated = await llm_client.generate(f"Create {platform} post: {content}")

    # 2. Send approval request via WhatsApp
    request_id = f"req_{uuid.uuid4()}"
    await send_approval_request(whatsapp_client, approver_phone, generated, request_id)

    # 3. Wait for response (handled by webhook)
    # 4. On approval, publish and track
    # 5. Update RAG knowledge base with performance
```

### RAG-Enhanced Content Generation

```python
async def generate_with_rag(topic: str):
    # 1. Retrieve relevant past successful posts
    similar_posts = rag_system.retrieve(topic, top_k=3)

    # 2. Build context-aware prompt
    context = "\n".join([post.text for post in similar_posts])
    prompt = f"Based on these successful posts:\n{context}\n\nGenerate new post about: {topic}"

    # 3. Generate with LLM
    return await llm_client.generate(prompt)
```

## Monitoring

### Track LLM Usage

```python
class LLMMetrics:
    async def track_call(self, model: str, tokens: int, latency: float):
        await self.increment_counter(f"llm.calls.{model}")
        await self.record_histogram(f"llm.tokens.{model}", tokens)
        await self.record_histogram(f"llm.latency.{model}", latency)
```

### Track Approval Workflow

```python
class ApprovalMetrics:
    async def track_request(self, platform: str):
        await self.increment_counter(f"approvals.sent.{platform}")

    async def track_response(self, action: str, response_time: float):
        await self.increment_counter(f"approvals.{action}")
        await self.record_histogram("approvals.response_time", response_time)
```

## Reference Documentation

- **[llm-prompting.md](references/llm-prompting.md)** - Comprehensive LLM prompting patterns, few-shot learning, multi-agent orchestration, and optimization techniques
- **[rag-systems.md](references/rag-systems.md)** - Complete RAG implementation with vector databases, chunking strategies, retrieval patterns, and feedback loops
- **[whatsapp-api.md](references/whatsapp-api.md)** - WhatsApp Business API integration, approval workflows, interactive messages, and webhook handling

## When NOT to Use This Skill

- **Simple single-model chatbots without RAG** — if you just need a basic API call to Claude or GPT, the full integration patterns here are overkill
- **Real-time streaming applications with strict latency requirements** — RAG retrieval adds latency; profile first before adding vector search to the hot path
- **Environments where WhatsApp Business API access is unavailable** — the approval workflow patterns require verified WhatsApp Business accounts

## Common Mistakes

- Chunking documents without overlap — adjacent chunks lose contextual continuity and degrade retrieval quality
- Not implementing retry logic with exponential backoff for LLM API calls — transient rate-limit errors cause unnecessary failures
- Sending unapproved WhatsApp template messages — Meta's policy requires pre-approval for template messages; using custom messages without templates triggers account suspension

## Related Skills

- [`mcp-builder`](../mcp-builder/SKILL.md) — Build MCP servers to expose the LLM integrations built here
- [`whatsapp-watcher`](../whatsapp-watcher/SKILL.md) — Monitor and respond to WhatsApp messages in real time
- [`orchestrator-engine`](../orchestrator-engine/SKILL.md) — Orchestrate multi-agent LLM workflows
