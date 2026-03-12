#!/usr/bin/env python3
"""
Claude Code to HEAVEN History Converter
Converts Claude Code transcript format to HEAVEN History format for summarization
"""

import json
import sys
import os
from datetime import datetime
from typing import List, Dict, Any, Optional

# Set HEAVEN environment variables
os.environ['HEAVEN_DATA_DIR'] = '/tmp/heaven_data'
os.makedirs('/tmp/heaven_data', exist_ok=True)

try:
    from heaven_base.memory.history import History, AgentStatus
    from langchain_core.messages import BaseMessage, SystemMessage, HumanMessage, AIMessage, ToolMessage
    from heaven_base.utils.auto_summarize import auto_summarize
    HEAVEN_AVAILABLE = True
except ImportError as e:
    print(f"HEAVEN framework not available: {e}", file=sys.stderr)
    HEAVEN_AVAILABLE = False


def convert_claude_message_to_langchain(claude_msg: Dict[str, Any]) -> Optional[BaseMessage]:
    """Convert a Claude Code message to LangChain format"""
    
    msg_type = claude_msg.get('type')
    message_content = claude_msg.get('message', {})
    
    if msg_type == 'user':
        # Extract text content from user messages
        content_text = ""
        if 'content' in message_content:
            for content_item in message_content['content']:
                if isinstance(content_item, dict) and content_item.get('type') == 'text':
                    content_text += content_item.get('text', '')
                elif isinstance(content_item, str):
                    content_text += content_item
        
        return HumanMessage(content=content_text)
    
    elif msg_type == 'assistant':
        # Handle assistant messages with tool calls
        content_items = message_content.get('content', [])
        
        # Extract text content
        text_content = ""
        tool_calls = []
        
        for item in content_items:
            if isinstance(item, dict):
                if item.get('type') == 'text':
                    text_content += item.get('text', '')
                elif item.get('type') == 'tool_use':
                    # Convert to LangChain tool call format (flat, no function wrapper)
                    tool_call = {
                        'id': item.get('id', ''),
                        'name': item.get('name', ''),
                        'args': item.get('input', {})
                    }
                    tool_calls.append(tool_call)
            elif isinstance(item, str):
                text_content += item
        
        # Create AIMessage with tool calls if any
        additional_kwargs = {}
        if tool_calls:
            additional_kwargs['tool_calls'] = tool_calls
            return AIMessage(
                content=text_content,
                additional_kwargs=additional_kwargs
            )
        else:
            return AIMessage(content=text_content, additional_kwargs=additional_kwargs)
    
    # Skip other message types for now
    return None


def parse_claude_transcript_to_langchain(transcript_content: str) -> List[BaseMessage]:
    """Parse Claude Code JSONL transcript to LangChain messages"""
    messages = []
    
    # Parse JSONL format
    for line in transcript_content.strip().split('\n'):
        if not line.strip():
            continue
            
        try:
            claude_msg = json.loads(line)
            
            # Skip summary messages and meta messages
            if claude_msg.get('isCompactSummary') or claude_msg.get('isMeta'):
                continue
                
            # Convert to LangChain format
            langchain_msg = convert_claude_message_to_langchain(claude_msg)
            if langchain_msg:
                messages.append(langchain_msg)
                
        except json.JSONDecodeError:
            continue
    
    return messages


