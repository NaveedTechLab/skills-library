#!/usr/bin/env python3
"""
Data Filtering Utilities for MCP Server Interactions

This module provides utility functions for filtering data retrieved from MCP servers
to minimize token usage in agent contexts.
"""

import os
import sys
import json
import heapq
from typing import List, Dict, Any, Callable, Union
from datetime import datetime, timedelta


def filter_top_results(
    data: List[Dict[str, Any]], 
    sort_key: str, 
    limit: int = 5,
    reverse: bool = True
) -> List[Dict[str, Any]]:
    """
    Filter data to return only the top N results based on a sort key.
    
    Args:
        data: List of dictionaries to filter
        sort_key: Key to sort by
        limit: Number of results to return
        reverse: Sort order (True for descending, False for ascending)
        
    Returns:
        Top N results sorted by the specified key
    """
    if not data:
        return []
    
    # Sort the data and return top N results
    sorted_data = sorted(data, key=lambda x: x.get(sort_key, 0), reverse=reverse)
    return sorted_data[:limit]


def filter_by_date_range(
    data: List[Dict[str, Any]], 
    date_key: str, 
    days_back: int = 30
) -> List[Dict[str, Any]]:
    """
    Filter data to include only items within a certain date range.
    
    Args:
        data: List of dictionaries to filter
        date_key: Key containing date information
        days_back: Number of days back to include
        
    Returns:
        Items within the specified date range
    """
    if not data:
        return []
    
    cutoff_date = datetime.now() - timedelta(days=days_back)
    
    filtered_data = []
    for item in data:
        date_str = item.get(date_key)
        if date_str:
            try:
                item_date = datetime.fromisoformat(date_str.replace('Z', '+00:00'))
                if item_date >= cutoff_date:
                    filtered_data.append(item)
            except ValueError:
                # If date parsing fails, include the item anyway
                filtered_data.append(item)
    
    return filtered_data


def filter_by_relevance(
    data: List[Dict[str, Any]], 
    relevance_key: str, 
    threshold: float = 0.5,
    limit: int = 5
) -> List[Dict[str, Any]]:
    """
    Filter data based on a relevance score.
    
    Args:
        data: List of dictionaries to filter
        relevance_key: Key containing relevance score
        threshold: Minimum relevance score to include
        limit: Maximum number of results to return
        
    Returns:
        Items with relevance scores above the threshold
    """
    if not data:
        return []
    
    relevant_items = [
        item for item in data 
        if item.get(relevance_key, 0) >= threshold
    ]
    
    # Sort by relevance score and return top N
    sorted_items = sorted(
        relevant_items, 
        key=lambda x: x.get(relevance_key, 0), 
        reverse=True
    )
    
    return sorted_items[:limit]


def truncate_long_fields(
    data: List[Dict[str, Any]], 
    field_lengths: Dict[str, int]
) -> List[Dict[str, Any]]:
    """
    Truncate long fields in data to specified lengths.
    
    Args:
        data: List of dictionaries to process
        field_lengths: Dictionary mapping field names to max lengths
        
    Returns:
        Data with long fields truncated
    """
    if not data:
        return []
    
    processed_data = []
    for item in data:
        new_item = item.copy()
        for field, max_len in field_lengths.items():
            if field in new_item and isinstance(new_item[field], str):
                if len(new_item[field]) > max_len:
                    new_item[field] = new_item[field][:max_len] + "..."
        processed_data.append(new_item)
    
    return processed_data


def select_fields(
    data: List[Dict[str, Any]], 
    include_fields: List[str],
    exclude_fields: List[str] = None
) -> List[Dict[str, Any]]:
    """
    Select only specified fields from data.
    
    Args:
        data: List of dictionaries to process
        include_fields: List of fields to include
        exclude_fields: List of fields to exclude (optional)
        
    Returns:
        Data with only specified fields
    """
    if not data:
        return []
    
    exclude_fields = exclude_fields or []
    processed_data = []
    
    for item in data:
        new_item = {}
        for field in include_fields:
            if field in item and field not in exclude_fields:
                new_item[field] = item[field]
        processed_data.append(new_item)
    
    return processed_data


