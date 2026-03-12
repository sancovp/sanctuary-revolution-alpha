"""Bandit factory."""

import time
from compoctopus.agent import CompoctopusAgent
from compoctopus.chain_ontology import Chain, FunctionLink
from compoctopus.types import PromptSection, SystemPrompt

from bandit.request_io import find_similar_requests, read_request, update_outcome, write_request

def _setup_request_link(ctx):
    task = ctx.get("task", "")
    history_dir = ctx.get("history_dir", "/tmp/bandit_history")
    request = {"task": task, "timestamp": str(time.time()), "tags": []}
    filepath = write_request(history_dir, request)
    ctx["request_path"] = filepath
    ctx["start_time"] = time.time()
    return ctx

def _extract_tags_link(ctx):
    tags = ctx.get("tags", [])
    if not tags:
        task = ctx.get("task", "")
        tags = [w for w in task.split() if len(w) > 3][:3]
        ctx["tags"] = tags
    request_path = ctx.get("request_path", "")
    if request_path:
        try:
            request = read_request(request_path)
            request["tags"] = tags
            import json
            with open(request_path, "w") as f:
                json.dump(request, f, indent=2)
        except: pass
    return ctx

def _pass_through(ctx):
    return ctx

def _select_worker_link(ctx):
    tags = ctx.get("tags", [])
    history_dir = ctx.get("history_dir", "/tmp/bandit_history")
    similar = find_similar_requests(history_dir, tags)
    if similar:
        for req in similar:
            if req.get("outcome") == "success" and req.get("selected_worker"):
                ctx["selected_worker"] = req["selected_worker"]
                if ctx.get("request_path"):
                    try:
                        request = read_request(ctx["request_path"])
                        request["selected_worker"] = ctx["selected_worker"]
                        import json
                        with open(ctx["request_path"], "w") as f:
                            json.dump(request, f, indent=2)
                    except: pass
                return ctx
    ctx["selected_worker"] = "octopus_coder"
    if ctx.get("request_path"):
        try:
            request = read_request(ctx["request_path"])
            request["selected_worker"] = ctx["selected_worker"]
            import json
            with open(ctx["request_path"], "w") as f:
                json.dump(request, f, indent=2)
        except: pass
    return ctx

def _dispatch_link(ctx):
    task = ctx.get("task", "")
    worker = ctx.get("selected_worker", "octopus_coder")
    ctx["dispatch_result"] = {"worker": worker, "task": task, "status": "dispatched"}
    return ctx

def _record_link(ctx):
    request_path = ctx.get("request_path", "")
    dispatch_result = ctx.get("dispatch_result", {})
    start_time = ctx.get("start_time", time.time())
    duration = time.time() - start_time
    outcome = "success" if dispatch_result.get("status") == "dispatched" else "failure"
    if request_path:
        try: update_outcome(request_path, outcome, duration)
        except: pass
    ctx["outcome"] = outcome
    return ctx

def make_bandit(history_dir="/tmp/bandit_history"):
    setup_link = FunctionLink("setup", _setup_request_link, "Create request file")
    extract_tags_link = FunctionLink("extract_tags", _extract_tags_link, "Extract tags")
    pass_link = FunctionLink("pass_through", _pass_through, "Pass through")
    select_link = FunctionLink("select", _select_worker_link, "Select worker")
    dispatch_link_fn = FunctionLink("dispatch", _dispatch_link, "Dispatch task")
    record_link_fn = FunctionLink("record", _record_link, "Record outcome")
    chain = Chain(chain_name="bandit", links=[setup_link, extract_tags_link, pass_link, select_link, dispatch_link_fn, record_link_fn])
    return CompoctopusAgent(agent_name="bandit", chain=chain, system_prompt=SystemPrompt(sections=[PromptSection(tag="IDENTITY", content="You are the Bandit."), PromptSection(tag="WORKFLOW", content="1.SETUP 2.TAG 3.SELECT 4.DISPATCH 5.RECORD")]), model="minimax")
