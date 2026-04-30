# RAG (Retrieval-Augmented Generation) Systems

## Overview

Comprehensive guide for implementing RAG systems for self-learning marketing agents, covering vector databases, embeddings, retrieval strategies, and feedback loop integration.

## RAG Architecture

### Core Components

```
┌─────────────────────────────────────────────────────────┐
│                    RAG System                            │
├─────────────────────────────────────────────────────────┤
│                                                          │
│  1. Document Processing                                  │
│     ├─ Chunking Strategy                                │
│     ├─ Metadata Extraction                              │
│     └─ Embedding Generation                             │
│                                                          │
│  2. Vector Storage                                       │
│     ├─ Vector Database (Pinecone/Weaviate/ChromaDB)    │
│     ├─ Indexing                                         │
│     └─ Metadata Filtering                               │
│                                                          │
│  3. Retrieval                                           │
│     ├─ Query Embedding                                  │
│     ├─ Similarity Search                                │
│     └─ Reranking                                        │
│                                                          │
│  4. Generation                                          │
│     ├─ Context Assembly                                 │
│     ├─ Prompt Construction                              │
│     └─ LLM Generation                                   │
│                                                          │
│  5. Feedback Loop                                       │
│     ├─ Performance Tracking                             │
│     ├─ Document Updates                                 │
│     └─ Continuous Learning                              │
│                                                          │
└─────────────────────────────────────────────────────────┘
```

## Document Processing

### Chunking Strategies

#### Fixed-Size Chunking

```python
def chunk_text_fixed(text: str, chunk_size: int = 512, overlap: int = 50) -> list[str]:
    """Split text into fixed-size chunks with overlap"""
    chunks = []
    start = 0

    while start < len(text):
        end = start + chunk_size
        chunk = text[start:end]
        chunks.append(chunk)
        start = end - overlap

    return chunks
```

#### Semantic Chunking

```python
def chunk_text_semantic(text: str, max_chunk_size: int = 512) -> list[str]:
    """Split text at semantic boundaries (sentences, paragraphs)"""
    import re

    # Split by paragraphs first
    paragraphs = text.split('\n\n')
    chunks = []
    current_chunk = ""

    for para in paragraphs:
        # Split paragraph into sentences
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

#### Recursive Chunking

```python
def chunk_text_recursive(
    text: str,
    chunk_size: int = 512,
    separators: list[str] = ["\n\n", "\n", ". ", " "]
) -> list[str]:
    """Recursively split text using hierarchy of separators"""
    if len(text) <= chunk_size:
        return [text]

    # Try each separator in order
    for separator in separators:
        if separator in text:
            parts = text.split(separator)
            chunks = []
            current_chunk = ""

            for part in parts:
                if len(current_chunk) + len(part) + len(separator) <= chunk_size:
                    current_chunk += part + separator
                else:
                    if current_chunk:
                        chunks.append(current_chunk.strip())
                    current_chunk = part + separator

            if current_chunk:
                chunks.append(current_chunk.strip())

            return chunks

    # If no separator works, fall back to fixed-size
    return chunk_text_fixed(text, chunk_size)
```

### Metadata Extraction

```python
from datetime import datetime
from typing import Dict, Any

def extract_metadata(document: str, source: str) -> Dict[str, Any]:
    """Extract metadata from document"""
    return {
        "source": source,
        "timestamp": datetime.utcnow().isoformat(),
        "length": len(document),
        "word_count": len(document.split()),
        "language": detect_language(document),
        "topics": extract_topics(document),
        "entities": extract_entities(document),
    }

def extract_topics(text: str) -> list[str]:
    """Extract main topics from text"""
    # Use keyword extraction or topic modeling
    # Simplified example
    keywords = ["marketing", "social media", "engagement", "analytics"]
    return [kw for kw in keywords if kw.lower() in text.lower()]
```

### Embedding Generation

#### Using OpenAI Embeddings

```python
import openai
from typing import List

def generate_embeddings_openai(texts: List[str], model: str = "text-embedding-3-small") -> List[List[float]]:
    """Generate embeddings using OpenAI"""
    response = openai.embeddings.create(
        input=texts,
        model=model
    )
    return [item.embedding for item in response.data]
