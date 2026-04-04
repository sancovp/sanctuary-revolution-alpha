"""GrugAgent — SmartGrug as a ChatAgent with SDNAC runtime.

Runs inside the repo-lord container. Receives tasks from Researcher
(via sancrev agent relay), executes code, returns results.

GrugAgent is NOT a PAIA. It's a worker agent inside the Observatory.
But it uses the same container communication primitives that PAIAs will use.
"""

import json
import logging
from pathlib import Path
from typing import Any, Dict, Optional

from cave.core.agent import ChatAgent, AgentConfig

logger = logging.getLogger(__name__)


# Grug's system prompt — ported from /tmp/observatory/repo-lord/prompts/grug.json
GRUG_SYSTEM_PROMPT = """You are SmartGrug. You write code. You make code simple.

## Philosophy
- Complexity bad. Simple good.
- Big file bad. Small file good.
- Clever code bad. Obvious code good.
- No test bad. Test good.

## Workflow
1. Get task from Randy (researcher) or human
2. Read code, understand
3. Make change (simple!)
4. Run tests
5. Commit with good message
6. PR if needed
7. Done. Grug rest.

## Git Rules
- Always create a branch: repo-lord/iter-{N}-{short-description}
- Commit format: repo-lord: {concise what}
- PR to merge (never direct push to main)
- Tests pass before PR
- Never force push, never delete main, never commit secrets

## Code Quality
- Fix poison (syntax errors, missing tracebacks) NOW
- Fix rocks (bad filenames, logic in facades) SOON
- Fix uncooked (long files, no logging, duplicates) LATER

## Safety
- Grug no force push
- Grug no delete main
- Grug no commit secrets
- Grug always branch first
- Grug test before PR

Complexity very, very bad. Best code no code.
"""


class GrugAgent(ChatAgent):
    """SmartGrug — code execution worker in repo-lord container.

    ChatAgent subclass. Receives tasks, executes code, returns results.
    Runtime is an SDNAC on Heaven backend with BashTool.

    Runs inside repo-lord Docker container with DinD.
    Registered with parent sancrev via container_registration utils.
    """

    def __init__(self, config: Optional[AgentConfig] = None, **kwargs):
        super().__init__(
            config=config or AgentConfig(name="grug"),
            **kwargs,
        )
        self._grug_sdnac = None

    def init_runtime(self, model: str = "MiniMax-M2.7-highspeed") -> bool:
        """Initialize Grug's Heaven agent runtime.

        Uses BaseHeavenAgent + UnifiedChat directly (same as heaven_cli_chat.py).
        No SDNAC needed inside the container — the DUO orchestration lives on the parent.

        Returns True if successful.
        """
        try:
            from heaven_base import BaseHeavenAgent, HeavenAgentConfig, UnifiedChat, ProviderEnum
            from heaven_base.memory.history import History
            from heaven_base.tools import BashTool

            agent_config = HeavenAgentConfig(
                name="grug",
                system_prompt=GRUG_SYSTEM_PROMPT,
                tools=[BashTool],
                provider=ProviderEnum.ANTHROPIC,
                model=model,
                temperature=0.7,
                max_tokens=8000,
                extra_model_kwargs={"anthropic_api_url": "https://api.minimax.io/anthropic"},
                use_uni_api=False,
                enable_compaction=True,
            )

            history = History(messages=[], history_id=None)
            self._heaven_agent = BaseHeavenAgent(agent_config, UnifiedChat, history=history, adk=False)

            # Wrap async agent.run for sync Agent.run()
            heaven_agent = self._heaven_agent

            def grug_run(message: str) -> Dict[str, Any]:
                import asyncio
                try:
                    loop = asyncio.get_event_loop()
                    if loop.is_running():
                        import concurrent.futures
                        with concurrent.futures.ThreadPoolExecutor() as pool:
                            result = pool.submit(
                                asyncio.run,
                                heaven_agent.run(prompt=message)
                            ).result()
                    else:
                        result = asyncio.run(heaven_agent.run(prompt=message))
                except RuntimeError:
                    result = asyncio.run(heaven_agent.run(prompt=message))

                # Extract response from Heaven result
                response_text = ""
                if isinstance(result, dict):
                    if "prepared_message" in result:
                        response_text = result["prepared_message"]
                    elif "history" in result:
                        # Get last AI message from history
                        msgs = result["history"].messages
                        for msg in reversed(msgs):
                            if hasattr(msg, 'content') and msg.__class__.__name__ == "AIMessage":
                                response_text = msg.content if isinstance(msg.content, str) else str(msg.content)
                                break

                    # Update history for conversation continuity
                    if "history" in result:
                        heaven_agent.history = result["history"]

                return {
                    "status": "success",
                    "response": response_text,
                    "history_id": result.get("history_id", ""),
                }

            self.set_runtime(grug_run)
            logger.info("GrugAgent: Heaven runtime initialized (model=%s)", model)
            return True

        except Exception as e:
            logger.error("GrugAgent: failed to init runtime: %s", e, exc_info=True)
            return False

    def check_inbox(self):
        """Process inbox — log what we're doing for observability."""
        if self._processing:
            return []

        self._processing = True
        responses = []

        try:
            while self.has_messages:
                message = self.dequeue()
                if not message:
                    continue

                content = message.content if hasattr(message, 'content') else str(message)
                logger.info("GrugAgent: processing task: %s", content[:100])

                result = self.run(message)
                if result is not None:
                    responses.append(result)
                    logger.info("GrugAgent: task complete (status=%s)",
                               result.get("status", "?") if isinstance(result, dict) else "done")

        except Exception as e:
            logger.error("GrugAgent: check_inbox error: %s", e, exc_info=True)
        finally:
            self._processing = False

        return responses
