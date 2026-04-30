---
name: qa-auditor
description: Specialized in code review and API auditing to ensure Zero-Backend-LLM compliance in Phase 1. Responsible for verifying that no forbidden LLM API calls, RAG summarization, or agent loops exist in the backend.
---

# QA Auditor

Specialized in code review and API auditing to ensure Zero-Backend-LLM compliance in Phase 1. Responsible for verifying that no forbidden LLM API calls, RAG summarization, or agent loops exist in the backend.

## When to Use This Skill

Use this skill when performing:
- Code reviews to identify LLM integration violations
- API audits for Zero-Backend-LLM compliance
- Security assessments of backend systems
- Verification of deterministic backend operations
- Compliance checks for educational technology systems
- Pre-deployment validation of backend logic

## Core Principles

### Zero-Backend-LLM Compliance
- No direct LLM API calls in backend code
- No RAG (Retrieval-Augmented Generation) implementations
- No agent loops or AI-driven decision making
- Purely deterministic backend processing
- Clear separation between frontend AI features and backend logic

### Forbidden Patterns
- Direct calls to OpenAI, Claude, or other LLM APIs
- Embedding services (e.g., OpenAI embeddings, Cohere)
- Vector databases used for RAG systems
- Agent frameworks (LangChain, AutoGen, etc.)
- Recursive AI decision loops
- AI-powered data processing pipelines

### Allowed Patterns
- Frontend AI integration (with proper isolation)
- Traditional database queries
- Business logic processing
- User authentication and authorization
- File upload/download services
- Standard CRUD operations

## Code Review Checklist

### 1. LLM API Detection
```python
# FORBIDDEN PATTERNS - These indicate violations:

# OpenAI API calls
import openai
openai.ChatCompletion.create(...)
client.chat.completions.create(...)

# Anthropic API calls
from anthropic import Anthropic
client.messages.create(...)

# Hugging Face inference
from transformers import pipeline
pipeline("text-generation", ...)

# Embedding services
from openai.embeddings import Embedding
from cohere import Client
```

### 2. RAG System Detection
```python
# FORBIDDEN PATTERNS - These indicate RAG violations:

# Vector databases
import pinecone
import weaviate
import chromadb

# Document loaders and processors
from langchain.document_loaders import ...
from llama_index import VectorStoreIndex

# Similarity search implementations
cosine_similarity(...)
vector_search(...)
semantic_search(...)
```

### 3. Agent Loop Detection
```python
# FORBIDDEN PATTERNS - These indicate agent loop violations:

# Recursive AI decision making
def process_with_ai_loop(data):
    result = ai_call(data)
    if needs_more_processing(result):
        return process_with_ai_loop(result)  # RECURSIVE LOOP!

# Agent frameworks
from langchain.agents import initialize_agent
from autogen import ConversableAgent

# Autonomous decision chains
while condition_met_by_ai(output):
    output = ai_process(output)
```

## API Auditing Techniques

### 1. Static Code Analysis
```bash
# Using grep to detect LLM API calls
grep -r "openai\|anthropic\|cohere\|transformers" --include="*.py" .
grep -r "ChatCompletion\|messages.create\|embeddings" --include="*.py" .
grep -r "langchain\|llama_index\|pinecone\|weaviate" --include="*.py" .
```

### 2. Dependency Analysis
```bash
# Check for forbidden dependencies
pip list | grep -E "(openai|anthropic|cohere|transformers|langchain|llama-index|pinecone-client|weaviate)"
poetry show | grep -E "(openai|anthropic|cohere|transformers|langchain)"
```

### 3. Network Traffic Analysis
```python
# Look for outbound API calls to LLM services
# In logs or network monitoring tools
"POST https://api.openai.com"
"POST https://api.anthropic.com"
"POST https://api.cohere.ai"
```

## Audit Scripts

