"""
Heaven Integration - How to wire ClaudeCodeChatModel into Heaven.

This file shows the pattern. You can either:
1. Patch unified_chat.py directly (add CLAUDE_CODE provider)
2. Use this as a drop-in replacement in specific agents

Option 1: Add to unified_chat.py
================================

# In unified_chat.py, add:

from game_wrapper.adapters.langchain_adapter import ClaudeCodeChatModel

class ProviderEnum(Enum):
    ANTHROPIC = 'anthropic'
    OPENAI = 'openai'
    GOOGLE = 'google'
    GROQ = 'groq'
    DEEPSEEK = 'deepseek'
    CLAUDE_CODE = 'claude_code'  # <-- ADD THIS

class UnifiedChat:
    PROVIDERS = {
        ProviderEnum.ANTHROPIC: ChatAnthropic,
        ProviderEnum.OPENAI: ChatOpenAI,
        ProviderEnum.GOOGLE: ChatGoogleGenerativeAI,
        ProviderEnum.GROQ: ChatGroq,
        ProviderEnum.DEEPSEEK: ChatDeepSeek,
        ProviderEnum.CLAUDE_CODE: ClaudeCodeChatModel,  # <-- ADD THIS
    }

    # In create(), add special handling:
    elif provider == ProviderEnum.CLAUDE_CODE:
        # Claude Code doesn't use API keys or standard params
        from game_wrapper.core.harness import HarnessConfig
        harness_config = HarnessConfig(
            agent_command=kwargs.get('agent_command', 'claude'),
            working_directory=kwargs.get('working_directory', os.getcwd())
        )
        return ClaudeCodeChatModel(harness_config=harness_config)


Option 2: Use directly in agent configs
=======================================

# In any agent config file:

from game_wrapper.adapters.langchain_adapter import ClaudeCodeChatModel
from game_wrapper.core.harness import PAIAHarness, HarnessConfig

# Create harness once (singleton pattern recommended)
harness = PAIAHarness(HarnessConfig(
    agent_command="claude",
    working_directory="/path/to/project"
))
harness.start()

# Create the chat model
chat_model = ClaudeCodeChatModel(harness=harness)

# Use it like any other LangChain model
response = chat_model.invoke([
    HumanMessage(content="What files are in this directory?")
])
print(response.content)
"""

from enum import Enum
from typing import Optional
import os

# Re-export for convenience
from .langchain_adapter import ClaudeCodeChatModel
from cave.core.harness import PAIAHarness, HarnessConfig


class ClaudeCodeProvider:
    """Factory for creating Claude Code chat models via harness.

    This matches the UnifiedChat.create() pattern.
    """

    _harness: Optional[PAIAHarness] = None

    @classmethod
    def get_harness(cls, config: Optional[HarnessConfig] = None) -> PAIAHarness:
        """Get or create the singleton harness."""
        if cls._harness is None:
            cls._harness = PAIAHarness(config or HarnessConfig())
        return cls._harness

    @classmethod
    def create(
        cls,
        agent_command: str = "claude",
        working_directory: Optional[str] = None,
        auto_start: bool = True,
        **kwargs
    ) -> ClaudeCodeChatModel:
        """Create a ClaudeCodeChatModel.

        Args:
            agent_command: Command to spawn agent (claude, aider, etc)
            working_directory: Directory for agent to work in
            auto_start: Whether to start harness if not running
            **kwargs: Additional config options

        Returns:
            ClaudeCodeChatModel ready for use
        """
        config = HarnessConfig(
            agent_command=agent_command,
            working_directory=working_directory or os.getcwd(),
            **{k: v for k, v in kwargs.items() if hasattr(HarnessConfig, k)}
        )

        harness = cls.get_harness(config)

        if auto_start and not harness.session_exists():
            harness.start()

        return ClaudeCodeChatModel(harness=harness)


# Quick test function
def test_integration():
    """Quick test of the integration."""
    model = ClaudeCodeProvider.create(
        agent_command="claude",
        working_directory="/tmp"
    )

    from langchain_core.messages import HumanMessage
    response = model.invoke([
        HumanMessage(content="Say 'Hello from harness!' and nothing else.")
    ])

    print(f"Response: {response.content}")
    return response


if __name__ == "__main__":
    test_integration()
