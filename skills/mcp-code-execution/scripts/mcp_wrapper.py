#!/usr/bin/env python3
"""
MCP Server Wrapper

This script wraps common MCP server calls and performs data filtering
to return only relevant results to the agent context, preventing token bloat.
"""

import os
import sys
import json
import argparse
from typing import List, Dict, Any, Optional
import requests


class MCPServerWrapper:
    """
    A wrapper class for common MCP server interactions that filters data
    to return only relevant results to the agent context.
    """
    
    def __init__(self, base_url: str = None):
        self.base_url = base_url or os.getenv("MCP_BASE_URL", "http://localhost:8080")
        self.session = requests.Session()
        
        # Add authentication if available
        auth_token = os.getenv("MCP_AUTH_TOKEN")
        if auth_token:
            self.session.headers.update({"Authorization": f"Bearer {auth_token}"})
    
    def _make_request(self, method: str, endpoint: str, **kwargs) -> Dict[str, Any]:
        """Make an HTTP request to the MCP server."""
        url = f"{self.base_url.rstrip('/')}/{endpoint.lstrip('/')}"
        
        try:
            response = self.session.request(method, url, **kwargs)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            return {"error": str(e)}
        except json.JSONDecodeError:
            return {"error": "Invalid JSON response"}
    
    def search_gdrive_files(self, query: str, limit: int = 5) -> List[Dict[str, Any]]:
        """
        Search Google Drive files and return only the most relevant results.
        
        Args:
            query: Search query string
            limit: Maximum number of results to return (default: 5)
            
        Returns:
            List of file metadata objects (filtered to top results)
        """
        # Simulate calling an MCP server endpoint for GDrive search
        params = {"q": query, "limit": limit * 2}  # Request more than needed for filtering
        response = self._make_request("GET", "/gdrive/search", params=params)
        
        if "error" in response:
            return [{"error": response["error"]}]
        
        files = response.get("files", [])
        
        # Sort by relevance (simulated - in real scenario this would be done by the server)
        sorted_files = sorted(files, key=lambda x: x.get("modified_time", ""), reverse=True)
        
        # Return only the top results with minimal metadata
        top_files = []
        for file in sorted_files[:limit]:
            top_files.append({
                "name": file.get("name"),
                "id": file.get("id"),
                "modified_time": file.get("modified_time"),
                "mime_type": file.get("mime_type", "").split("/")[-1]  # Just the type part
            })
        
        return top_files
    
    def query_database(self, query: str, limit: int = 5, sort_by: str = None) -> List[Dict[str, Any]]:
        """
        Execute a database query and return only the most relevant results.
        
        Args:
            query: SQL query string
            limit: Maximum number of results to return (default: 5)
            sort_by: Column to sort by (optional)
            
        Returns:
            List of query results (filtered to top results)
        """
        payload = {
            "query": query,
            "limit": limit * 2,  # Request more than needed for filtering
            "sort_by": sort_by
        }
        
        response = self._make_request("POST", "/database/query", json=payload)
        
        if "error" in response:
            return [{"error": response["error"]}]
        
        results = response.get("results", [])
        
        # Apply additional client-side filtering if needed
        if sort_by:
            results = sorted(results, key=lambda x: x.get(sort_by, ""), reverse=True)
        
        # Return only the top results
        return results[:limit]
    
    def list_recent_documents(self, limit: int = 5) -> List[Dict[str, Any]]:
        """
        Get a list of recently accessed documents.
        
        Args:
            limit: Maximum number of results to return (default: 5)
            
        Returns:
            List of recent documents with minimal metadata
        """
        params = {"limit": limit * 2}
        response = self._make_request("GET", "/documents/recent", params=params)
        
        if "error" in response:
            return [{"error": response["error"]}]
        
        docs = response.get("documents", [])
        
        # Sort by access time (most recent first)
        sorted_docs = sorted(docs, key=lambda x: x.get("last_accessed", ""), reverse=True)
        
        # Return only the top results with minimal metadata
        top_docs = []
        for doc in sorted_docs[:limit]:
            top_docs.append({
                "title": doc.get("title"),
                "id": doc.get("id"),
                "last_accessed": doc.get("last_accessed"),
                "owner": doc.get("owner", {}).get("name", "Unknown")
            })
        
        return top_docs
    
    def search_knowledge_base(self, query: str, limit: int = 5, tags: List[str] = None) -> List[Dict[str, Any]]:
        """
        Search the knowledge base and return only the most relevant results.
        
        Args:
            query: Search query string
            limit: Maximum number of results to return (default: 5)
            tags: Optional list of tags to filter by
            
        Returns:
            List of knowledge base articles (filtered to top results)
        """
        payload = {
            "query": query,
            "limit": limit * 2,
            "tags": tags or []
        }
        
        response = self._make_request("POST", "/knowledge/search", json=payload)
        
        if "error" in response:
            return [{"error": response["error"]}]
        
        articles = response.get("articles", [])
        
        # Sort by relevance score (simulated)
        sorted_articles = sorted(articles, key=lambda x: x.get("relevance_score", 0), reverse=True)
        
        # Return only the top results with minimal content
        top_articles = []
        for article in sorted_articles[:limit]:
            top_articles.append({
                "title": article.get("title"),
                "id": article.get("id"),
                "relevance_score": article.get("relevance_score"),
                "summary": article.get("summary", "")[:200] + "..." if len(article.get("summary", "")) > 200 else article.get("summary")  # Truncate long summaries
            })
        
        return top_articles


def main():
    parser = argparse.ArgumentParser(description='MCP Server Wrapper for filtered data retrieval')
    parser.add_argument('--action', '-a', required=True, 
                       choices=['gdrive-search', 'db-query', 'recent-docs', 'kb-search'],
                       help='Action to perform')
    parser.add_argument('--query', '-q', help='Search/query string')
    parser.add_argument('--limit', '-l', type=int, default=5, help='Result limit (default: 5)')
    parser.add_argument('--sort-by', help='Column to sort by (for DB queries)')
    parser.add_argument('--tags', nargs='+', help='Tags to filter by (for KB search)')
    
    args = parser.parse_args()
    
    wrapper = MCPServerWrapper()
    
    if args.action == 'gdrive-search':
        if not args.query:
            print("Error: Query is required for GDrive search")
            sys.exit(1)
        
        results = wrapper.search_gdrive_files(args.query, args.limit)
        print(json.dumps(results, indent=2))
        
    elif args.action == 'db-query':
        if not args.query:
            print("Error: Query is required for database query")
            sys.exit(1)
        
        results = wrapper.query_database(args.query, args.limit, args.sort_by)
        print(json.dumps(results, indent=2))
        
    elif args.action == 'recent-docs':
        results = wrapper.list_recent_documents(args.limit)
        print(json.dumps(results, indent=2))
        
    elif args.action == 'kb-search':
        if not args.query:
            print("Error: Query is required for knowledge base search")
            sys.exit(1)
        
        results = wrapper.search_knowledge_base(args.query, args.limit, args.tags)
        print(json.dumps(results, indent=2))


if __name__ == "__main__":
    main()