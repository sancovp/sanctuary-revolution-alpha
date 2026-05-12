"""
LangChain adapter for PAIA Harness.

Provides a BaseChatModel-compatible interface so Heaven can use
Claude Code via the harness without knowing the difference.

Usage in Heaven:
    from game_wrapper.adapters.langchain_adapter import ClaudeCodeChatModel

    # Add to UnifiedChat.PROVIDERS
    ProviderEnum.CLAUDE_CODE: ClaudeCodeChatModel
"""
import logging
from typing import Any, List, Optional, Iterator

from langchain_core.callbacks import CallbackManagerForLLMRun
from langchain_core.language_models.chat_models import BaseChatModel
from langchain_core.messages import BaseMessage, AIMessage, HumanMessage, SystemMessage
from langchain_core.outputs import ChatResult, ChatGeneration

from ..core.harness import PAIAHarness, HarnessConfig

logger = logging.getLogger(__name__)


class ClaudeCodeChatModel(BaseChatModel):
    """LangChain-compatible chat model that routes to Claude Code via harness.

    This adapter allows Heaven to use Claude Code as if it were an API,
    but under the hood it's controlling a live Claude Code instance via tmux.
    """

    harness: PAIAHarness
    """The PAIA harness instance controlling Claude Code."""

    class Config:
        arbitrary_types_allowed = True

    def __init__(
        self,
        harness: Optional[PAIAHarness] = None,
        harness_config: Optional[HarnessConfig] = None,
        **kwargs
    ):
        """Initialize the adapter.

        Args:
            harness: Existing harness instance to use
            harness_config: Config to create new harness if none provided
        """
        if harness is None:
            config = harness_config or HarnessConfig()
            harness = PAIAHarness(config)

        super().__init__(harness=harness, **kwargs)

    @property
    def _llm_type(self) -> str:
        return "claude-code-harness"

    @property
    def _identifying_params(self) -> dict:
        return {
            "tmux_session": self.harness.config.tmux_session,
            "agent_command": self.harness.config.agent_command,
        }

    def _messages_to_prompt(self, messages: List[BaseMessage]) -> str:
        """Convert LangChain messages to a single prompt string.

        Claude Code doesn't have a native multi-turn API - we send text.
        This flattens the conversation into a prompt.
        """
        parts = []

        for msg in messages:
            if isinstance(msg, SystemMessage):
                # System messages become context/instructions
                parts.append(f"[System]: {msg.content}")
            elif isinstance(msg, HumanMessage):
                parts.append(f"[User]: {msg.content}")
            elif isinstance(msg, AIMessage):
                parts.append(f"[Assistant]: {msg.content}")
            else:
                # Generic fallback
                parts.append(str(msg.content))

        return "\n\n".join(parts)

    def _generate(
        self,
        messages: List[BaseMessage],
        stop: Optional[List[str]] = None,
        run_manager: Optional[CallbackManagerForLLMRun] = None,
        **kwargs
    ) -> ChatResult:
        """Generate a response from Claude Code.

        This is the core method LangChain calls.
        """
        logger.info(f"ClaudeCodeChatModel._generate called with {len(messages)} messages")

        # Convert messages to prompt
        prompt = self._messages_to_prompt(messages)

        # Send to harness and wait for response
        try:
            response_text = self.harness.send_and_wait(prompt)
            logger.info(f"Got response: {len(response_text)} chars")
        except Exception as e:
            logger.exception(f"Harness error: {e}")
            response_text = f"[Harness Error]: {e}"

        # Wrap in LangChain types
        message = AIMessage(content=response_text)
        generation = ChatGeneration(message=message)

        return ChatResult(generations=[generation])

    def _stream(
        self,
        messages: List[BaseMessage],
        stop: Optional[List[str]] = None,
        run_manager: Optional[CallbackManagerForLLMRun] = None,
        **kwargs
    ) -> Iterator[ChatGeneration]:
        """Stream response - falls back to generate for now."""
        # TODO: Implement true streaming by polling capture_pane
        result = self._generate(messages, stop, run_manager, **kwargs)
        yield result.generations[0]

    def ensure_started(self) -> bool:
        """Ensure the harness and agent are running."""
        if not self.harness.session_exists():
            logger.info("Starting harness...")
            self.harness.start()
            return True
        return False