```

#### Using Sentence Transformers

```python
from sentence_transformers import SentenceTransformer

class EmbeddingGenerator:
    def __init__(self, model_name: str = "all-MiniLM-L6-v2"):
        self.model = SentenceTransformer(model_name)

    def generate(self, texts: List[str]) -> List[List[float]]:
        """Generate embeddings using sentence transformers"""
        embeddings = self.model.encode(texts, convert_to_numpy=True)
        return embeddings.tolist()
```

## Vector Database Integration

### Pinecone

```python
import pinecone
from typing import List, Dict, Any

class PineconeVectorStore:
    def __init__(self, api_key: str, environment: str, index_name: str):
        pinecone.init(api_key=api_key, environment=environment)
        self.index = pinecone.Index(index_name)

    def upsert(self, documents: List[Dict[str, Any]]):
        """Insert or update documents"""
        vectors = []
        for doc in documents:
            vectors.append({
                "id": doc["id"],
                "values": doc["embedding"],
                "metadata": doc["metadata"]
            })

        self.index.upsert(vectors=vectors)

    def query(self, query_embedding: List[float], top_k: int = 5, filter: Dict = None):
        """Query similar documents"""
        results = self.index.query(
            vector=query_embedding,
            top_k=top_k,
            filter=filter,
            include_metadata=True
        )
        return results.matches
```

### ChromaDB

```python
import chromadb
from chromadb.config import Settings

class ChromaVectorStore:
    def __init__(self, persist_directory: str = "./chroma_db"):
        self.client = chromadb.Client(Settings(
            persist_directory=persist_directory,
            anonymized_telemetry=False
        ))
        self.collection = self.client.get_or_create_collection("marketing_knowledge")

    def add(self, documents: List[str], metadatas: List[Dict], ids: List[str]):
        """Add documents to collection"""
        self.collection.add(
            documents=documents,
            metadatas=metadatas,
            ids=ids
        )

    def query(self, query_text: str, n_results: int = 5, where: Dict = None):
        """Query similar documents"""
        results = self.collection.query(
            query_texts=[query_text],
            n_results=n_results,
            where=where
        )
        return results
```

### Weaviate

```python
import weaviate

class WeaviateVectorStore:
    def __init__(self, url: str):
        self.client = weaviate.Client(url)

    def create_schema(self):
        """Create schema for marketing documents"""
        schema = {
            "class": "MarketingDocument",
            "properties": [
                {"name": "content", "dataType": ["text"]},
                {"name": "source", "dataType": ["string"]},
                {"name": "timestamp", "dataType": ["date"]},
                {"name": "platform", "dataType": ["string"]},
                {"name": "engagement_score", "dataType": ["number"]},
            ]
        }
        self.client.schema.create_class(schema)

    def add(self, document: Dict[str, Any]):
        """Add document to Weaviate"""
        self.client.data_object.create(
            data_object=document,
            class_name="MarketingDocument"
        )

    def query(self, query_text: str, limit: int = 5):
        """Semantic search"""
        result = (
            self.client.query
            .get("MarketingDocument", ["content", "source", "platform"])
            .with_near_text({"concepts": [query_text]})
            .with_limit(limit)
            .do()
        )
        return result
```

## Retrieval Strategies

### Basic Similarity Search

```python
def retrieve_basic(query: str, vector_store, top_k: int = 5):
    """Basic similarity search"""
    query_embedding = generate_embedding(query)
    results = vector_store.query(query_embedding, top_k=top_k)
    return results
```

### Hybrid Search (Dense + Sparse)

```python
from rank_bm25 import BM25Okapi

class HybridRetriever:
    def __init__(self, vector_store, documents: List[str]):
        self.vector_store = vector_store
        self.documents = documents

        # Build BM25 index
        tokenized_docs = [doc.split() for doc in documents]
        self.bm25 = BM25Okapi(tokenized_docs)

    def retrieve(self, query: str, top_k: int = 5, alpha: float = 0.5):
        """Hybrid retrieval combining dense and sparse"""
        # Dense retrieval (vector similarity)
        query_embedding = generate_embedding(query)
        dense_results = self.vector_store.query(query_embedding, top_k=top_k * 2)

        # Sparse retrieval (BM25)
        tokenized_query = query.split()
        sparse_scores = self.bm25.get_scores(tokenized_query)

        # Combine scores
        combined_scores = {}
        for result in dense_results:
            doc_id = result.id
            dense_score = result.score
            sparse_score = sparse_scores[int(doc_id)]

            # Weighted combination
            combined_scores[doc_id] = alpha * dense_score + (1 - alpha) * sparse_score

        # Sort and return top k
        sorted_results = sorted(combined_scores.items(), key=lambda x: x[1], reverse=True)
        return sorted_results[:top_k]