def create_heaven_history_from_claude_transcript(transcript_path: str, session_id: str) -> Optional[History]:
    """Create a HEAVEN History object from Claude Code transcript"""
    
    if not HEAVEN_AVAILABLE:
        print("HEAVEN framework not available", file=sys.stderr)
        return None
    
    try:
        # Read the transcript
        with open(transcript_path, 'r') as f:
            transcript_content = f.read()
        
        # Convert to LangChain messages
        messages = parse_claude_transcript_to_langchain(transcript_content)
        
        if not messages:
            print("No valid messages found in transcript", file=sys.stderr)
            return None
        
        # Insert SystemMessage at index 0 (required for HEAVEN)
        from langchain_core.messages import SystemMessage
        system_message = SystemMessage(content="Converted Claude Code conversation for analysis.")
        messages.insert(0, system_message)
        
        # Create HEAVEN History
        history = History(
            messages=messages,
            created_datetime=datetime.now(),
            metadata={
                "source": "claude_code",
                "session_id": session_id,
                "transcript_path": transcript_path,
                "converted_at": datetime.now().isoformat()
            },
            project="claude_code_conversation"
        )
        
        # Save the history
        history_id = history.save("claude_code_converted")
        history.history_id = history_id
        
        print(f"Created HEAVEN History with ID: {history_id}", file=sys.stderr)
        return history
        
    except Exception as e:
        print(f"Error creating HEAVEN history: {e}", file=sys.stderr)
        import traceback
        print(f"Full traceback:\n{traceback.format_exc()}", file=sys.stderr)
        return None


async def summarize_claude_transcript_with_heaven(transcript_path: str, session_id: str) -> Optional[Dict[str, Any]]:
    """Convert Claude transcript to HEAVEN format and summarize it"""
    
    if not HEAVEN_AVAILABLE:
        return None
    
    # Create HEAVEN History
    history = create_heaven_history_from_claude_transcript(transcript_path, session_id)
    if not history:
        return None
    
    try:
        # Use HEAVEN's auto_summarize function
        summary_result = await auto_summarize(history)
        
        return {
            "heaven_history_id": history.history_id,
            "summary_result": summary_result,
            "success": True
        }
        
    except Exception as e:
        print(f"Error summarizing with HEAVEN: {e}", file=sys.stderr)
        return {
            "heaven_history_id": history.history_id if history else None,
            "error": str(e),
            "success": False
        }


def test_converter():
    """Test the converter with sample data"""
    
    # Sample Claude Code message format
    sample_transcript = '''{"type":"user","message":{"role":"user","content":[{"type":"text","text":"Hello, can you help me with a coding task?"}]},"uuid":"test-1","timestamp":"2025-08-16T22:00:00.000Z"}
{"type":"assistant","message":{"role":"assistant","content":[{"type":"text","text":"Of course! I'd be happy to help you with coding. What specific task are you working on?"}]},"uuid":"test-2","timestamp":"2025-08-16T22:00:05.000Z"}
{"type":"user","message":{"role":"user","content":[{"type":"text","text":"I need to create a function that processes a list"}]},"uuid":"test-3","timestamp":"2025-08-16T22:00:10.000Z"}
{"type":"assistant","message":{"role":"assistant","content":[{"type":"tool_use","id":"tool-1","name":"Write","input":{"file_path":"/tmp/test.py","content":"def process_list(items):\\n    return [item.upper() for item in items]"}}]},"uuid":"test-4","timestamp":"2025-08-16T22:00:15.000Z"}'''
    
    # Test parsing
    messages = parse_claude_transcript_to_langchain(sample_transcript)
    
    print(f"Parsed {len(messages)} messages:")
    for i, msg in enumerate(messages):
        print(f"  {i+1}. {type(msg).__name__}: {msg.content[:50]}...")
        if hasattr(msg, 'tool_calls') and msg.tool_calls:
            print(f"     Tool calls: {len(msg.tool_calls)}")
    
    if HEAVEN_AVAILABLE:
        # Test creating HEAVEN History
        try:
            history = History(
                messages=messages,
                created_datetime=datetime.now(),
                metadata={"test": True},
                project="test_conversion"
            )
            print(f"Successfully created HEAVEN History with {len(history.messages)} messages")
            return True
        except Exception as e:
            print(f"Error creating HEAVEN History: {e}")
            return False
    else:
        print("HEAVEN framework not available for testing")
        return False


if __name__ == "__main__":
    # Test the converter
    print("Testing Claude Code to HEAVEN converter...")
    success = test_converter()
    if success:
        print("✅ Converter test passed!")
    else:
        print("❌ Converter test failed!")