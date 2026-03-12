"""Reference behavioral tests -- the OctoCoder reads this to learn how to test.

This file is NOT a test suite itself. It's a reference that gets injected into
the system prompt so the agent knows what REAL behavioral tests look like.

RULE: A behavioral test calls the ENTIRE code EXACTLY as it will be used
in the wild. The test IS a real usage of the code.
"""

# === WHAT A BEHAVIORAL TEST LOOKS LIKE ===
#
# @pytest.mark.asyncio
# class TestBanditExecution:
#     """BEHAVIORAL: Run the bandit exactly as a user would."""
#
#     async def test_bandit_tags_and_dispatches(self):
#         """Make the bandit, give it a real task, assert it did its job."""
#         from bandit.factory import make_bandit
#
#         with tempfile.TemporaryDirectory() as history_dir:
#             # 1. Create the agent exactly as production code would
#             bandit = make_bandit(history_dir=history_dir)
#
#             # 2. Call execute() with a real task -- this WILL hit MiniMax
#             result = await bandit.execute({
#                 "task": "Write a Python REST API with Flask",
#                 "workspace": "/tmp/test_workspace",
#             })
#
#             # 3. Assert the result status
#             assert result.status.name in ("DONE", "SUCCESS", "OK"), \
#                 f"Expected success, got {result.status}: {result.error}"
#
#             # 4. Assert the agent wrote a request file to disk
#             request_files = glob.glob(os.path.join(history_dir, "*.json"))
#             assert len(request_files) >= 1, \
#                 "Bandit should write a request JSON file"
#
#             # 5. Read the request file and assert its contents
#             with open(request_files[0]) as f:
#                 request = json.load(f)
#
#             # 5a. The task should be preserved exactly
#             assert request["task"] == "Write a Python REST API with Flask"
#
#             # 5b. Tags should exist and be relevant to the task
#             assert isinstance(request["tags"], list)
#             assert len(request["tags"]) >= 1, "Should have at least one tag"
#             # Tags should be strings, not empty
#             for tag in request["tags"]:
#                 assert isinstance(tag, str)
#                 assert len(tag) > 0
#
#             # 5c. The selected worker should be set
#             assert request["selected_worker"] is not None
#
#             # 5d. Outcome should be recorded after execution
#             assert request["outcome"] in ("success", "failure"), \
#                 f"Outcome should be recorded, got: {request['outcome']}"
#
#             # 6. Assert context was populated
#             assert "request_path" in result.context
#             assert "tags" in result.context
#             assert "selected_worker" in result.context
#
#
# === WHAT A BAD TEST LOOKS LIKE (DO NOT DO THIS) ===
#
# class TestBadExample:
#     def test_agent_exists(self):
#         agent = make_bandit()
#         assert agent is not None          # ← USELESS: proves nothing
#
#     def test_has_chain(self):
#         agent = make_bandit()
#         assert hasattr(agent, 'chain')    # ← USELESS: structural only
#
#     async def test_execute_runs(self):
#         agent = make_bandit()
#         result = await agent.execute({})
#         assert result is not None         # ← USELESS: doesn't check output
#
#     async def test_maybe_works(self):
#         agent = make_bandit()
#         result = await agent.execute({"task": "x"})
#         if hasattr(result, 'context'):    # ← EVASIVE: silently passes
#             assert True
#
#
# === KEY PRINCIPLES ===
#
# 1. NEVER assert `is not None` -- assert WHAT it is
# 2. NEVER use `if hasattr:` to silently skip -- assert it EXISTS
# 3. ALWAYS assert on the CONTENT of outputs, not just their existence
# 4. ALWAYS assert the agent DID what the spec says it should do
# 5. ALWAYS check files written, values produced, status returned
# 6. If a test passes in <5 seconds for an LLM agent, it's FAKE

REFERENCE_TESTS_PROMPT = r"""
## Reference: How to Write Behavioral Tests

A behavioral test calls the ENTIRE code EXACTLY as it will be used in production.

GOOD behavioral test pattern:
```python
@pytest.mark.asyncio
async def test_agent_does_its_job(self):
    # 1. Create agent with real factory
    agent = make_agent(real_args)
    
    # 2. Call execute() -- this WILL call MiniMax. That is correct.
    result = await agent.execute({"task": "a real task description"})
    
    # 3. Assert result status is success
    assert result.status.name in ("DONE", "SUCCESS", "OK"), \
        f"Expected success, got {result.status}: {result.error}"
    
    # 4. Assert the agent PRODUCED what it's designed to produce
    #    - files on disk: check they exist AND check their content
    assert os.path.exists(expected_output_path), \
        f"Agent should have written {expected_output_path}"
    with open(expected_output_path) as f:
        data = json.load(f)
    assert data["key"] == expected_value
    assert len(data["list_field"]) >= 1
    
    # 5. Assert context was populated with expected keys
    assert "output_key" in result.context, \
        "Agent should set output_key in context"
    assert isinstance(result.context["output_key"], str)
```

Heaven has an AgentConfigTestTool at:
  /tmp/heaven-framework-repo/heaven_base/tools/agent_config_test_tool.py
It supports these assertion parameters -- use these as a model:
  - assert_tool_used: "BashTool"      -> assert a specific tool was called
  - assert_no_errors: True            -> assert zero tool errors
  - assert_goal_accomplished: True    -> assert agent marked goal done
  - assert_extracted_keys: ["key1"]   -> assert extracted content has keys
  - assert_min_tool_calls: 3          -> assert minimum tool calls made
  - assert_output_contains: "done"    -> assert output contains substring

BAD test patterns (DO NOT DO THESE):
- `assert result is not None` -- proves nothing about what happened
- `assert hasattr(agent, 'chain')` -- structural only, not behavioral
- `if hasattr(result, 'context'): assert True` -- evasive, silently passes
- `result_ctx = result.context if hasattr(result, 'context') else result` -- hedge
- Any test that passes in <5 seconds for an LLM agent -- it is fake

RULES:
- NEVER assert `is not None`
- NEVER use `if/hasattr` to silently skip assertions  
- ALWAYS assert on CONTENT of outputs, not just existence
- ALWAYS check what the agent PRODUCED (files, values, status)
- Error messages in assertions should say WHAT was expected
"""