### 1. LLM Detector Script
```python
import ast
import re
from typing import List, Tuple

class LLMApiDetector(ast.NodeVisitor):
    """
    Detects LLM API calls in Python code
    """
    def __init__(self):
        self.violations = []
        self.forbidden_patterns = [
            'openai', 'anthropic', 'cohere', 'transformers',
            'ChatCompletion', 'messages.create', 'embeddings',
            'langchain', 'llama_index', 'pinecone', 'weaviate',
            'chromadb', 'huggingface'
        ]

    def visit_Import(self, node):
        for alias in node.names:
            for pattern in self.forbidden_patterns:
                if pattern in alias.name.lower():
                    self.violations.append({
                        'type': 'import_violation',
                        'line': node.lineno,
                        'code': f"import {alias.name}",
                        'pattern': pattern
                    })
        self.generic_visit(node)

    def visit_ImportFrom(self, node):
        for pattern in self.forbidden_patterns:
            if pattern in node.module.lower():
                self.violations.append({
                    'type': 'import_violation',
                    'line': node.lineno,
                    'code': f"from {node.module} import ...",
                    'pattern': pattern
                })
        self.generic_visit(node)

    def visit_Call(self, node):
        # Check function calls for LLM patterns
        if isinstance(node.func, ast.Attribute):
            attr_name = node.func.attr.lower()
            for pattern in ['create', 'generate', 'complete', 'embed']:
                if pattern in attr_name:
                    # Check if it's related to LLMs
                    if hasattr(node.func, 'value') and isinstance(node.func.value, ast.Name):
                        var_name = node.func.value.id.lower()
                        if any(llm_pattern in var_name for llm_pattern in ['openai', 'anthropic', 'client']):
                            self.violations.append({
                                'type': 'function_call_violation',
                                'line': node.lineno,
                                'code': ast.unparse(node),
                                'pattern': f"{var_name}.{attr_name}"
                            })
        self.generic_visit(node)

def audit_python_file(file_path: str) -> List[dict]:
    """
    Audit a Python file for LLM API violations
    """
    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()

    try:
        tree = ast.parse(content)
        detector = LLMApiDetector()
        detector.visit(tree)
        return detector.violations
    except SyntaxError:
        return [{'type': 'syntax_error', 'file': file_path, 'message': 'Syntax error in file'}]
```

### 2. API Endpoint Analyzer
```python
import ast
import re
from typing import List, Dict

class ApiEndpointAnalyzer(ast.NodeVisitor):
    """
    Analyzes API endpoints for potential LLM integration
    """
    def __init__(self):
        self.endpoints = []
        self.current_function = None

    def visit_FunctionDef(self, node):
        # Check if this looks like an API endpoint
        if self._is_api_endpoint(node):
            old_func = self.current_function
            self.current_function = node.name
            self.generic_visit(node)

            # Analyze the function for LLM patterns
            endpoint_info = {
                'function_name': node.name,
                'line': node.lineno,
                'llm_indicators': self._find_llm_indicators(node),
                'parameters': [arg.arg for arg in node.args.args]
            }
            self.endpoints.append(endpoint_info)

            self.current_function = old_func
        else:
            self.generic_visit(node)

    def _is_api_endpoint(self, node) -> bool:
        """
        Determine if function looks like an API endpoint
        """
        # Check decorators (common in frameworks like Flask, FastAPI)
        for decorator in node.decorator_list:
            if isinstance(decorator, ast.Call) and isinstance(decorator.func, ast.Attribute):
                decorator_name = decorator.func.attr.lower()
                if decorator_name in ['get', 'post', 'put', 'delete', 'route']:
                    return True
            elif isinstance(decorator, ast.Name) and decorator.id.lower() in ['get', 'post', 'put', 'delete', 'route']:
                return True
        return False

    def _find_llm_indicators(self, node) -> List[str]:
        """
        Find potential LLM indicators in the function
        """
        indicators = []
        source_lines = ast.unparse(node).lower()

        llm_patterns = [
            'openai', 'anthropic', 'cohere', 'transformers',
            'chatcompletion', 'messages.create', 'embeddings',
            'generate', 'complete', 'llm', 'ai_call',
            'langchain', 'llama_index', 'vector', 'semantic'
        ]

        for pattern in llm_patterns:
            if pattern in source_lines:
                indicators.append(pattern)

        return indicators

def analyze_api_endpoints(file_path: str) -> List[Dict]:
    """
    Analyze API endpoints in a file for LLM integration
    """
    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()

    try:
        tree = ast.parse(content)
        analyzer = ApiEndpointAnalyzer()
        analyzer.visit(tree)
        return analyzer.endpoints
    except SyntaxError:
        return []
```

## Review Procedures

### 1. Pull Request Review Checklist
- [ ] No LLM API imports or calls detected
- [ ] No embedding services or vector databases
- [ ] No agent frameworks or recursive AI loops
- [ ] Backend logic is deterministic
- [ ] Frontend AI features properly isolated
- [ ] Dependencies comply with Zero-Backend-LLM policy
- [ ] API endpoints don't call external LLM services
- [ ] Data processing is rule-based, not AI-driven