```

### Reranking

```python
from sentence_transformers import CrossEncoder

class Reranker:
    def __init__(self, model_name: str = "cross-encoder/ms-marco-MiniLM-L-6-v2"):
        self.model = CrossEncoder(model_name)

    def rerank(self, query: str, documents: List[str], top_k: int = 5):
        """Rerank documents using cross-encoder"""
        # Create query-document pairs
        pairs = [[query, doc] for doc in documents]

        # Score pairs
        scores = self.model.predict(pairs)

        # Sort by score
        ranked = sorted(zip(documents, scores), key=lambda x: x[1], reverse=True)

        return ranked[:top_k]
```

### Metadata Filtering

```python
def retrieve_with_filters(
    query: str,
    vector_store,
    filters: Dict[str, Any],
    top_k: int = 5
):
    """Retrieve with metadata filters"""
    query_embedding = generate_embedding(query)

    # Example filters
    # filters = {
    #     "platform": "linkedin",
    #     "engagement_score": {"$gte": 0.7},
    #     "timestamp": {"$gte": "2024-01-01"}
    # }

    results = vector_store.query(
        query_embedding,
        top_k=top_k,
        filter=filters
    )

    return results
```

## RAG Pipeline

### Complete RAG Implementation

```python
class RAGSystem:
    def __init__(self, vector_store, llm_client, embedding_generator):
        self.vector_store = vector_store
        self.llm = llm_client
        self.embedder = embedding_generator

    def add_documents(self, documents: List[str], metadatas: List[Dict]):
        """Add documents to knowledge base"""
        # Chunk documents
        chunks = []
        chunk_metadatas = []

        for doc, metadata in zip(documents, metadatas):
            doc_chunks = chunk_text_semantic(doc)
            chunks.extend(doc_chunks)
            chunk_metadatas.extend([metadata] * len(doc_chunks))

        # Generate embeddings
        embeddings = self.embedder.generate(chunks)

        # Store in vector database
        for i, (chunk, embedding, metadata) in enumerate(zip(chunks, embeddings, chunk_metadatas)):
            self.vector_store.upsert({
                "id": f"{metadata['source']}_{i}",
                "embedding": embedding,
                "metadata": {**metadata, "text": chunk}
            })

    def retrieve(self, query: str, top_k: int = 5, filters: Dict = None):
        """Retrieve relevant documents"""
        query_embedding = self.embedder.generate([query])[0]
        results = self.vector_store.query(query_embedding, top_k=top_k, filter=filters)
        return results

    def generate(self, query: str, top_k: int = 5):
        """RAG: Retrieve and generate"""
        # Retrieve relevant documents
        retrieved_docs = self.retrieve(query, top_k=top_k)

        # Construct context
        context = "\n\n".join([doc.metadata["text"] for doc in retrieved_docs])

        # Build prompt
        prompt = f"""Based on the following context, answer the question.

Context:
{context}

Question: {query}

Answer:"""

        # Generate response
        response = self.llm.generate(prompt)

        return {
            "answer": response,
            "sources": retrieved_docs,
            "context": context
        }
```

## Feedback Loop Integration

### Performance Tracking

```python
class FeedbackTracker:
    def __init__(self, vector_store):
        self.vector_store = vector_store

    def track_retrieval(self, query: str, retrieved_docs: List, user_feedback: Dict):
        """Track retrieval performance"""
        feedback_entry = {
            "query": query,
            "retrieved_doc_ids": [doc.id for doc in retrieved_docs],
            "relevance_scores": user_feedback.get("relevance_scores", []),
            "selected_doc_id": user_feedback.get("selected_doc_id"),
            "timestamp": datetime.utcnow().isoformat()
        }

        # Store feedback for analysis
        self.store_feedback(feedback_entry)

    def store_feedback(self, feedback: Dict):
        """Store feedback in database"""
        # Implementation depends on your storage solution
        pass
