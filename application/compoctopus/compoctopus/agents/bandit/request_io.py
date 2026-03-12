"""Request I/O functions for Bandit - mechanical file operations."""

import json
import os
import uuid
from typing import List, Optional, TypedDict


class RequestRecord(TypedDict, total=False):
    """JSON record for each request written to history_dir."""
    request_id: str
    timestamp: str
    task: str
    tags: List[str]
    selected_worker: Optional[str]
    outcome: Optional[str]
    duration_seconds: Optional[float]


def write_request(history_dir: str, request: RequestRecord) -> str:
    """Write a request record to a JSON file in history_dir."""
    request_id = request.get("request_id", str(uuid.uuid4()))
    request["request_id"] = request_id
    filename = f"{request_id}.json"
    filepath = os.path.join(history_dir, filename)
    os.makedirs(history_dir, exist_ok=True)
    with open(filepath, 'w') as f:
        json.dump(request, f, indent=2)
    return filepath


def read_request(filepath: str) -> RequestRecord:
    """Read a request record from a JSON file."""
    with open(filepath) as f:
        return json.load(f)


def update_outcome(filepath: str, outcome: str, duration_seconds: float) -> RequestRecord:
    """Update a request record with outcome and duration."""
    request = read_request(filepath)
    request["outcome"] = outcome
    request["duration_seconds"] = duration_seconds
    with open(filepath, 'w') as f:
        json.dump(request, f, indent=2)
    return request


def find_similar_requests(history_dir: str, tags: List[str], limit: int = 5) -> List[RequestRecord]:
    """Search history for requests with similar tags."""
    if not os.path.exists(history_dir):
        return []
    results = []
    for filename in os.listdir(history_dir):
        if not filename.endswith('.json'):
            continue
        filepath = os.path.join(history_dir, filename)
        try:
            request = read_request(filepath)
        except (json.JSONDecodeError, IOError):
            continue
        request_tags = request.get('tags', [])
        match_count = sum(1 for tag in tags if tag in request_tags)
        if match_count > 0:
            results.append((match_count, request))
    results.sort(key=lambda x: x[0], reverse=True)
    return [r[1] for r in results[:limit]]
