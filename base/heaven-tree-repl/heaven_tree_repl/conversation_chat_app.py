#!/usr/bin/env python3
"""
Enhanced HEAVEN Chat App with Conversation Management

This demonstrates proper conversation flow:
- start_chat: Creates new conversation + first history
- continue_chat: Adds new history to existing conversation
- list_conversations: Show available conversations
- load_conversation: Switch to existing conversation

Uses both heaven_response_utils and heaven_conversation_utils.

TreeShell Conversation Registry:
- Tracks which conversations were started from TreeShell
- list_conversations filters to only TreeShell conversations
- load_conversation validates against registry
"""

import asyncio
import json
import os

from heaven_tree_repl import UserTreeShell, render_response
from heaven_base import HeavenAgentConfig, ProviderEnum, completion_runner
from heaven_base.langgraph.foundation import HeavenState
from heaven_base.utils.heaven_response_utils import extract_heaven_response, extract_history_id_from_result
from heaven_base.utils.heaven_conversation_utils import start_chat, continue_chat, load_chat, list_chats, search_chats, get_latest_history
from heaven_base.tools.view_history_tool import view_history_tool_func

# Global state for current conversation
current_conversation = {
    "conversation_id": None,
    "conversation_data": None
}

# ============================================================================
# TreeShell Conversation Registry
# ============================================================================
# Registry file stores conversation IDs that were started from TreeShell
# CONNECTS_TO: /tmp/heaven_data/tree_shell_conversations_registry.json (read/write) — tracks TreeShell-originated conversations
TREESHELL_REGISTRY_PATH = "/tmp/heaven_data/tree_shell_conversations_registry.json"


def _get_treeshell_conv_ids():
    """Get set of TreeShell-originated conversation IDs."""
    if os.path.exists(TREESHELL_REGISTRY_PATH):
        try:
            with open(TREESHELL_REGISTRY_PATH) as f:
                return set(json.load(f))
        except (json.JSONDecodeError, IOError):
            return set()
    return set()


def _register_treeshell_conv(conv_id):
    """Register a conversation as TreeShell-originated."""
    ids = _get_treeshell_conv_ids()
    ids.add(conv_id)
    os.makedirs(os.path.dirname(TREESHELL_REGISTRY_PATH), exist_ok=True)
    with open(TREESHELL_REGISTRY_PATH, 'w') as f:
        json.dump(list(ids), f)


def _filter_treeshell_conversations(conversations):
    """Filter conversation list to only TreeShell-originated conversations."""
    treeshell_ids = _get_treeshell_conv_ids()
    return [c for c in conversations if c["conversation_id"] in treeshell_ids]


def _is_treeshell_conversation(conv_id):
    """Check if a conversation was started from TreeShell."""
    return conv_id in _get_treeshell_conv_ids()


# ============================================================================
# Chat Functions
# ============================================================================

async def _start_chat(title: str, message: str, tags: str, agent_config, return_all_results: bool = False):
    """Start a new conversation."""
    if not title.strip():
        return "❌ Please provide a conversation title", False
    if not message.strip():
        return "❌ Please provide a first message", False
    if not agent_config:
        return "❌ No agent configuration provided", False
    
    # DEBUG: Show what agent config we're getting
    debug_info = f"Agent config debug: name={agent_config.name}, model={agent_config.model}, provider={agent_config.provider}, tools={agent_config.tools}"
    if len(debug_info) > 500:
        debug_info = debug_info[:500] + "..."
    
    try:
        
        # Parse tags
        tag_list = [tag.strip() for tag in tags.split(",") if tag.strip()] if tags else []
        
        # Create HEAVEN state and get first response
        state = HeavenState({
            "results": [],
            "context": {},
            "agents": {}
        })
        
        result = await completion_runner(
            state,
            prompt=message,
            agent=agent_config
        )
        
        # Extract response and history_id
        history_id = extract_history_id_from_result(result)
        
        if return_all_results:
            # Return full iteration view
            from heaven_base.memory.history import History
            history = History.load_from_id(history_id)
            last_index = len(history.iterations) - 1
            response = view_history_tool_func(history_id, start=last_index, end=last_index)
        else:
            # Return final message only (default behavior)
            response = extract_heaven_response(result)
        
        if not history_id:
            return f"❌ Failed to get history_id from completion\n\n{debug_info}\n\nDEBUG INFO:\nCompletion result type: {type(result)}\nCompletion result: {repr(result)}\nExtracted response: {repr(response)}\nExtracted history_id: {repr(history_id)}", False
        
        # Start the conversation
        conversation_data = start_chat(
            title=title,
            first_history_id=history_id,
            agent_name=agent_config.name,
            tags=tag_list
        )
        
        # Register as TreeShell conversation
        _register_treeshell_conv(conversation_data["conversation_id"])
        
        # Update current conversation
        current_conversation["conversation_id"] = conversation_data["conversation_id"]
        current_conversation["conversation_data"] = conversation_data
        
        result_text = f"""🚀 **Started New Conversation**
📝 **Title:** {title}
🆔 **ID:** {conversation_data['conversation_id']}
🏷️ **Tags:** {', '.join(tag_list) if tag_list else 'None'}

**Agent response:** {response}"""
        
        return result_text, True
        
    except Exception as e:
        import traceback
        full_traceback = traceback.format_exc()
        error_msg = f"❌ Error starting conversation: {str(e)}\n\n**Exception Type:** {type(e).__name__}\n**Full Traceback:**\n{full_traceback}"
        print(f"FULL ERROR DETAILS:\n{error_msg}")  # Also print to console
        return error_msg, False


