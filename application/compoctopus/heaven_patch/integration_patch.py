"""Integration Patch — KeywordBasedStateMachine into BaseHeavenAgent.

WITH THE TOOL APPROACH, we only need 2 patches instead of 5.
No _process_agent_response changes. No additional_kws registration.
No prompt injection. The tool handles everything.

================================
PATCH 1: HeavenAgentConfig fields
================================

Location: class HeavenAgentConfig(BaseModel)
After: additional_kw_instructions field (~line 345)

    state_machine: Optional[Any] = None     # KeywordBasedStateMachine instance
    min_sm_cycles: Optional[int] = None     # Minimum complete SM cycles before stopping

================================
PATCH 2: BaseHeavenAgent.__init__ — wire SM tool
================================

Location: BaseHeavenAgent.__init__
After: self.tools initialization (~line 844)

    # --- State Machine Tool Integration ---
    self.state_machine = config.state_machine
    self.min_sm_cycles = config.min_sm_cycles

    if self.state_machine is not None:
        from .state_machine import KeywordBasedStateMachine
        assert isinstance(self.state_machine, KeywordBasedStateMachine)

        # Must be named (persistence needs unique path)
        if config.name in KeywordBasedStateMachine.UNNAMED_AGENTS:
            raise ValueError(f"SM requires named agent, got '{config.name}'")

        # Load persisted state
        self.state_machine.load_state(self.name)

        # Create the SM tool with closure capturing this SM instance
        from .state_machine_tool import create_sm_tool
        sm_tool = create_sm_tool(self.state_machine)
        self.tools.append(sm_tool)

        # Inject SM context into system prompt
        sm_prompt = self.state_machine.build_transition_prompt()
        self.system_prompt += "\\n\\n" + sm_prompt

================================
PATCH 3 (optional): run_langchain break override for min_sm_cycles
================================

Location: run_langchain, iteration break condition (~line 1901)

    # Before the existing break logic:
    if self.current_task == "GOAL ACCOMPLISHED" or not self.goal:
        # Check if SM needs more cycles
        if (hasattr(self, 'state_machine') and self.state_machine is not None
            and self.min_sm_cycles is not None
            and self.state_machine.cycles_completed < self.min_sm_cycles):
            # Override: don't break, force more iterations
            if self.state_machine.is_terminal:
                self.state_machine.reset()
                self.state_machine.save_state(self.name)
                self.goal = "Continue — SM cycle reset, more cycles needed"
            pass  # Don't break
        else:
            break

    # Also extend max_iterations if SM needs it:
    if (hasattr(self, 'min_sm_cycles') and self.min_sm_cycles is not None
        and hasattr(self, 'state_machine') and self.state_machine is not None
        and self.state_machine.cycles_completed < self.min_sm_cycles):
        self.max_iterations = max(self.max_iterations, self.current_iteration + 10)


================================
WHAT WE DON'T NEED ANYMORE
================================

The tool approach eliminates:
- ❌ No additional_kws registration (state names as keywords)
- ❌ No _process_agent_response patch
- ❌ No KV consume-and-delete in _process_agent_response
- ❌ No additional_kw_instructions merge
- ❌ No apply_to_agent method
- ❌ No XML tag parsing by the existing extraction system

The agent just calls StateMachineTool(transition_to="ANNEAL", reason="done")
and gets the new phase prompt back immediately as a tool result.

================================
FILE MAP
================================

heaven_base/
├── state_machine.py               # KeywordBasedStateMachine class (standalone)
├── state_machine_tool.py          # create_sm_tool() factory function
├── baseheavenagent.py             # Patches 1-3 applied here
└── tools/
    └── __init__.py                # Export StateMachineTool if needed
"""
