# Zero-Backend-LLM Remediation Templates

## Common Violation Patterns and Fixes

### 1. OpenAI API Call Replacement

#### Pattern A: Chat Completion API
```python
# BEFORE (Violation)
import openai

def generate_response(prompt):
    response = openai.ChatCompletion.create(
        model="gpt-3.5-turbo",
        messages=[{"role": "user", "content": prompt}],
        max_tokens=150
    )
    return response.choices[0].message.content

# AFTER (Compliant)
def generate_response(prompt):
    """
    Generate response using deterministic business logic
    """
    prompt_lower = prompt.lower()

    # Greeting responses
    if any(greeting in prompt_lower for greeting in ["hello", "hi", "hey", "greetings"]):
        return "Hello! How can I assist you today?"

    # Help responses
    elif any(help_word in prompt_lower for help_word in ["help", "support", "assist"]):
        return ("I can help with the following:\n"
                "• Checking your account status\n"
                "• Updating your profile information\n"
                "• Providing course materials\n"
                "• Scheduling appointments")

    # Common questions
    elif "schedule" in prompt_lower:
        return "You can view and update your schedule in the dashboard under 'My Schedule'."

    elif "payment" in prompt_lower or "bill" in prompt_lower:
        return "Payment information can be found in the 'Billing' section of your account."

    # Default response
    else:
        return ("I've received your message. For specific inquiries, please use the contact form "
                "or reach out to our support team directly.")
```

#### Pattern B: Embedding API
```python
# BEFORE (Violation)
import openai

def get_embeddings(text):
    response = openai.Embedding.create(
        input=text,
        model="text-embedding-ada-002"
    )
    return response.data[0].embedding

# AFTER (Compliant)
def get_embeddings(text):
    """
    Generate deterministic embeddings using hashing
    """
    import hashlib

    # Create a simple hash-based embedding
    # This is deterministic and suitable for basic similarity comparison
    hash_obj = hashlib.sha256(text.encode())
    hex_dig = hash_obj.hexdigest()

    # Convert hex digest to numerical embedding
    embedding = []
    for i in range(0, len(hex_dig), 2):
        byte_val = int(hex_dig[i:i+2], 16)
        normalized_val = (byte_val / 255.0) * 2 - 1  # Normalize to [-1, 1]
        embedding.append(normalized_val)

    # Pad or truncate to standard size (1536 dimensions like OpenAI's embeddings)
    while len(embedding) < 1536:
        embedding.append(0.0)

    return embedding[:1536]
```

### 2. LangChain Agent Replacement

#### Pattern C: Simple Agent Loop
```python
# BEFORE (Violation)
from langchain.agents import initialize_agent
from langchain.llms import OpenAI

def process_request(user_input):
    llm = OpenAI(temperature=0)
    agent = initialize_agent(
        tools=[],
        llm=llm,
        agent="zero-shot-react-description",
        verbose=True
    )
    return agent.run(user_input)

# AFTER (Compliant)
def process_request(user_input):
    """
    Process request using deterministic workflow
    """
    # Classify intent using keyword matching
    intent = classify_intent(user_input)

    if intent == "question_answering":
        return handle_qa_request(user_input)
    elif intent == "data_lookup":
        return handle_data_lookup(user_input)
    elif intent == "calculation":
        return handle_calculation(user_input)
    else:
        return "I'm not sure how to handle that request. Please be more specific."

def classify_intent(text):
    """Classify user intent using keyword matching"""
    text_lower = text.lower()

    qa_indicators = ["what", "how", "when", "where", "why", "who", "explain", "define"]
    lookup_indicators = ["find", "search", "get", "show", "list", "retrieve", "look up"]
    calc_indicators = ["calculate", "compute", "add", "subtract", "multiply", "divide", "sum"]

    if any(indicator in text_lower for indicator in qa_indicators):
        return "question_answering"
    elif any(indicator in text_lower for indicator in lookup_indicators):
        return "data_lookup"
    elif any(indicator in text_lower for indicator in calc_indicators):
        return "calculation"
    else:
        return "unknown"
```

### 3. Vector Database Replacement

#### Pattern D: Semantic Search
```python
# BEFORE (Violation)
import pinecone
from openai import OpenAI

def semantic_search(query, top_k=5):
    # Create embedding for query
    client = OpenAI()
    query_embedding = client.embeddings.create(
        input=query,
        model="text-embedding-ada-002"
    ).data[0].embedding

    # Search vector database
    index = pinecone.Index("my-index")
    results = index.query(vector=query_embedding, top_k=top_k)

    return [match.metadata for match in results.matches]

# AFTER (Compliant)
import sqlite3
import re

def semantic_search(query, top_k=5):
    """
    Search using traditional text matching with relevance scoring
    """
    conn = sqlite3.connect('documents.db')
    cursor = conn.cursor()

    # Simple keyword matching with scoring
    query_keywords = set(re.findall(r'\b\w+\b', query.lower()))

    cursor.execute("""
        SELECT id, title, content,
               (SELECT COUNT(*) FROM (
                   SELECT value FROM json_each(json_array(content, title))
                   WHERE LOWER(value) IN ({})
               )) as keyword_matches
        FROM documents
        WHERE keyword_matches > 0
        ORDER BY keyword_matches DESC
        LIMIT ?
    """.format(','.join(['?' for _ in query_keywords])),
        list(query_keywords) + [top_k]
    )

    results = cursor.fetchall()
    conn.close()

    return [{"id": r[0], "title": r[1], "content": r[2], "relevance": r[3]} for r in results]
```