```

### Document Updates

```python
class DocumentUpdater:
    def __init__(self, vector_store):
        self.vector_store = vector_store

    def update_from_feedback(self, post_id: str, performance_metrics: Dict):
        """Update document metadata based on performance"""
        # Retrieve existing document
        doc = self.vector_store.get(post_id)

        # Update metadata with performance data
        doc.metadata.update({
            "engagement_rate": performance_metrics["engagement_rate"],
            "click_through_rate": performance_metrics["ctr"],
            "performance_score": self.calculate_score(performance_metrics),
            "last_updated": datetime.utcnow().isoformat()
        })

        # Re-index with updated metadata
        self.vector_store.upsert(doc)

    def calculate_score(self, metrics: Dict) -> float:
        """Calculate overall performance score"""
        weights = {
            "engagement_rate": 0.4,
            "ctr": 0.3,
            "shares": 0.2,
            "comments": 0.1
        }

        score = sum(metrics.get(k, 0) * v for k, v in weights.items())
        return min(score, 1.0)
```

### Continuous Learning

```python
class ContinuousLearner:
    def __init__(self, rag_system: RAGSystem):
        self.rag = rag_system

    def learn_from_successful_posts(self, threshold: float = 0.7):
        """Add high-performing posts to knowledge base"""
        # Query for high-performing posts
        successful_posts = self.query_successful_posts(threshold)

        # Extract insights
        documents = []
        metadatas = []

        for post in successful_posts:
            # Create learning document
            doc = f"""
            Platform: {post['platform']}
            Content: {post['content']}
            Performance: {post['engagement_rate']:.2%} engagement
            Key Success Factors:
            - Posted at {post['posting_time']}
            - Target audience: {post['audience']}
            - Content type: {post['content_type']}
            """

            documents.append(doc)
            metadatas.append({
                "source": "successful_post",
                "post_id": post['id'],
                "performance_score": post['engagement_rate'],
                "platform": post['platform']
            })

        # Add to knowledge base
        self.rag.add_documents(documents, metadatas)

    def query_successful_posts(self, threshold: float):
        """Query database for successful posts"""
        # Implementation depends on your database
        pass
```

## Evaluation Metrics

### Retrieval Metrics

```python
def calculate_retrieval_metrics(retrieved_docs: List, relevant_docs: List):
    """Calculate precision, recall, F1"""
    retrieved_ids = set(doc.id for doc in retrieved_docs)
    relevant_ids = set(relevant_docs)

    true_positives = len(retrieved_ids & relevant_ids)
    false_positives = len(retrieved_ids - relevant_ids)
    false_negatives = len(relevant_ids - retrieved_ids)

    precision = true_positives / (true_positives + false_positives) if (true_positives + false_positives) > 0 else 0
    recall = true_positives / (true_positives + false_negatives) if (true_positives + false_negatives) > 0 else 0
    f1 = 2 * (precision * recall) / (precision + recall) if (precision + recall) > 0 else 0

    return {
        "precision": precision,
        "recall": recall,
        "f1": f1
    }
```

### Generation Metrics

```python
from rouge import Rouge

def calculate_generation_metrics(generated: str, reference: str):
    """Calculate ROUGE scores"""
    rouge = Rouge()
    scores = rouge.get_scores(generated, reference)[0]

    return {
        "rouge-1": scores["rouge-1"]["f"],
        "rouge-2": scores["rouge-2"]["f"],
        "rouge-l": scores["rouge-l"]["f"]
    }
```

## Best Practices

1. **Chunking**: Use semantic chunking for better context preservation
2. **Metadata**: Include rich metadata for filtering and ranking
3. **Embeddings**: Choose embedding model based on domain and language
4. **Retrieval**: Combine multiple retrieval strategies (hybrid search)
5. **Reranking**: Use cross-encoders for better relevance
6. **Feedback**: Continuously update knowledge base with performance data
7. **Evaluation**: Regularly measure and optimize retrieval quality
8. **Caching**: Cache embeddings and frequent queries
9. **Monitoring**: Track retrieval latency and relevance
10. **Versioning**: Version your knowledge base for rollback capability
