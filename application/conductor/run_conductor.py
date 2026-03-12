"""Run Conductor agent directly. Usage: python run_conductor.py <prompt> [max_turns]"""
import asyncio
import sys
import logging

logging.basicConfig(level=logging.DEBUG, filename="/tmp/conductor_debug.log", filemode="w")

async def main():
    prompt = sys.argv[1] if len(sys.argv) > 1 else "hello"
    max_turns = int(sys.argv[2]) if len(sys.argv) > 2 else 5

    from conductor.conductor import Conductor, _build_agent_config
    from conductor.cave_registration import get_conductor_system_prompt, ConductorConfig
    from conductor.connector import ClaudePConnector
    from conductor.state_machine import StateMachine

    from heaven_base.baseheavenagent import BaseHeavenAgent
    from heaven_base.unified_chat import UnifiedChat

    system_prompt = get_conductor_system_prompt(ConductorConfig())
    config = _build_agent_config(system_prompt)

    agent = BaseHeavenAgent(
        config, UnifiedChat(),
        use_uni_api=config.use_uni_api,
        max_tool_calls=max_turns,
    )

    result = await agent.run(prompt)
    print(result)

asyncio.run(main())