async def _continue_chat(message: str, agent_config, return_all_results: bool = False):
    """Continue the current conversation."""
    if not message.strip():
        return "❌ Please provide a message", False
    if not agent_config:
        return "❌ No agent configuration provided", False
    
    if not current_conversation["conversation_id"]:
        return "❌ No active conversation. Please start a new chat first.", False
    
    try:
        
        # Get conversation context from the latest complete history only
        conv_data = current_conversation["conversation_data"]
        latest_history_id = get_latest_history(current_conversation["conversation_id"])
        
        # Build context-aware prompt with conversation context
        context_prompt = f"Continuing conversation '{conv_data['title']}'.\n\nUser message: {message}"
        
        # TODO: Could load actual conversation context from latest_history_id if needed
        # For now using simplified context with conversation title
        
        # Create HEAVEN state and get response
        state = HeavenState({
            "results": [],
            "context": {},
            "agents": {}
        })
        
        result = await completion_runner(
            state,
            prompt=context_prompt,
            agent=agent_config,
            history_id=latest_history_id
        )
        
        # Extract response and history_id
        history_id = extract_history_id_from_result(result)
        
        if return_all_results:
            # Return full iteration view
            from heaven_base.memory.history import History
            history = History.load_from_id(history_id)
            last_index = len(history.iterations) - 1
            response = view_history_tool_func(history_id, start=last_index, end=last_index)
        else:
            # Return final message only (default behavior)
            response = extract_heaven_response(result)
        
        if not history_id:
            return f"❌ Failed to get history_id from completion\n\n{debug_info}\n\nDEBUG INFO:\nCompletion result type: {type(result)}\nCompletion result: {repr(result)}\nExtracted response: {repr(response)}\nExtracted history_id: {repr(history_id)}", False
        
        # Continue the conversation
        updated_conv = continue_chat(
            current_conversation["conversation_id"],
            history_id
        )
        
        # Update current conversation data
        current_conversation["conversation_data"] = updated_conv
        
        result_text = f"""💬 **Continued Conversation**
📝 **Title:** {conv_data['title']}
🔢 **Exchange #{updated_conv['metadata']['total_exchanges']}**

**Agent response:** {response}"""
        
        return result_text, True
        
    except Exception as e:
        import traceback
        error_msg = f"""❌ Error continuing conversation: {str(e)}
        
**Exception Type:** {type(e).__name__}
**Traceback:**
```
{traceback.format_exc()}
```"""
        return error_msg, False


def _list_conversations(limit: int = 10):
    """List recent TreeShell conversations only."""
    
    try:
        # Get ALL conversations from underlying system
        all_conversations = list_chats(limit=limit)
        
        # Filter to only TreeShell-originated conversations
        treeshell_conversations = _filter_treeshell_conversations(all_conversations)
        
        if not treeshell_conversations:
            return "📭 No TreeShell conversations found (use 'start' to begin a new one)", True
        
        result_lines = [f"📚 **Recent TreeShell Conversations** (showing {len(treeshell_conversations)}):"]
        result_lines.append("")
        
        for i, conv in enumerate(treeshell_conversations, 1):
            tags_str = ", ".join(conv["metadata"]["tags"]) if conv["metadata"]["tags"] else "None"
            exchanges = conv["metadata"]["total_exchanges"]
            last_updated = conv["last_updated"][:19].replace("T", " ")  # Format datetime
            
            # Mark current conversation
            current_marker = " 🔹 (ACTIVE)" if conv["conversation_id"] == current_conversation["conversation_id"] else ""
            
            result_lines.append(f"{i}. **{conv['title']}**{current_marker}")
            result_lines.append(f"   🆔 ID: `{conv['conversation_id']}`")
            result_lines.append(f"   💬 Exchanges: {exchanges} | 🕐 Updated: {last_updated}")
            result_lines.append(f"   🏷️ Tags: {tags_str}")
            result_lines.append("")
        
        return "\n".join(result_lines), True
        
    except Exception as e:
        return f"❌ Error listing conversations: {str(e)}", False