### 4. Configuration Remediation

#### Pattern E: Environment Variables
```yaml
# BEFORE (Violation)
# .env
OPENAI_API_KEY=sk-...
ANTHROPIC_API_KEY=...

# config.yaml
llm:
  provider: openai
  model: gpt-4
  temperature: 0.7

# AFTER (Compliant)
# .env
# (Remove LLM API keys)

# config.yaml
# (Remove LLM configuration sections)
features:
  enabled:
    - user_authentication
    - data_storage
    - basic_search
    - content_delivery
```

### 5. Dependency Removal Templates

#### Pattern F: Requirements Cleanup
```txt
# BEFORE (With LLM dependencies)
openai==0.27.8
anthropic==0.3.0
transformers==4.21.0
langchain==0.0.240
pinecone-client==2.2.4
torch==1.13.1

# AFTER (Zero-Backend-LLM compliant)
fastapi==0.104.1
sqlalchemy==2.0.23
pydantic==2.5.0
python-multipart==0.0.6
psycopg2-binary==2.9.9
bcrypt==4.0.1
python-jose[cryptography]==3.3.0
```

## Remediation Scripts

### 6. Automated Import Removal
```python
# import_cleanup.py
import re

def remove_llm_imports(content):
    """
    Remove common LLM imports from Python code
    """
    # Patterns for LLM imports
    llm_import_patterns = [
        r'^\s*import openai\s*$',
        r'^\s*from openai import.*$',
        r'^\s*import anthropic\s*$',
        r'^\s*from anthropic import.*$',
        r'^\s*import langchain\s*$',
        r'^\s*from langchain import.*$',
        r'^\s*import transformers\s*$',
        r'^\s*from transformers import.*$',
        r'^\s*import (pinecone|weaviate|chromadb)\s*$'
    ]

    lines = content.split('\n')
    filtered_lines = []

    for line in lines:
        should_remove = False
        for pattern in llm_import_patterns:
            if re.match(pattern, line.strip()):
                should_remove = True
                print(f"Removing: {line.strip()}")
                break

        if not should_remove:
            filtered_lines.append(line)

    return '\n'.join(filtered_lines)
```

### 7. Function Call Replacement
```python
# function_replacement.py
import re

def replace_llm_calls(content):
    """
    Replace common LLM API calls with compliant alternatives
    """
    replacements = {
        # OpenAI calls
        r'openai\.ChatCompletion\.create\((.*?)\)': 'deterministic_chat_response(\\1)',
        r'openai\.Completion\.create\((.*?)\)': 'deterministic_completion(\\1)',
        r'client\.chat\.completions\.create\((.*?)\)': 'deterministic_completions(\\1)',

        # Anthropic calls
        r'client\.messages\.create\((.*?)\)': 'deterministic_messages(\\1)',

        # Embedding calls
        r'client\.embeddings\.create\((.*?)\)': 'deterministic_embeddings(\\1)',
    }

    modified_content = content
    for pattern, replacement in replacements.items():
        modified_content = re.sub(pattern, replacement, modified_content, flags=re.DOTALL)

    return modified_content
```

### 8. Stub Function Library
```python
# compliance_stubs.py
"""
Stub functions for Zero-Backend-LLM compliance
These replace LLM API calls with deterministic alternatives
"""

def deterministic_chat_response(**kwargs):
    """
    Stub for openai.ChatCompletion.create()
    Returns deterministic response based on input
    """
    print("WARNING: LLM API call attempted - returning compliant stub")

    messages = kwargs.get('messages', [])
    if messages:
        user_msg = next((m for m in messages if m.get('role') == 'user'), {})
        content = user_msg.get('content', '')

        if 'hello' in content.lower():
            return {'choices': [{'message': {'content': 'Hello! This is a compliant response.'}}]}
        else:
            return {'choices': [{'message': {'content': 'This is a deterministic response for compliance.'}}]}
    return {'choices': [{'message': {'content': 'Default compliant response'}}]}

def deterministic_embeddings(**kwargs):
    """
    Stub for embedding API calls
    Returns deterministic hash-based embedding
    """
    print("WARNING: Embedding API call attempted - returning compliant stub")

    input_text = kwargs.get('input', '')
    # Simple hash-based embedding
    import hashlib
    hash_obj = hashlib.md5(input_text.encode())
    return {'data': [{'embedding': [ord(c)/255.0 for c in hash_obj.hexdigest()[:1536]]}]}

def deterministic_completion(**kwargs):
    """
    Stub for openai.Completion.create()
    Returns deterministic response
    """
    print("WARNING: LLM API call attempted - returning compliant stub")
    return {'choices': [{'text': 'This is a deterministic response for compliance.'}]}

def deterministic_completions(**kwargs):
    """
    Stub for client.chat.completions.create()
    Returns deterministic response
    """
    print("WARNING: LLM API call attempted - returning compliant stub")
    return {'choices': [{'message': {'content': 'This is a compliant response.'}}]}

def deterministic_messages(**kwargs):
    """
    Stub for client.messages.create()
    Returns deterministic response
    """
    print("WARNING: LLM API call attempted - returning compliant stub")
    return {'content': [{'type': 'text', 'text': 'This is a compliant response.'}]}
```

These templates provide ready-to-use patterns for remediating common LLM integration violations while maintaining functionality.