def deduplicate_by_field(
    data: List[Dict[str, Any]], 
    field: str
) -> List[Dict[str, Any]]:
    """
    Remove duplicates based on a specific field.
    
    Args:
        data: List of dictionaries to process
        field: Field to use for deduplication
        
    Returns:
        Data with duplicates removed
    """
    if not data:
        return []
    
    seen_values = set()
    unique_data = []
    
    for item in data:
        value = item.get(field)
        if value not in seen_values:
            seen_values.add(value)
            unique_data.append(item)
    
    return unique_data


def apply_filters(
    data: List[Dict[str, Any]],
    filters: List[Callable[[List[Dict[str, Any]]], List[Dict[str, Any]]]]
) -> List[Dict[str, Any]]:
    """
    Apply a series of filters to data.
    
    Args:
        data: List of dictionaries to filter
        filters: List of filter functions to apply
        
    Returns:
        Data after applying all filters
    """
    result = data
    for filter_func in filters:
        result = filter_func(result)
    return result


def compact_response_format(
    data: List[Dict[str, Any]], 
    max_total_size: int = 10000
) -> List[Dict[str, Any]]:
    """
    Compact the response format to stay under a size limit.
    
    Args:
        data: List of dictionaries to compact
        max_total_size: Maximum total character size
        
    Returns:
        Compacted data that fits within the size limit
    """
    if not data:
        return []
    
    # First, try to reduce field count
    reduced_data = select_fields(data, ["id", "name", "title", "summary", "score"])
    
    # If still too large, truncate further
    if json.dumps(reduced_data).__len__() > max_total_size:
        # Further reduce fields
        reduced_data = select_fields(reduced_data, ["id", "name", "title"])
        
        # If still too large, reduce count
        if json.dumps(reduced_data).__len__() > max_total_size:
            reduced_data = reduced_data[:max(1, len(reduced_data) // 2)]
    
    # Final truncation if needed
    if json.dumps(reduced_data).__len__() > max_total_size:
        # Truncate the longest fields
        field_lengths = {field: max(50, max_total_size // (len(reduced_data) * len([f for r in reduced_data for f in r]))) 
                         for field in set(f for r in reduced_data for f in r)}
        reduced_data = truncate_long_fields(reduced_data, field_lengths)
    
    return reduced_data


def mcp_filtered_query(
    raw_data: List[Dict[str, Any]],
    top_n: int = 5,
    sort_by: str = None,
    date_filter_days: int = None,
    relevance_threshold: float = None,
    truncate_fields: Dict[str, int] = None,
    select_only: List[str] = None,
    deduplicate_by: str = None
) -> List[Dict[str, Any]]:
    """
    Apply multiple filters to MCP server data to return minimal, relevant results.
    
    Args:
        raw_data: Raw data from MCP server
        top_n: Number of top results to return
        sort_by: Field to sort by
        date_filter_days: Days back to include in date filter
        relevance_threshold: Minimum relevance score
        truncate_fields: Fields to truncate with max lengths
        select_only: Only include these fields
        deduplicate_by: Deduplicate by this field
        
    Returns:
        Filtered and processed data suitable for agent context
    """
    filters = []
    
    # Apply deduplication first
    if deduplicate_by:
        filters.append(lambda data: deduplicate_by_field(data, deduplicate_by))
    
    # Apply date filter
    if date_filter_days and sort_by:
        filters.append(lambda data: filter_by_date_range(data, sort_by, date_filter_days))
    
    # Apply relevance filter
    if relevance_threshold:
        filters.append(lambda data: filter_by_relevance(data, "relevance_score", relevance_threshold, top_n * 2))
    
    # Apply sorting and top-n filter
    if sort_by:
        filters.append(lambda data: filter_top_results(data, sort_by, top_n))
    else:
        # If no sort specified, just limit to top N
        filters.append(lambda data: data[:top_n])
    
    # Apply field selection
    if select_only:
        filters.append(lambda data: select_fields(data, select_only))
    
    # Apply field truncation
    if truncate_fields:
        filters.append(lambda data: truncate_long_fields(data, truncate_fields))
    
    # Apply all filters
    result = apply_filters(raw_data, filters)
    
    # Finally, compact to reasonable size
    return compact_response_format(result)


# Example usage functions for specific MCP server interactions
def gdrive_search_filtered(query: str, limit: int = 5) -> List[Dict[str, Any]]:
    """
    Example function that simulates a filtered GDrive search.
    In a real implementation, this would call the actual MCP server.
    """
    # Simulated raw data from MCP server
    raw_data = [
        {"id": "1", "name": f"Document related to {query} 1", "modified_time": "2023-10-15T10:30:00Z", "size": 1024000, "mime_type": "application/pdf"},
        {"id": "2", "name": f"Another {query} document", "modified_time": "2023-10-14T09:15:00Z", "size": 2048000, "mime_type": "application/vnd.google-apps.document"},
        {"id": "3", "name": f"Old {query} file", "modified_time": "2023-09-20T14:22:00Z", "size": 512000, "mime_type": "text/plain"},
        {"id": "4", "name": f"Recent {query} report", "modified_time": "2023-10-16T16:45:00Z", "size": 4096000, "mime_type": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"},
        {"id": "5", "name": f"Final {query} document", "modified_time": "2023-10-16T11:30:00Z", "size": 1536000, "mime_type": "application/msword"},
        {"id": "6", "name": f"Supplementary {query} material", "modified_time": "2023-10-13T08:05:00Z", "size": 768000, "mime_type": "application/pdf"},
    ]
    
    # Apply filtering to return only relevant results
    return mcp_filtered_query(
        raw_data,
        top_n=limit,
        sort_by="modified_time",
        date_filter_days=30,
        select_only=["id", "name", "modified_time"],
        truncate_fields={"name": 50}
    )


def db_query_filtered(sql_query: str, limit: int = 5) -> List[Dict[str, Any]]:
    """
    Example function that simulates a filtered database query.
    In a real implementation, this would call the actual MCP server.
    """
    # Simulated raw data from MCP server
    raw_data = [
        {"id": 1, "name": "John Doe", "email": "john@example.com", "created_at": "2023-10-15T10:30:00Z", "relevance_score": 0.95},
        {"id": 2, "name": "Jane Smith", "email": "jane@example.com", "created_at": "2023-10-14T09:15:00Z", "relevance_score": 0.87},
        {"id": 3, "name": "Bob Johnson", "email": "bob@example.com", "created_at": "2023-09-20T14:22:00Z", "relevance_score": 0.72},
        {"id": 4, "name": "Alice Williams", "email": "alice@example.com", "created_at": "2023-10-16T16:45:00Z", "relevance_score": 0.91},
        {"id": 5, "name": "Charlie Brown", "email": "charlie@example.com", "created_at": "2023-10-16T11:30:00Z", "relevance_score": 0.83},
        {"id": 6, "name": "Diana Prince", "email": "diana@example.com", "created_at": "2023-10-13T08:05:00Z", "relevance_score": 0.78},
    ]
    
    # Apply filtering to return only relevant results
    return mcp_filtered_query(
        raw_data,
        top_n=limit,
        sort_by="relevance_score",
        relevance_threshold=0.75,
        select_only=["id", "name", "email"],
        truncate_fields={"name": 30, "email": 30}
    )


if __name__ == "__main__":
    # Example usage
    print("Filtered GDrive search results:")
    gdrive_results = gdrive_search_filtered("project", 3)
    print(json.dumps(gdrive_results, indent=2))
    
    print("\nFiltered database query results:")
    db_results = db_query_filtered("SELECT * FROM users", 3)
    print(json.dumps(db_results, indent=2))