def _load_conversation(conversation_id: str):
    """Load an existing TreeShell conversation."""
    
    if not conversation_id.strip():
        return "❌ Please provide a conversation_id", False
    
    try:
        # First check if it's a TreeShell conversation
        if not _is_treeshell_conversation(conversation_id):
            return f"❌ Conversation '{conversation_id}' was not started from TreeShell.\n\nOnly TreeShell-originated conversations can be loaded here.\nUse 'list' to see available TreeShell conversations.", False
        
        # Load the conversation
        conv_data = load_chat(conversation_id)
        
        if not conv_data:
            return f"❌ Conversation '{conversation_id}' not found", False
        
        # Update current conversation
        current_conversation["conversation_id"] = conversation_id
        current_conversation["conversation_data"] = conv_data
        
        tags_str = ", ".join(conv_data["metadata"]["tags"]) if conv_data["metadata"]["tags"] else "None"
        exchanges = conv_data["metadata"]["total_exchanges"]
        histories = len(conv_data["history_chain"])
        
        result_text = f"""✅ **Loaded Conversation**
📝 **Title:** {conv_data['title']}
🆔 **ID:** {conversation_id}
💬 **Exchanges:** {exchanges}
📚 **Histories:** {histories}
🏷️ **Tags:** {tags_str}
🕐 **Created:** {conv_data['created_datetime'][:19].replace('T', ' ')}
🕐 **Updated:** {conv_data['last_updated'][:19].replace('T', ' ')}

Ready to continue this conversation!"""
        
        return result_text, True
        
    except Exception as e:
        return f"❌ Error loading conversation: {str(e)}", False


def _search_conversations(query: str):
    """Search TreeShell conversations only."""
    
    if not query.strip():
        return "❌ Please provide a search query", False
    
    try:
        # Search all conversations
        all_matches = search_chats(query)
        
        # Filter to only TreeShell conversations
        matches = [c for c in all_matches if _is_treeshell_conversation(c["conversation_id"])]
        
        if not matches:
            return f"🔍 No TreeShell conversations found matching '{query}'", True
        
        result_lines = [f"🔍 **Search Results for '{query}'** ({len(matches)} TreeShell conversations):"]
        result_lines.append("")
        
        for i, conv in enumerate(matches, 1):
            tags_str = ", ".join(conv["metadata"]["tags"]) if conv["metadata"]["tags"] else "None"
            exchanges = conv["metadata"]["total_exchanges"]
            
            result_lines.append(f"{i}. **{conv['title']}**")
            result_lines.append(f"   🆔 ID: `{conv['conversation_id']}`")
            result_lines.append(f"   💬 Exchanges: {exchanges}")
            result_lines.append(f"   🏷️ Tags: {tags_str}")
            result_lines.append("")
        
        return "\n".join(result_lines), True
        
    except Exception as e:
        return f"❌ Error searching conversations: {str(e)}", False


async def main():
    config = {
        "app_id": "HEAVENly TOME",
        "domain": "universal", 
        "role": "AI Automation Emergence Engineer",
        "about_app": "A conversation management system that tracks chat history, enables seamless chat continuation, and provides search capabilities across all your AI interactions.",
        "about_domain": "The universal domain encompasses all aspects of AI automation emergence engineering, from conversation management to system orchestration.",
        "nodes": {
            "start_chat": {
                "type": "Callable",
                "prompt": "Start New Chat",
                "description": "Start a new conversation with a title and first message",
                "function_name": "_start_chat",
                "args_schema": {
                    "title": "str", 
                    "message": "str",
                    "tags": "str",  # comma-separated
                    "return_all_results": "bool"  # False = final message only, True = full iteration
                }
            },
            "continue_chat": {
                "type": "Callable",
                "prompt": "Continue Chat", 
                "description": "Continue the current active conversation",
                "function_name": "_continue_chat",
                "args_schema": {
                    "message": "str",
                    "return_all_results": "bool"  # False = final message only, True = full iteration
                }
            },
            "list_conversations": {
                "type": "Callable",
                "prompt": "List Conversations",
                "description": "Show recent TreeShell conversations",
                "function_name": "_list_conversations",
                "args_schema": {"limit": "int"}
            },
            "load_conversation": {
                "type": "Callable",
                "prompt": "Load Conversation",
                "description": "Switch to an existing TreeShell conversation",
                "function_name": "_load_conversation", 
                "args_schema": {"conversation_id": "str"}
            },
            "search_conversations": {
                "type": "Callable",
                "prompt": "Search Conversations",
                "description": "Search TreeShell conversations by title or tags",
                "function_name": "_search_conversations",
                "args_schema": {"query": "str"}
            }
        }
    }
    
    # Create shell and state
    shell = UserTreeShell(config)
    
    # Use the global current_conversation state defined at module level
    # Functions are already defined at module level, no need to redefine them
    
    # Register functions
    shell.register_async_function("_start_chat", _start_chat)
    shell.register_async_function("_continue_chat", _continue_chat)
    shell._list_conversations = _list_conversations
    shell._load_conversation = _load_conversation
    shell._search_conversations = _search_conversations
    
    # Only print when run directly, not when imported
    if __name__ == "__main__":
        response = await shell.handle_command("")
        print(render_response(response))
    
    # Return the shell for manual testing
    return shell


if __name__ == "__main__":
    asyncio.run(main())