### 2. Automated Review Script
```bash
#!/bin/bash
# zero_backend_llm_check.sh

set -e

echo "🔍 Starting Zero-Backend-LLM compliance check..."

VIOLATIONS_FOUND=0

# Check for forbidden imports in Python files
echo "Checking for forbidden imports..."
FORBIDDEN_IMPORTS=$(find . -name "*.py" -exec grep -l -i -E "openai|anthropic|cohere|transformers|langchain|llama_index|pinecone|weaviate|chromadb|huggingface" {} \; || true)

if [ ! -z "$FORBIDDEN_IMPORTS" ]; then
    echo "❌ Forbidden imports detected:"
    echo "$FORBIDDEN_IMPORTS"
    VIOLATIONS_FOUND=$((VIOLATIONS_FOUND + 1))
else
    echo "✅ No forbidden imports found"
fi

# Check for LLM API calls
echo "Checking for LLM API calls..."
LLM_CALLS=$(find . -name "*.py" -exec grep -l -i -E "chatcompletion|messages\.create|embeddings|generate|complete" {} \; || true)

if [ ! -z "$LLM_CALLS" ]; then
    echo "❌ Potential LLM API calls detected:"
    echo "$LLM_CALLS"
    VIOLATIONS_FOUND=$((VIOLATIONS_FOUND + 1))
else
    echo "✅ No LLM API calls found"
fi

# Check dependencies
echo "Checking dependencies..."
if command -v pip &> /dev/null; then
    PIP_VIOLATIONS=$(pip list 2>/dev/null | grep -i -E "openai|anthropic|cohere|transformers|langchain|llama-index|pinecone-client|weaviate" || true)
    if [ ! -z "$PIP_VIOLATIONS" ]; then
        echo "❌ Forbidden dependencies detected:"
        echo "$PIP_VIOLATIONS"
        VIOLATIONS_FOUND=$((VIOLATIONS_FOUND + 1))
    else
        echo "✅ No forbidden dependencies found"
    fi
elif command -v poetry &> /dev/null; then
    POETRY_VIOLATIONS=$(poetry show 2>/dev/null | grep -i -E "openai|anthropic|cohere|transformers|langchain" || true)
    if [ ! -z "$POETRY_VIOLATIONS" ]; then
        echo "❌ Forbidden dependencies detected:"
        echo "$POETRY_VIOLATIONS"
        VIOLATIONS_FOUND=$((VIOLATIONS_FOUND + 1))
    else
        echo "✅ No forbidden dependencies found"
    fi
fi

if [ $VIOLATIONS_FOUND -gt 0 ]; then
    echo "❌ $VIOLATIONS_FOUND compliance violation(s) detected!"
    echo "Please address these issues before merging."
    exit 1
else
    echo "✅ Zero-Backend-LLM compliance check PASSED!"
    exit 0
fi
```

## Compliance Reporting

### 1. Audit Report Template
```markdown
# Zero-Backend-LLM Compliance Audit Report

**Audit Date:** [DATE]
**Auditor:** [NAME]
**Codebase Version:** [VERSION]
**Review Type:** [Full/Patch/PR]

## Summary
- **Files reviewed:** [COUNT]
- **Violations found:** [COUNT]
- **Severity level:** [Low/Medium/High/Critical]
- **Compliance status:** [Pass/Fail]

## Violations Found
### High Severity
- [List critical violations]

### Medium Severity
- [List medium violations]

### Low Severity
- [List low severity issues]

## Recommendations
1. [Action item 1]
2. [Action item 2]
3. [Action item 3]

## Next Steps
- [Immediate actions required]
- [Timeline for fixes]
- [Follow-up audit scheduled]
```

### 2. Continuous Integration Integration
```yaml
# .github/workflows/zero-backend-llm-check.yml
name: Zero-Backend-LLM Compliance Check

on:
  pull_request:
    branches: [ main, master ]
  push:
    branches: [ main, master ]

jobs:
  compliance-check:
    runs-on: ubuntu-latest
    steps:
    - uses: actions/checkout@v3

    - name: Set up Python
      uses: actions/setup-python@v4
      with:
        python-version: '3.x'

    - name: Install dependencies
      run: |
        python -m pip install --upgrade pip
        # Install project dependencies for import checking

    - name: Run Zero-Backend-LLM compliance check
      run: |
        bash zero_backend_llm_check.sh
```

## Remediation Guidelines

### 1. Replacing LLM Calls with Deterministic Logic
```python
# BEFORE (Forbidden): LLM-powered content generation
def generate_response(user_input):
    response = openai.Completion.create(
        engine="davinci",
        prompt=user_input
    )
    return response.choices[0].text

# AFTER (Compliant): Rule-based content generation
def generate_response(user_input):
    # Implement deterministic logic based on business rules
    if "hello" in user_input.lower():
        return "Hello! How can I help you?"
    elif "help" in user_input.lower():
        return "I can help with the following: [list of features]"
    else:
        return "I received your message. How else can I assist you?"
```

### 2. Replacing RAG Systems with Database Queries
```python
# BEFORE (Forbidden): Semantic search with embeddings
def search_knowledge_base(query):
    query_embedding = openai.Embedding.create(input=query)['data'][0]['embedding']
    # Find similar documents using vector similarity
    similar_docs = find_similar_vectors(query_embedding)
    return similar_docs

# AFTER (Compliant): Traditional database search
def search_knowledge_base(query):
    # Use traditional text search with LIKE, full-text search, or regex
    return db.execute(
        "SELECT * FROM knowledge_base WHERE content LIKE ?",
        (f"%{query}%",)
    ).fetchall()
```

This skill provides comprehensive guidance for ensuring Zero-Backend-LLM compliance through systematic code review and API auditing.