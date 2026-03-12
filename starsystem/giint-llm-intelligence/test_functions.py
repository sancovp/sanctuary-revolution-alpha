#!/usr/bin/env python3
"""Test the core functions directly."""

import asyncio
import sys
from pathlib import Path

# Import the actual functions from the module
sys.path.insert(0, str(Path(__file__).parent))

# Import the core functions directly, not the FastMCP wrapped versions
from mcp_server import (
    get_qa_path, get_response_file, load_qa_metadata, save_qa_metadata,
    RESPONSE_DIR
)

async def test_basic_functionality():
    """Test the basic file operations."""
    
    print("Testing core file operations...")
    
    # Test path generation
    qa_path = get_qa_path("test123")
    print(f"QA path: {qa_path}")
    
    response_file = get_response_file("test123", 1)
    print(f"Response file: {response_file}")
    
    # Test metadata operations
    metadata = {
        "qa_id": "test123",
        "created_at": "2025-09-08",
        "response_count": 0,
        "status": "active",
        "tags": [],
        "files": []
    }
    
    # Create directory and save metadata
    qa_path.mkdir(parents=True, exist_ok=True)
    save_qa_metadata("test123", metadata)
    
    # Load it back
    loaded = load_qa_metadata("test123")
    print(f"Saved and loaded metadata: {loaded}")
    
    # Test response file creation
    with open(response_file, "w") as f:
        f.write("# Response 1: Test response\n\nThis is a test response.")
    
    # Verify it exists
    assert response_file.exists()
    content = response_file.read_text()
    print(f"Response file content: {content[:50]}...")
    
    print("✅ All basic tests passed!")

if __name__ == "__main__":
    asyncio.run(test_basic_functionality())