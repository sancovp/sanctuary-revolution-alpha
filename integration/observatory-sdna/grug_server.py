#!/usr/bin/env python3
"""Grug Container Entry Point — ServiceAgent + SDNAC inside repo-lord.

The simplest possible agent server:
- FastAPI with /execute and /health
- ServiceAgent with an SDNAC
- /execute builds SDNAC per request, runs it, returns result

In sancrev, Grug is a RemoteAgent that hits this /execute endpoint.
"""

import argparse
import logging
import os
import sys

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(name)s %(levelname)s %(message)s",
)
logger = logging.getLogger("grug-server")

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


def make_grug_sdnac(task: str, model: str = "MiniMax-M2.7-highspeed"):
    """Build a fresh SDNAC for one Grug task."""
    from sdna.sdna import SDNAC
    from sdna.ariadne import AriadneChain, InjectConfig
    from sdna.config import HermesConfig, HeavenInputs, HeavenAgentArgs
    from heaven_base.tools import BashTool

    ariadne = AriadneChain(
        name="grug_ariadne",
        elements=[
            InjectConfig(source="literal", inject_as="task", value=task),
        ],
    )

    hermes = HermesConfig(
        name="grug",
        goal=task,
        backend="heaven",
        model=model,
        max_turns=15,
        permission_mode="bypassPermissions",
        source_container="repo-lord",
        target_container="repo-lord",
        heaven_inputs=HeavenInputs(
            agent=HeavenAgentArgs(
                provider="ANTHROPIC",
                max_tokens=8000,
                tools=[BashTool],
                enable_compaction=False,
            ),
        ),
        system_prompt=GRUG_SYSTEM_PROMPT,
    )

    return SDNAC(name="grug", ariadne=ariadne, config=hermes)


def main():
    parser = argparse.ArgumentParser(description="Grug Container Server")
    parser.add_argument("--port", type=int, default=8081)
    parser.add_argument("--host", type=str, default="0.0.0.0")
    parser.add_argument("--model", type=str, default="MiniMax-M2.7-highspeed")
    parser.add_argument("--no-register", action="store_true")
    args = parser.parse_args()

    from fastapi import FastAPI
    from typing import Any, Dict
    import uvicorn

    app = FastAPI(title="Grug Server", version="0.1.0")

    @app.get("/health")
    def health():
        return {"status": "ok"}

    @app.post("/execute")
    async def execute_task(data: Dict[str, Any]):
        task = data.get("code", data.get("task", data.get("message", "")))
        if not task:
            return {"error": "No task provided (use 'code', 'task', or 'message' field)"}

        try:
            sdnac = make_grug_sdnac(task, model=args.model)
            result = await sdnac.execute({})

            history_id = ""
            response_text = ""
            if hasattr(result, 'context') and isinstance(result.context, dict):
                history_id = result.context.get("history_id", "")
                response_text = result.context.get("prepared_message", "")

            # Check for agent execution errors hidden in "success" responses
            status = "success"
            if not history_id:
                # No history_id means hermes_step didn't complete a full conversation
                if "Agent run failed" in response_text or "execution error" in response_text.lower():
                    status = "error"
                    return {
                        "status": "error",
                        "error": f"Grug agent errored during execution: {response_text[:500]}",
                        "history_id": history_id,
                        "response": response_text,
                    }

            return {
                "status": status,
                "history_id": history_id,
                "response": response_text,
            }
        except Exception as e:
            logger.error("Grug execute failed: %s", e, exc_info=True)
            return {"error": str(e)}

    @app.post("/dispatch")
    async def dispatch_task(data: Dict[str, Any]):
        """Async dispatch — accept task, run in background, POST result to callback_url."""
        import asyncio

        task = data.get("task", "")
        investigation_name = data.get("investigation_name", "")
        callback_url = data.get("callback_url", "")

        if not task:
            return {"error": "No task provided"}

        async def _run_and_callback():
            try:
                sdnac = make_grug_sdnac(task, model=args.model)
                result = await sdnac.execute({})

                history_id = ""
                response_text = ""
                status = "success"
                if hasattr(result, 'context') and isinstance(result.context, dict):
                    history_id = result.context.get("history_id", "")
                    response_text = result.context.get("prepared_message", "")

                if not history_id and ("Agent run failed" in response_text or "execution error" in response_text.lower()):
                    status = "error"

                grug_result = {
                    "status": status,
                    "history_id": history_id,
                    "response": response_text,
                }
            except Exception as e:
                logger.error("Grug dispatch execute failed: %s", e, exc_info=True)
                grug_result = {"status": "error", "error": str(e)}

            # Callback to sancrev with history path — researcher reads it via NetworkEditTool
            if callback_url:
                try:
                    import httpx
                    history_id = grug_result.get("history_id", "")
                    grug_history_path = ""
                    if history_id:
                        date_dir = "_".join(history_id.split("_")[:3])
                        grug_history_path = f"/tmp/heaven_data/agents/grug/memories/histories/{date_dir}/{history_id}.json"

                    async with httpx.AsyncClient() as client:
                        resp = await client.post(callback_url, json={
                            "investigation_name": investigation_name,
                            "history_id": history_id,
                            "grug_history_path": grug_history_path,
                            "status": grug_result.get("status", ""),
                        }, timeout=10.0)
                    logger.info("Callback to %s: status=%s", callback_url, resp.status_code)
                except Exception as e:
                    logger.error("Callback to %s failed: %s", callback_url, e)

        asyncio.create_task(_run_and_callback())
        logger.info("Dispatched grug task in background for %s", investigation_name)
        return {"status": "dispatched", "investigation_name": investigation_name}

    logger.info("Starting Grug server on %s:%d (model=%s)", args.host, args.port, args.model)
    uvicorn.run(app, host=args.host, port=args.port)


if __name__ == "__main__":
    main()
